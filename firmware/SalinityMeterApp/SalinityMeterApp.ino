// AI smart salinity meter - integrated firmware (R7 wiring, R8.0 software).
// Patent P2026-070 flow:
//   S100/S300 salinity (EC probe + DS18B20)       -> SALT screen / "measure"
//   S200/S400 ToF depth map + camera, broth volume -> SCAN screen / "scan"
//   S500      target salinity                      -> TARGET screen / "target"
//   S600      salt g or water mL guide             -> GUIDE screen / "guide" event
//   S700      add, mix, re-measure until +-0.05%p  -> GUIDE screen K1 / "recheck"
// Results go to the phone over BLE (see BleLink.h) and to USB serial as "EVT {json}".
// The R7.1 serial commands m/k/t/p and their output lines are kept.
#include <Wire.h>
#include "mbedtls/base64.h"

#include "Config.h"
#include "SalinityProbe.h"
#include "Buzzer.h"
#include "Buttons.h"
#include "Display.h"
#include "TofSensor.h"
#include "CameraCapture.h"
#include "Storage.h"
#include "SaltModel.h"
#include "BleLink.h"
#include "JsonLine.h"

// ---------------------------------------------------------------- state

enum class Screen : uint8_t { Salt, Scan, Target, Guide, Link, Count };
const char *const kScreenTitle[] = {"SALT", "SCAN", "TARGET", "GUIDE", "LINK"};

enum class Source : uint8_t { Usb, Ble, Button };

struct SaltState {
  bool valid = false;        // a completed acquisition exists
  uint32_t seq = 0;
  uint32_t atMs = 0;
  uint32_t epoch = 0;
  float tablePct = NAN;      // calibration table output
  float pct = NAN;           // after temperature / cell correction (reported value)
  double index = NAN;
  float trials[3] = {NAN, NAN, NAN};
  float tempC = NAN;
  probe::Span span = probe::Span::OutsideDomain;
  bool unstable = false;
  bool saved = false;
};

struct ScanState {
  bool valid = false;
  uint32_t atMs = 0;
  tof::Frame frame;
  model::Volume volume;
};

struct Session {                 // S700 add / re-measure loop
  uint8_t rounds = 0;
  bool reached = false;
  bool advise = false;           // rounds exceeded: manual adjustment / sensor check
};

SaltState salt;
ScanState scan;
Session session;
Screen screen = Screen::Salt;
bool dirty = true;
uint32_t lastDraw = 0;
uint32_t lastActivity = 0;
int64_t epochOffset = 0;         // epoch seconds - millis()/1000, 0 = unknown
bool wasSubscribed = false;
uint16_t imageChunkBytes = 0;    // chunk size announced in image_begin
char toastBig[12] = "";
char toastFoot[22] = "";
uint32_t toastUntil = 0;

// ---------------------------------------------------------------- helpers

void i2cFast() {
  Wire.setClock(cfg::kI2cFastHz);
  Wire.setTimeOut(cfg::kI2cFastTimeoutMs);
}

// Exactly the bus settings of the R7.1 calibration runs.
void i2cMeasure() {
  Wire.setClock(cfg::kI2cMeasureHz);
  Wire.setTimeOut(cfg::kI2cMeasureTimeoutMs);
}

uint32_t nowEpoch() {
  if (epochOffset == 0) return 0;
  return uint32_t(epochOffset + int64_t(millis() / 1000));
}

bool scanFresh() { return scan.valid && millis() - scan.atMs < cfg::kScanFreshMs; }

// Broth volume from the phone app (camera + ToF + back-calculation), if recent.
float brothOverrideMl = NAN;
uint32_t brothOverrideAt = 0;
float stepRatio = 1.0f;  // share of the amount shown for the first (split) addition

bool brothOverrideFresh() {
  return isfinite(brothOverrideMl) && millis() - brothOverrideAt < cfg::kBrothOverrideMs;
}

float freshBrothMl() {
  if (brothOverrideFresh()) return brothOverrideMl;
  return (scanFresh() && scan.volume.valid) ? scan.volume.brothMl : NAN;
}

void toastFor(const char *big, const char *foot, uint32_t ms) {
  strlcpy(toastBig, big, sizeof(toastBig));
  strlcpy(toastFoot, foot, sizeof(toastFoot));
  toastUntil = millis() + ms;
  dirty = true;
}

void toast(const char *big, const char *foot) { toastFor(big, foot, 2500); }

void showBusy(const char *title, const char *big, uint8_t progress, const char *foot) {
  display::setPower(true);
  display::View v;
  v.title = title;
  v.right = "BUSY";
  v.big = big;
  v.foot = foot;
  v.progress = progress;
  display::draw(v);
}

void emit(JsonLine &json) {
  const char *line = json.finish();
  Serial.print("EVT ");
  Serial.println(line);
  blelink::sendLine(line);
}

void emitError(const char *op, const char *code, const char *message) {
  JsonLine j("error");
  j.s("op", op).s("code", code).s("msg", message);
  emit(j);
}

void emitAck(const char *cmd) {
  JsonLine j("ack");
  j.s("cmd", cmd);
  emit(j);
}

// ---------------------------------------------------------------- events

void emitSettings() {
  const store::Settings &s = store::settings();
  JsonLine j("settings");
  j.f("targetPct", s.targetPct)
   .f("floorMm", s.floorMm, 1)
   .s("bowlShape", s.bowlShape == store::BowlShape::Rect ? "rect" : "round")
   .f("bowlAMm", s.bowlAMm, 1).f("bowlBMm", s.bowlBMm, 1).f("bowlDepthMm", s.bowlDepthMm, 1)
   .f("solidsAlpha", s.solidsAlpha, 3).f("solidsGamma", s.solidsGamma, 3)
   .f("tempBeta", s.tempBeta, 4).f("tempRefC", cfg::kTempRefC, 1)
   .f("cellGain", s.cellGain, 4).f("saltK", s.saltK, 2)
   .f("tolerancePct", cfg::kTargetTolerance).u("maxRounds", cfg::kMaxAdjustRounds);
  emit(j);
}

void emitHello() {
  JsonLine j("hello");
  j.s("fw", cfg::kFirmwareId).s("name", blelink::deviceName()).s("cal", probe::calibrationName())
   .b("adc", probe::adcReady()).b("tempSensor", probe::temperatureReady())
   .b("oled", display::present()).b("tof", tof::present()).b("camera", cam::present())
   .b("psram", psramFound()).b("timeSet", epochOffset != 0)
   .u("records", store::recordCount())
   .b("temperatureCompensated", store::settings().tempBeta != 0.0f)
   .b("accuracyIndependentlyValidated", false);
  emit(j);
}

void emitSalinity() {
  char trials[64];
  snprintf(trials, sizeof(trials), "[%.5f,%.5f,%.5f]", salt.trials[0], salt.trials[1], salt.trials[2]);
  const store::Settings &s = store::settings();
  JsonLine j("salinity");
  j.u("seq", salt.seq).f("pct", salt.pct).f("tablePct", salt.tablePct)
   .f("index", salt.index, 5).f("tempC", salt.tempC).s("span", probe::spanName(salt.span))
   .raw("trials", trials).b("unstable", salt.unstable)
   .b("temperatureCompensated", s.tempBeta != 0.0f).f("cellGain", s.cellGain, 4)
   .s("cal", probe::calibrationName()).u("epoch", salt.epoch).u("uptimeMs", salt.atMs);
  emit(j);
}

model::Guide currentGuide() {
  if (!salt.valid || !isfinite(salt.pct)) return model::Guide{};
  model::Guide g = model::guide(store::settings(), salt.pct, freshBrothMl());
  // Split addition decided by the app: show only the share to add now.
  if (brothOverrideFresh() && stepRatio < 1.0f &&
      (g.kind == model::GuideKind::AddSalt || g.kind == model::GuideKind::AddWater))
    g.amount *= stepRatio;
  return g;
}

void emitGuide() {
  const model::Guide g = currentGuide();
  const float broth = freshBrothMl();
  const bool scanKnown = scanFresh() && scan.volume.valid;
  JsonLine j("guide");
  j.f("targetPct", store::settings().targetPct).f("currentPct", salt.valid ? salt.pct : NAN)
   .s("kind", model::guideName(g.kind))
   .f("amount", g.amount, g.kind == model::GuideKind::AddWater ? 0 : 1)
   .s("unit", g.kind == model::GuideKind::AddWater ? "mL" : "g")
   .b("perLiter", g.perLiter)
   .f("brothMl", broth, 0)
   .f("totalMl", scanKnown ? scan.volume.totalMl : NAN, 0)
   .s("brothSource", brothOverrideFresh() ? "app" : scanKnown ? "device" : "none")
   .f("stepRatio", brothOverrideFresh() ? stepRatio : 1.0f)
   .u("round", session.rounds).b("reached", session.reached).b("advise", session.advise);
  emit(j);
}

void emitScan() {
  char grid[400];
  size_t n = 0;
  grid[n++] = '[';
  for (uint8_t z = 0; z < tof::kZones; ++z)
    n += snprintf(grid + n, sizeof(grid) - n, z ? ",%d" : "%d", scan.frame.mm[z]);
  snprintf(grid + n, sizeof(grid) - n, "]");
  const model::Volume &v = scan.volume;
  JsonLine j("tof");
  j.f("surfaceMm", scan.frame.surfaceMm, 1).f("spreadMm", scan.frame.spreadMm, 1)
   .u("validZones", scan.frame.validZones).u("centerValid", scan.frame.centerValid)
   .f("floorMm", store::settings().floorMm, 1).f("fillMm", v.fillMm, 1)
   .f("totalMl", v.totalMl, 0).f("solidsMl", v.solidsMl, 0).f("brothMl", v.brothMl, 0)
   .s("note", v.note).raw("grid", grid);
  emit(j);
}

void emitRecord(const store::Record &r) {
  JsonLine j("record");
  j.u("seq", r.seq).u("epoch", r.epoch).f("pct", r.percent).f("index", r.index, 5)
   .f("tempC", r.tempC).f("brothMl", r.brothMl, 0).f("targetPct", r.targetPct)
   .s("span", probe::spanName(static_cast<probe::Span>(r.span)))
   .b("temperatureCompensated", r.flags & 1).b("cellCorrected", r.flags & 2)
   .b("unstable", r.flags & 4);
  emit(j);
}

// ---------------------------------------------------------------- actions

// S100 + S300. The acquisition runs with the R7.1 bus clock, with the camera off,
// the ToF idle, the buzzer silent and no display/BLE traffic until it is done.
bool doMeasure(const char *op) {
  showBusy("MEASURE", "WAIT ~4s", 0, "keep probe still");
  buzzer::play(buzzer::Pattern::Start);
  buzzer::finish();

  i2cMeasure();
  probe::SalinityResult r;
  const probe::Error error = probe::measureSalinity(r);
  probe::releaseDrive();
  i2cFast();
  buttons::flush();
  lastActivity = millis();
  dirty = true;

  if (error != probe::Error::None) {
    emitError(op, probe::errorCode(error),
              error == probe::Error::TempMissing ? "DS18B20 missing or invalid" :
              error == probe::Error::AdcMissing ? "ADS1115 not responding" :
              "drive/input/pulse validation failed; check probe immersion and wiring");
    buzzer::play(buzzer::Pattern::Error);
    toastFor("ERROR", probe::errorCode(error), 4000);
    return false;
  }

  salt = SaltState{};
  salt.valid = true;
  salt.seq = store::nextSeq();
  salt.atMs = millis();
  salt.epoch = nowEpoch();
  salt.index = r.index;
  salt.tempC = r.tempC;
  salt.span = r.span;
  for (uint8_t i = 0; i < 3; ++i) salt.trials[i] = r.trialIndex[i];
  const float lo = min(r.trialIndex[0], min(r.trialIndex[1], r.trialIndex[2]));
  const float hi = max(r.trialIndex[0], max(r.trialIndex[1], r.trialIndex[2]));
  salt.unstable = (hi - lo) > cfg::kTrialSpreadWarn;
  if (r.span != probe::Span::OutsideDomain) {
    salt.tablePct = r.percent;
    salt.pct = model::correct(store::settings(), r.percent, r.tempC);
  }
  emitSalinity();
  buzzer::play(r.span == probe::Span::OutsideDomain || salt.unstable ? buzzer::Pattern::Warn
                                                                      : buzzer::Pattern::Done);
  return true;
}

// S200 + S400 (ToF part). Returns false when no surface distance was obtained.
bool doTof() {
  showBusy("SCAN", "ToF...", 0, "");
  if (!tof::present()) {
    emitError("tof", "TOF_MISSING", "VL53L5CX not detected");
    return false;
  }
  tof::Frame frame;
  if (!tof::capture(frame)) {
    emitError("tof", "TOF_NO_SURFACE", "not enough valid zones");
    return false;
  }
  scan.valid = true;
  scan.atMs = millis();
  scan.frame = frame;
  scan.volume = model::estimate(store::settings(), frame.surfaceMm);
  emitScan();
  return true;
}

void dumpImageBase64() {
  // USB fallback so the camera can be tested without the phone app.
  const uint8_t *data = cam::data();
  const size_t size = cam::size();
  unsigned char out[80];
  size_t written = 0;
  uint32_t lineNo = 0;
  Serial.printf("IMG_B64_BEGIN id=%u bytes=%u crc32=%08lx\n", cam::id(), unsigned(size),
                (unsigned long)cam::crc32());
  for (size_t offset = 0; offset < size; offset += 57) {
    const size_t n = min<size_t>(57, size - offset);
    if (mbedtls_base64_encode(out, sizeof(out), &written, data + offset, n) != 0) break;
    out[written] = '\0';
    Serial.printf("IMG_B64 %lu %s\n", (unsigned long)lineNo++, out);
  }
  Serial.println("IMG_B64_END");
}

void sendImageChunks(const uint16_t *only, uint8_t onlyCount) {
  const uint8_t *data = cam::data();
  const size_t size = cam::size();
  if (!data || size == 0 || imageChunkBytes == 0) return;
  const uint32_t chunks = (size + imageChunkBytes - 1) / imageChunkBytes;
  uint32_t sent = 0;
  uint8_t lastPct = 255;
  const uint32_t total = onlyCount ? onlyCount : chunks;
  for (uint32_t k = 0; k < total; ++k) {
    const uint32_t index = onlyCount ? only[k] : k;
    if (index >= chunks) continue;
    const size_t offset = size_t(index) * imageChunkBytes;
    const size_t n = min<size_t>(imageChunkBytes, size - offset);
    if (!blelink::sendImageChunk(cam::id(), uint16_t(index), data + offset, n)) break;
    ++sent;
    const uint8_t pct = uint8_t(100 * (k + 1) / total);
    if (pct / 10 != lastPct / 10) {
      lastPct = pct;
      showBusy("SEND", "IMAGE", max<uint8_t>(pct, 1), "");
    }
  }
  JsonLine j("image_end");
  j.u("id", cam::id()).u("sent", sent).u("requested", total).b("complete", sent == total);
  emit(j);
}

void announceImage(Source src) {
  imageChunkBytes = uint16_t(blelink::imagePayloadBytes());
  const uint32_t chunks = (cam::size() + imageChunkBytes - 1) / imageChunkBytes;
  char crc[12];
  snprintf(crc, sizeof(crc), "%08lx", (unsigned long)cam::crc32());
  JsonLine j("image_begin");
  j.u("id", cam::id()).s("format", "jpeg").u("bytes", cam::size()).s("crc32", crc)
   .u("width", cam::width()).u("height", cam::height())
   .u("chunkBytes", imageChunkBytes).u("chunks", chunks)
   .b("ble", blelink::imageSubscribed()).b("usb", src == Source::Usb);
  emit(j);
  if (src == Source::Usb) dumpImageBase64();
  if (blelink::imageSubscribed()) sendImageChunks(nullptr, 0);
}

bool doPhoto(Source src, const char *size) {
  showBusy("SCAN", "CAMERA", 0, "");
  if (!cam::present()) {
    emitError("photo", "CAMERA_MISSING", cam::lastError());
    return false;
  }
  if (!cam::capture(size)) {
    emitError("photo", "CAPTURE_FAILED", cam::lastError());
    return false;
  }
  announceImage(src);
  return true;
}

void doScan(Source src, bool withPhoto, const char *size) {
  const bool tofOk = doTof();
  const bool photoOk = withPhoto ? doPhoto(src, size) : true;
  buttons::flush();
  lastActivity = millis();
  dirty = true;
  if (salt.valid) emitGuide();
  buzzer::play(tofOk && photoOk ? buzzer::Pattern::Done : buzzer::Pattern::Error);
  if (tofOk && !scan.volume.valid) toastFor("NO VOLUME", scan.volume.note, 3000);
}

void doSetFloor(float manualMm) {
  store::Settings &s = store::settings();
  if (isfinite(manualMm)) {
    s.floorMm = manualMm;
  } else {
    // Patent: empty-container distance stored as the reference offset (Dfloor).
    showBusy("FLOOR", "EMPTY BOWL", 0, "");
    tof::Frame frame;
    if (!tof::present() || !tof::capture(frame)) {
      emitError("floor", "TOF_NO_SURFACE", "point the sensor at the empty container");
      buzzer::play(buzzer::Pattern::Error);
      dirty = true;
      return;
    }
    s.floorMm = frame.surfaceMm;
  }
  store::saveSettings();
  scan.valid = false;
  char foot[22];
  snprintf(foot, sizeof(foot), "floor %.0f mm", s.floorMm);
  toast("FLOOR SET", foot);
  buzzer::play(buzzer::Pattern::Done);
  emitSettings();
}

void resetSession() { session = Session{}; }

void publishGuideWithSession() {
  const model::Guide g = currentGuide();
  if (g.kind == model::GuideKind::OnTarget) {
    session.reached = true;
    buzzer::play(buzzer::Pattern::Success);
    toastFor("ON TARGET", "adjustment complete", 3000);
  } else if (session.rounds >= cfg::kMaxAdjustRounds && g.kind != model::GuideKind::NoData) {
    session.advise = true;
    buzzer::play(buzzer::Pattern::Warn);
    toastFor("CHECK", "manual adj / calibrate", 4000);
  }
  emitGuide();
}

// S700: user added salt/water and mixed -> re-scan (if the floor is known) and re-measure.
void doRecheck() {
  ++session.rounds;
  session.reached = false;
  if (isfinite(store::settings().floorMm) && tof::present()) doTof();
  if (doMeasure("recheck")) publishGuideWithSession();
  screen = Screen::Guide;
}

void doSaveRecord() {
  if (!salt.valid) {
    toast("NO DATA", "measure first");
    buzzer::play(buzzer::Pattern::Error);
    return;
  }
  const store::Settings &s = store::settings();
  store::Record r = {};
  r.seq = salt.seq;
  r.epoch = salt.epoch;
  r.percent = salt.pct;
  r.index = float(salt.index);
  r.tempC = salt.tempC;
  r.brothMl = freshBrothMl();
  r.targetPct = s.targetPct;
  r.span = uint8_t(salt.span);
  r.flags = (s.tempBeta != 0.0f ? 1 : 0) | (s.cellGain != 1.0f ? 2 : 0) | (salt.unstable ? 4 : 0);
  store::appendRecord(r);
  salt.saved = true;
  emitRecord(r);
  char foot[22];
  snprintf(foot, sizeof(foot), "#%lu (%u stored)", (unsigned long)r.seq, store::recordCount());
  toast("SAVED", foot);
  buzzer::play(buzzer::Pattern::Done);
}

void sendHistory() {
  const uint8_t count = store::recordCount();
  store::Record r;
  for (uint8_t i = 0; i < count; ++i)
    if (store::getRecord(i, r)) emitRecord(r);
  JsonLine j("history_end");
  j.u("count", count);
  emit(j);
}

void changeTarget(float delta) {
  store::Settings &s = store::settings();
  s.targetPct = constrain(roundf((s.targetPct + delta) * 100.0f) / 100.0f, cfg::kTargetMin, cfg::kTargetMax);
  store::saveSettings();
  resetSession();
  dirty = true;
  emitGuide();
}

void syncToPhone() {
  emitHello();
  emitSettings();
  if (salt.valid) emitSalinity();
  if (scan.valid) emitScan();
  if (salt.valid) emitGuide();
}

// ---------------------------------------------------------------- commands

void handleCommand(char *line, Source src) {
  lastActivity = millis();
  display::setPower(true);
  dirty = true;

  char *tokens[12];
  uint8_t count = 0;
  for (char *t = strtok(line, " \t,"); t && count < 12; t = strtok(nullptr, " \t,")) tokens[count++] = t;
  if (count == 0) return;
  const char *cmd = tokens[0];
  auto is = [&](const char *name) { return strcasecmp(cmd, name) == 0; };
  auto arg = [&](uint8_t i) -> float { return i < count ? strtof(tokens[i], nullptr) : NAN; };
  store::Settings &s = store::settings();

  // R7.1 single-letter commands.
  if (is("m") || is("measure")) {
    resetSession();
    if (doMeasure("measure")) emitGuide();
  } else if (is("k") || is("raw")) {
    i2cMeasure();
    float index, tempC;
    const probe::Error e = probe::measureRawIndex(index, tempC);
    i2cFast();
    if (e != probe::Error::None) emitError("raw", probe::errorCode(e), "raw acquisition failed");
    else {
      JsonLine j("raw");
      j.f("index", index, 5).f("tempC", tempC).b("valueIsSalinity", false);
      emit(j);
    }
  } else if (is("t") || is("temp")) {
    float c;
    if (probe::readTemperature(c)) {
      Serial.printf("TEMP temp_C=%.2f\n", c);
      JsonLine j("temp");
      j.f("tempC", c);
      emit(j);
    } else {
      emitError("temp", "TEMP_MISSING", "DS18B20 missing or invalid");
    }
  } else if (is("p") || is("cal")) {
    probe::printCalibration();
    emitAck("cal");
  // Patent S200/S400.
  } else if (is("scan")) {
    doScan(src, true, count > 1 ? tokens[1] : "vga");
  } else if (is("tof")) {
    doScan(src, false, "");
  } else if (is("photo")) {
    doPhoto(src, count > 1 ? tokens[1] : "vga");
    buttons::flush();
  } else if (is("img")) {
    // img <id> [chunk ...] : resend chunks of the last image
    if (count < 2 || uint16_t(atoi(tokens[1])) != cam::id() || cam::size() == 0) {
      emitError("img", "IMAGE_EXPIRED", "only the latest image can be resent");
    } else {
      uint16_t only[10];
      uint8_t n = 0;
      for (uint8_t i = 2; i < count && n < 10; ++i) only[n++] = uint16_t(atoi(tokens[i]));
      sendImageChunks(n ? only : nullptr, n);
    }
  } else if (is("floor") || is("baseline")) {
    if (count > 1 && !strcasecmp(tokens[1], "clear")) {
      s.floorMm = NAN;
      store::saveSettings();
      emitSettings();
    } else {
      doSetFloor(arg(1));
    }
  } else if (is("bowl")) {
    // bowl round <top_mm> <bottom_mm> <depth_mm> | bowl rect <width_mm> <length_mm> <depth_mm>
    const bool rect = count > 1 && !strcasecmp(tokens[1], "rect");
    const float a = arg(2), b = arg(3), d = arg(4);
    if (count < 5 || !(a > 0 && b > 0 && d > 0)) {
      emitError("bowl", "BAD_ARGS", "bowl round|rect <a_mm> <b_mm> <depth_mm>");
    } else {
      s.bowlShape = rect ? store::BowlShape::Rect : store::BowlShape::Round;
      s.bowlAMm = a; s.bowlBMm = b; s.bowlDepthMm = d;
      store::saveSettings();
      if (scan.valid) scan.volume = model::estimate(s, scan.frame.surfaceMm);
      emitSettings();
    }
  } else if (is("solids")) {
    // solids <alpha> [gamma] : area ratio of solids from the phone's image analysis
    const float alpha = arg(1), gamma = count > 2 ? arg(2) : s.solidsGamma;
    if (!(alpha >= 0.0f && alpha <= 0.95f) || !(gamma >= 0.0f && gamma <= 2.0f)) {
      emitError("solids", "BAD_ARGS", "solids <alpha 0..0.95> [gamma 0..2]");
    } else {
      s.solidsAlpha = alpha;
      s.solidsGamma = gamma;
      store::saveSettings();
      if (scan.valid) scan.volume = model::estimate(s, scan.frame.surfaceMm);
      emitSettings();
      if (salt.valid) emitGuide();
    }
  // Patent S500..S700.
  } else if (is("target")) {
    const float t = arg(1);
    if (!(t >= cfg::kTargetMin && t <= cfg::kTargetMax)) {
      emitError("target", "BAD_ARGS", "target 0.3..3.0");
    } else {
      s.targetPct = t;
      store::saveSettings();
      resetSession();
      emitGuide();
    }
  } else if (is("guide")) {
    emitGuide();
  } else if (is("recheck") || is("added")) {
    doRecheck();
  // Sensor correction (patent: automatic sensor calibration).
  } else if (is("tcomp")) {
    const float beta = arg(1);
    if (!(beta >= 0.0f && beta <= 0.05f)) emitError("tcomp", "BAD_ARGS", "tcomp <beta 0..0.05 per C>, 0 = off");
    else { s.tempBeta = beta; store::saveSettings(); emitSettings(); }
  } else if (is("cellcal")) {
    // cellcal <known_pct> : one-point correction in a reference solution; cellcal reset
    if (count > 1 && !strcasecmp(tokens[1], "reset")) {
      s.cellGain = 1.0f;
      store::saveSettings();
      emitSettings();
    } else {
      const float known = arg(1);
      if (!(known > 0.1f && known < 5.0f)) {
        emitError("cellcal", "BAD_ARGS", "cellcal <known_pct> | cellcal reset");
      } else if (doMeasure("cellcal")) {
        if (!isfinite(salt.pct) || salt.pct <= 0.0f) {
          emitError("cellcal", "OUTSIDE_MODEL_DOMAIN", "reference reading outside the calibration model");
        } else {
          const float gain = s.cellGain * known / salt.pct;
          if (gain < cfg::kCellGainMin || gain > cfg::kCellGainMax) {
            emitError("cellcal", "OUT_OF_RANGE", "correction outside 0.7..1.3; check probe / solution");
          } else {
            s.cellGain = gain;
            store::saveSettings();
            emitSettings();
          }
        }
      }
    }
  } else if (is("broth")) {
    // broth <ml> [step_ratio] : broth volume and split ratio from the phone app; broth clear
    if (count > 1 && !strcasecmp(tokens[1], "clear")) {
      brothOverrideMl = NAN;
      stepRatio = 1.0f;
      emitAck("broth clear");
      if (salt.valid) emitGuide();
    } else {
      const float ml = arg(1);
      const float ratio = count > 2 ? arg(2) : 1.0f;
      if (!(ml > 0.0f && ml < 50000.0f) || !(ratio >= 0.1f && ratio <= 1.0f)) {
        emitError("broth", "BAD_ARGS", "broth <ml> [ratio 0.1..1] | broth clear");
      } else {
        brothOverrideMl = ml;
        brothOverrideAt = millis();
        stepRatio = ratio;
        if (salt.valid) emitGuide();
      }
    }
  } else if (is("saltk")) {
    const float k = arg(1);
    if (!(k > 1.0f && k < 50.0f)) emitError("saltk", "BAD_ARGS", "saltk <g per %p per L>");
    else { s.saltK = k; store::saveSettings(); emitSettings(); }
  // Records / housekeeping.
  } else if (is("save")) {
    doSaveRecord();
  } else if (is("history")) {
    if (count > 1 && !strcasecmp(tokens[1], "clear")) { store::clearRecords(); emitAck("history clear"); }
    else sendHistory();
  } else if (is("time")) {
    const double epoch = count > 1 ? strtod(tokens[1], nullptr) : 0;
    if (epoch < 1.6e9) emitError("time", "BAD_ARGS", "time <unix_epoch_seconds>");
    else { epochOffset = int64_t(epoch) - int64_t(millis() / 1000); emitAck("time"); }
  } else if (is("settings")) {
    emitSettings();
  } else if (is("factory")) {
    store::resetSettings();
    emitSettings();
  } else if (is("status") || is("hello") || is("sync")) {
    syncToPhone();
  } else if (is("beep")) {
    buzzer::play(buzzer::Pattern::Done);
    emitAck("beep");
  } else if (is("help") || is("?")) {
    Serial.println("Commands: m k t p | measure scan [qvga|vga|svga|xga] tof photo [size] img <id> [chunks]");
    Serial.println("  target <pct> guide recheck | floor [mm|clear] bowl round|rect a b depth solids <a> [g]");
    Serial.println("  tcomp <beta> cellcal <pct>|reset saltk <k> broth <ml> [ratio]|clear | save history [clear] time <epoch> settings status beep factory");
  } else {
    emitError("command", "UNKNOWN", cmd);
  }
}

// ---------------------------------------------------------------- buttons

void onButton(const buttons::Event &ev) {
  lastActivity = millis();
  dirty = true;
  if (!display::powered()) {  // first press only wakes the screen
    display::setPower(true);
    return;
  }
  buzzer::play(ev.press == buttons::Press::Long ? buzzer::Pattern::Long : buzzer::Pattern::Click);
  const bool isShort = ev.press == buttons::Press::Short;

  switch (ev.key) {
    case buttons::Key::Mode:
      if (isShort) screen = Screen((uint8_t(screen) + 1) % uint8_t(Screen::Count));
      else display::setPower(false);
      return;

    case buttons::Key::Measure:
      if (!isShort) {               // long: measure from any screen
        resetSession();
        if (doMeasure("measure")) emitGuide();
        screen = Screen::Salt;
        return;
      }
      switch (screen) {
        case Screen::Salt: resetSession(); if (doMeasure("measure")) emitGuide(); break;
        case Screen::Scan: doScan(Source::Button, true, "vga"); break;
        case Screen::Target: changeTarget(+cfg::kTargetStep); break;
        case Screen::Guide: doRecheck(); break;
        default: syncToPhone(); toast("SYNC", blelink::connected() ? "sent to phone" : "no phone"); break;
      }
      return;

    case buttons::Key::Save:
      if (!isShort) {
        if (screen == Screen::Scan) doSetFloor(NAN);
        else if (screen == Screen::Salt) sendHistory();
        return;
      }
      switch (screen) {
        case Screen::Salt: case Screen::Guide: doSaveRecord(); break;
        case Screen::Scan: doScan(Source::Button, false, ""); break;
        case Screen::Target: changeTarget(-cfg::kTargetStep); break;
        default: sendHistory(); break;
      }
      return;

    default:
      return;
  }
}

// ---------------------------------------------------------------- display

void render() {
  lastDraw = millis();
  dirty = false;
  if (!display::powered()) return;
  char right[16], big[12], foot[22];
  display::View v;
  const store::Settings &s = store::settings();

  if (isfinite(salt.tempC)) snprintf(right, sizeof(right), "%.1fC %s", salt.tempC, blelink::connected() ? "BT*" : "BT");
  else snprintf(right, sizeof(right), "%s", blelink::connected() ? "BT*" : "BT");
  v.right = right;
  v.title = kScreenTitle[uint8_t(screen)];
  big[0] = foot[0] = '\0';

  if (millis() < toastUntil) {
    v.big = toastBig;
    v.foot = toastFoot;
    display::draw(v);
    return;
  }

  switch (screen) {
    case Screen::Salt:
      if (!salt.valid) {
        strcpy(big, "--.--%");
        strcpy(foot, "K1 measure  K3 save");
      } else if (!isfinite(salt.pct)) {
        strcpy(big, "OUT RANGE");
        snprintf(foot, sizeof(foot), "index %.2f", salt.index);
      } else {
        snprintf(big, sizeof(big), "%.2f%%", salt.pct);
        const char *span = salt.span == probe::Span::In ? "in span" :
                           salt.span == probe::Span::Below ? "below span" : "above span";
        // Footer is 21 characters wide: an unstable flag replaces the span text.
        snprintf(foot, sizeof(foot), "%s%s", salt.unstable ? "UNSTABLE" : span,
                 salt.saved ? " saved" : "");
      }
      break;

    case Screen::Scan:
      if (scanFresh() && scan.volume.valid) {
        snprintf(big, sizeof(big), "%.0fmL", scan.volume.brothMl);
        snprintf(foot, sizeof(foot), "H%.0fmm a%.2f%s", scan.volume.fillMm, s.solidsAlpha,
                 cam::id() ? " img" : "");
      } else if (scanFresh()) {
        snprintf(big, sizeof(big), "%.0fmm", scan.frame.surfaceMm);
        strcpy(foot, isfinite(s.floorMm) ? "volume n/a" : "K3 hold: set floor");
      } else {
        strcpy(big, "--- mL");
        strcpy(foot, isfinite(s.floorMm) ? "K1 scan  K3 ToF" : "empty bowl: K3 hold");
      }
      break;

    case Screen::Target:
      snprintf(big, sizeof(big), "%.2f%%", s.targetPct);
      strcpy(foot, "K1 +0.1     K3 -0.1");
      break;

    case Screen::Guide: {
      const model::Guide g = currentGuide();
      switch (g.kind) {
        case model::GuideKind::AddSalt:
          snprintf(big, sizeof(big), g.perLiter ? "+%.1fg/L" : "+%.1fg", g.amount);
          break;
        case model::GuideKind::AddWater:
          snprintf(big, sizeof(big), g.perLiter ? "+%.0fmL/L" : "+%.0fmL", g.amount);
          break;
        case model::GuideKind::OnTarget: strcpy(big, "ON TARGET"); break;
        default: strcpy(big, "MEASURE"); break;
      }
      if (session.advise) strcpy(foot, "manual adj/calibrate");
      else if (g.kind == model::GuideKind::AddSalt) snprintf(foot, sizeof(foot), "SALT %.2f>%.2f%%", salt.pct, s.targetPct);
      else if (g.kind == model::GuideKind::AddWater) snprintf(foot, sizeof(foot), "WATER %.2f>%.2f%%", salt.pct, s.targetPct);
      else if (g.kind == model::GuideKind::OnTarget) snprintf(foot, sizeof(foot), "done (round %u)", session.rounds);
      else strcpy(foot, "SALT screen K1");
      if (session.rounds > 0 && !session.advise && g.kind != model::GuideKind::OnTarget) {
        const size_t len = strlen(foot);
        snprintf(foot + len, sizeof(foot) - len, " R%u", session.rounds);
      }
      break;
    }

    default:
      strcpy(big, blelink::connected() ? "CONNECTED" : "WAITING");
      snprintf(foot, sizeof(foot), "%s", blelink::deviceName());
      break;
  }
  v.big = big;
  v.foot = foot;
  display::draw(v);
}

void bootStep(const char *what) {
  display::View v;
  v.title = "BOOT";
  v.right = "R8.0";
  v.big = "SALT METER";
  v.foot = what;
  display::draw(v);
}

// ---------------------------------------------------------------- serial

char serialLine[160];
size_t serialLength = 0;
uint32_t serialLastByte = 0;

void pollSerial() {
  while (Serial.available()) {
    const char c = Serial.read();
    serialLastByte = millis();
    if (c == '\n' || c == '\r') {
      if (serialLength) {
        serialLine[serialLength] = '\0';
        serialLength = 0;
        handleCommand(serialLine, Source::Usb);
      }
    } else if (serialLength < sizeof(serialLine) - 1) {
      serialLine[serialLength++] = c;
    }
  }
  // R7.1 tools send a bare 'm' without a newline: accept a line after 50 ms of silence.
  if (serialLength && millis() - serialLastByte > 50) {
    serialLine[serialLength] = '\0';
    serialLength = 0;
    handleCommand(serialLine, Source::Usb);
  }
}

// ---------------------------------------------------------------- setup / loop

void setup() {
  // R7.1: ESP32 core 3.3.12 requires GPIO registration before digitalWrite.
  buzzer::begin();
  probe::releaseDrive();
  Serial.begin(115200);
  Wire.begin(cfg::kPinSda, cfg::kPinScl);
  i2cFast();

  display::begin();
  bootStep("storage");
  store::begin();
  buttons::begin();
  bootStep("probe");
  probe::begin();
  bootStep("ToF firmware");
  tof::begin();
  bootStep("camera");
  cam::detect();
  bootStep("bluetooth");
  blelink::begin();
  i2cFast();

  Serial.printf("READY %s cal=%s ble=%s adc=%d temp=%d oled=%d tof=%d camera=%d psram=%d. "
                "m=calibrated estimate(median3), k=raw response, p=calibration table, t=temperature, help=all commands. Drive idle.\n",
                cfg::kFirmwareId, probe::calibrationName(), blelink::deviceName(), probe::adcReady(),
                probe::temperatureReady(), display::present(), tof::present(), cam::present(), psramFound());
  emitHello();
  buzzer::play(probe::adcReady() ? buzzer::Pattern::Click : buzzer::Pattern::Error);
  lastActivity = millis();
  dirty = true;
}

void loop() {
  const uint32_t now = millis();
  buzzer::update(now);
  blelink::loop();

  // Phone just subscribed: push the current state.
  const bool subscribed = blelink::textSubscribed();
  if (subscribed != wasSubscribed) {
    wasSubscribed = subscribed;
    dirty = true;
    if (subscribed) syncToPhone();
  }

  pollSerial();
  char line[160];
  while (blelink::popCommand(line, sizeof(line))) handleCommand(line, Source::Ble);

  buttons::Event ev;
  if (buttons::poll(ev)) onButton(ev);

  if (display::powered() && now - lastActivity > cfg::kOledSleepMs) display::setPower(false);
  if (dirty || now - lastDraw > 1000) render();
  delay(2);
}
