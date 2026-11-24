// Head response test. Send 'm' over USB to measure five polarity pairs.
// R7 MVP: D0/D1 -> R1/R2 -> E1/E2; J7 -> ADS A0:A..A3:A.
// Battery display omitted; D10 unwired. Sense resistors/J3 remain intact.
// SD/shared SPI unused. Boot buzzer chirp is acceptable.
// USB-C charging uses the onboard charger; battery ADC is not used.
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "CalibrationTable.h"

Adafruit_ADS1115 ads;
OneWire temperatureBus(D3);
DallasTemperature temperatureSensor(&temperatureBus);
DeviceAddress temperatureAddress;
bool temperatureFound = false;
constexpr uint8_t adsAddress = 0x48;
constexpr unsigned long pulseMs = 20;
constexpr uint8_t pairCount = 5;

struct DifferentialPhase {
  bool forward;
  float early, late, drive;
  unsigned long earlyEndUs, lateEndUs, driveEndUs, pulseEndUs;
};

struct Readings {
  float volts[4];
};

struct ElectricalRecord {
  uint8_t state, trial, order;
  float volts[4];
  uint16_t config[4];
  unsigned long endUs[4], pulseUs;
};

void releaseDrive() {
  pinMode(D0, INPUT);
  pinMode(D1, INPUT);
}

bool readChannels(Readings &readings) {
  for (uint8_t channel = 0; channel < 4; ++channel) {
    Wire.beginTransmission(adsAddress);
    if (Wire.endTransmission() != 0) return false;

    ads.startADCReading(MUX_BY_CHANNEL[channel], false);
    const unsigned long started = millis();
    while (!ads.conversionComplete()) {
      if (millis() - started >= 8) return false;
      delay(1);
    }
    readings.volts[channel] = ads.computeVolts(ads.getLastConversionResults());
  }
  return true;
}

bool weakPullCheck(uint8_t pin, uint8_t nearChannel, uint8_t farChannel) {
  pinMode(pin, INPUT_PULLUP);
  delay(5);
  Readings readings;
  const bool ok = readChannels(readings);
  releaseDrive();
  return ok && readings.volts[nearChannel] - readings.volts[farChannel] >= 0.04f;
}

bool checkDriveWiring() {
  Readings idle;
  return readChannels(idle) && idle.volts[2] < 0.20f && idle.volts[3] < 0.20f &&
         weakPullCheck(D0, 2, 3) && weakPullCheck(D1, 3, 2);
}

bool measurePhase(bool forward, float &response) {
  const uint8_t highPin = forward ? D0 : D1;
  const uint8_t lowPin = forward ? D1 : D0;
  pinMode(lowPin, OUTPUT);
  digitalWrite(lowPin, LOW);
  pinMode(highPin, OUTPUT);
  digitalWrite(highPin, HIGH);

  const unsigned long started = millis();
  delay(3);
  Readings readings;
  const bool ok = readChannels(readings);
  const unsigned long elapsed = millis() - started;
  if (ok && elapsed < pulseMs) delay(pulseMs - elapsed);
  digitalWrite(highPin, LOW);
  releaseDrive();
  if (!ok || elapsed > pulseMs) return false;

  const float driveHigh = readings.volts[forward ? 2 : 3];
  const float driveLow = readings.volts[forward ? 3 : 2];
  const float driveSpan = driveHigh - driveLow;
  if (driveHigh < 2.8f || driveLow > 0.20f) return false;

  const float probeSpan = fabsf(readings.volts[0] - readings.volts[1]);
  Serial.printf("PHASE %s A0=%.3f A1=%.3f A2=%.3f A3=%.3f V\n",
                forward ? "D0+" : "D1+", readings.volts[0], readings.volts[1],
                readings.volts[2], readings.volts[3]);
  // Dimensionless percentage of the drive voltage dropped across the series resistors.
  response = constrain(100.0f * (1.0f - probeSpan / driveSpan), 0.0f, 100.0f);
  return true;
}

bool readTemperature(float &celsius) {
  temperatureSensor.setCheckForConversion(false);
  if (!temperatureFound) {
    temperatureSensor.begin();
    temperatureFound = temperatureSensor.getAddress(temperatureAddress, 0) &&
                       temperatureAddress[0] == DS18B20MODEL;
    if (temperatureFound) temperatureSensor.setResolution(temperatureAddress, 12);
  }
  if (!temperatureFound || !temperatureSensor.requestTemperaturesByAddress(temperatureAddress)) {
    temperatureFound = false;
    Serial.println("STOP: DS18B20 missing. Check red=3V3, black=GND, yellow=D3.");
    return false;
  }

  celsius = temperatureSensor.getTempC(temperatureAddress);
  if (!isfinite(celsius) || celsius < -55.0f || celsius > 125.0f) {
    temperatureFound = false;
    Serial.println("STOP: DS18B20 reading failed. Check temperature wiring.");
    return false;
  }
  return true;
}

void runMeasurement(float celsius) {
  if (!checkDriveWiring()) {
    Serial.println("STOP: ADC or drive wiring check failed.");
    return;
  }

  float forwardTotal = 0.0f;
  float reverseTotal = 0.0f;
  float minimum = 100.0f;
  float maximum = 0.0f;
  for (uint8_t pair = 0; pair < pairCount; ++pair) {
    float forward, reverse;
    if (!measurePhase(true, forward) || !measurePhase(false, reverse)) {
      Serial.println("STOP: invalid ADC reading or pulse.");
      return;
    }
    forwardTotal += forward;
    reverseTotal += reverse;
    const float average = (forward + reverse) / 2.0f;
    minimum = min(minimum, average);
    maximum = max(maximum, average);
    delay(50);
  }

  const float forward = forwardTotal / pairCount;
  const float reverse = reverseTotal / pairCount;
  Serial.printf("RESULT temp_C=%.2f  response=%.2f / 100  D0+=%.2f  D1+=%.2f  range=%.2f..%.2f\n",
                celsius, (forward + reverse) / 2.0f, forward, reverse, minimum, maximum);
}

bool ready = false;

// Signed differential diagnosis. A0-A1 is converted directly by the ADC,
// instead of subtracting two single-ended readings taken at different times.
// All serial output is deferred until the balanced pulse train has ended.
bool differentialRead(uint16_t mux, float &volts) {
  ads.startADCReading(mux, false);
  const unsigned long started = micros();
  while (!ads.conversionComplete()) {
    if (micros() - started >= 5000) return false;
    delayMicroseconds(100);
  }
  const int16_t counts = ads.getLastConversionResults();
  if (counts == INT16_MAX || counts == INT16_MIN) return false;
  volts = ads.computeVolts(counts);
  return true;
}

void waitPhaseTime(unsigned long started, unsigned long targetUs) {
  while (micros() - started < targetUs) delayMicroseconds(50);
}

bool differentialPhase(bool forward, DifferentialPhase &sample) {
  const uint8_t highPin = forward ? D0 : D1;
  const uint8_t lowPin = forward ? D1 : D0;
  digitalWrite(lowPin, LOW);
  digitalWrite(highPin, LOW);
  pinMode(lowPin, OUTPUT);
  pinMode(highPin, OUTPUT);
  digitalWrite(highPin, HIGH);
  const unsigned long started = micros();
  sample.forward = forward;

  waitPhaseTime(started, 3000);
  bool ok = differentialRead(ADS1X15_REG_CONFIG_MUX_DIFF_0_1, sample.early);
  sample.earlyEndUs = micros() - started;
  if (ok && sample.earlyEndUs < 9000) {
    waitPhaseTime(started, 9000);
    ok = differentialRead(ADS1X15_REG_CONFIG_MUX_DIFF_0_1, sample.late);
    sample.lateEndUs = micros() - started;
  } else ok = false;
  if (ok && sample.lateEndUs < 14000) {
    waitPhaseTime(started, 14000);
    ok = differentialRead(ADS1X15_REG_CONFIG_MUX_DIFF_2_3, sample.drive);
    sample.driveEndUs = micros() - started;
  } else ok = false;
  if (ok && sample.driveEndUs < 20000) waitPhaseTime(started, 20000);
  else ok = false;

  digitalWrite(highPin, LOW);
  releaseDrive();
  sample.pulseEndUs = micros() - started;
  delayMicroseconds(1000);  // Equal idle interval after either polarity.
  return ok && sample.pulseEndUs < 22000 &&
         (forward ? sample.drive > 2.8f : sample.drive < -2.8f) &&
         fabsf(sample.drive) < 3.6f;
}

void runDifferential(bool reverseFirst, float celsius) {
  if (!checkDriveWiring()) {
    releaseDrive();
    Serial.println("STOP: differential preflight wiring check failed.");
    return;
  }
  DifferentialPhase samples[16] = {};
  delay(100);
  bool ok = true;
  for (uint8_t i = 0; i < 16; ++i) {
    const bool forward = ((i % 2) == 0) != reverseFirst;
    if (!differentialPhase(forward, samples[i])) {
      ok = false;
      break;
    }
  }
  releaseDrive();
  if (!ok) {
    Serial.println("STOP: differential conversion, timing or drive validation failed; drive released.");
    return;
  }
  Serial.printf("DIAG_BEGIN version=SIGNED_DIFF_V1 temp_C=%.2f first=%s pulse_target_us=20000 idle_us=1000\n",
                celsius, reverseFirst ? "D1+" : "D0+");
  for (uint8_t i = 0; i < 16; ++i) {
    const DifferentialPhase &s = samples[i];
    Serial.printf("DIFF pair=%u phase=%s early_V=%.6f late_V=%.6f drive_V=%.6f early_end_us=%lu late_end_us=%lu drive_end_us=%lu pulse_us=%lu\n",
                  unsigned(i / 2 + 1), s.forward ? "D0+" : "D1+",
                  s.early, s.late, s.drive, s.earlyEndUs, s.lateEndUs,
                  s.driveEndUs, s.pulseEndUs);
  }
  Serial.println("DIAG_END drive=INPUT");
}

// A shorter, fixed pulse train. The first 24 pairs warm up the response;
// all samples are retained so convergence can be assessed, not presumed.
void runFastDifferential(bool reverseFirst, float celsius) {
  if (!checkDriveWiring()) {
    releaseDrive();
    Serial.println("STOP: fast differential preflight failed.");
    return;
  }
  float values[64] = {};
  unsigned long ends[64] = {};
  unsigned long durations[64] = {};
  bool ok = true;
  delay(100);
  for (uint8_t i = 0; i < 64; ++i) {
    const bool forward = ((i % 2) == 0) != reverseFirst;
    const uint8_t highPin = forward ? D0 : D1;
    const uint8_t lowPin = forward ? D1 : D0;
    digitalWrite(lowPin, LOW);
    digitalWrite(highPin, LOW);
    pinMode(lowPin, OUTPUT);
    pinMode(highPin, OUTPUT);
    digitalWrite(highPin, HIGH);
    const unsigned long started = micros();
    waitPhaseTime(started, 3000);
    ok = differentialRead(ADS1X15_REG_CONFIG_MUX_DIFF_0_1, values[i]);
    ends[i] = micros() - started;
    if (ok && ends[i] < 8000) waitPhaseTime(started, 8000);
    else ok = false;
    digitalWrite(highPin, LOW);
    releaseDrive();
    durations[i] = micros() - started;
    delayMicroseconds(1000);
    if (!ok || durations[i] >= 10000) { ok = false; break; }
  }
  releaseDrive();
  if (!ok) {
    Serial.println("STOP: fast differential conversion or timing failed; drive released.");
    return;
  }
  Serial.printf("FAST_BEGIN version=SIGNED_DIFF_V2 temp_C=%.2f first=%s pulse_target_us=8000 idle_us=1000 warmup_pairs=24 retained_pairs=8\n",
                celsius, reverseFirst ? "D1+" : "D0+");
  for (uint8_t i = 0; i < 64; ++i) {
    const bool forward = ((i % 2) == 0) != reverseFirst;
    Serial.printf("FAST pair=%u phase=%s probe_V=%.6f sample_end_us=%lu pulse_us=%lu\n",
                  unsigned(i / 2 + 1), forward ? "D0+" : "D1+", values[i], ends[i], durations[i]);
  }
  Serial.println("FAST_END drive=INPUT");
}

// Reconstruct the repetitive waveform at fixed conversion call offsets.
// Each block has the same pulse cadence for both polarities, a 24-pair warmup,
// and eight retained pairs. Timings are software call/result timings, not a
// claim about the exact internal ADC integration window. No salinity is output.
void runTimingSweep(float celsius) {
  if (!checkDriveWiring()) {
    releaseDrive();
    Serial.println("STOP: timing sweep preflight failed.");
    return;
  }
  const unsigned long widths[] = {6000, 8000, 20000};
  const unsigned long offsets[3][6] = {
    {0, 1500, 3000, 0, 0, 0},
    {0, 2000, 4000, 0, 0, 0},
    {0, 3000, 6000, 9000, 12000, 15000}
  };
  const uint8_t offsetCounts[] = {3, 3, 6};
  Serial.printf("SWEEP_BEGIN version=SIGNED_DIFF_V3 temp_C=%.2f warmup_pairs=24 retained_pairs=8 idle_us=1000\n", celsius);
  for (uint8_t w = 0; w < 3; ++w) {
    for (uint8_t offset = 0; offset < offsetCounts[w]; ++offset) {
      float values[64] = {};
      unsigned long starts[64] = {}, ends[64] = {}, durations[64] = {};
      bool ok = true;
      delay(100);
      Wire.beginTransmission(adsAddress);
      if (Wire.endTransmission() != 0) {
        Serial.println("STOP: ADC lost before sweep block.");
        return;
      }
      for (uint8_t i = 0; i < 64; ++i) {
        const bool forward = (i % 2) == 0;
        const uint8_t highPin = forward ? D0 : D1;
        const uint8_t lowPin = forward ? D1 : D0;
        digitalWrite(lowPin, LOW);
        digitalWrite(highPin, LOW);
        pinMode(lowPin, OUTPUT);
        pinMode(highPin, OUTPUT);
        digitalWrite(highPin, HIGH);
        const unsigned long started = micros();
        waitPhaseTime(started, offsets[w][offset]);
        starts[i] = micros() - started;
        ok = differentialRead(ADS1X15_REG_CONFIG_MUX_DIFF_0_1, values[i]);
        ends[i] = micros() - started;
        if (ok && ends[i] < widths[w]) waitPhaseTime(started, widths[w]);
        else ok = false;
        digitalWrite(highPin, LOW);
        releaseDrive();
        durations[i] = micros() - started;
        delayMicroseconds(1000);
        if (!ok || durations[i] > widths[w] + 2000) { ok = false; break; }
      }
      releaseDrive();
      Wire.beginTransmission(adsAddress);
      if (!ok || Wire.endTransmission() != 0) {
        Serial.println("STOP: sweep block conversion, connection or timing failed; drive released.");
        return;
      }
      for (uint8_t i = 0; i < 64; ++i) {
        if (i >= 2 && i < 48) continue;
        Serial.printf("SWEEP width_us=%lu offset_us=%lu pair=%u phase=%s probe_V=%.6f sample_start_us=%lu sample_end_us=%lu pulse_us=%lu\n",
                      widths[w], offsets[w][offset], unsigned(i / 2 + 1),
                      (i % 2) == 0 ? "D0+" : "D1+", values[i], starts[i], ends[i], durations[i]);
      }
    }
  }
  releaseDrive();
  Serial.println("SWEEP_END drive=INPUT");
}

bool checkedRegister(uint8_t address, uint16_t &value) {
  Wire.beginTransmission(adsAddress);
  Wire.write(address);
  if (Wire.endTransmission() != 0) return false;
  if (Wire.requestFrom(adsAddress, uint8_t(2)) != 2) return false;
  value = (uint16_t(Wire.read()) << 8) | uint16_t(Wire.read());
  return true;
}

// A separate electrical diagnostic. Existing m/d/e/f/g/s acquisition remains
// unchanged. Both-equal states check common-mode loading; opposite states
// retain equal pulse counts. Every active state is bounded to about20ms.
// This command intentionally does not require the temperature probe.
void runElectricalCheck() {
  releaseDrive();
  if (!checkDriveWiring()) {
    Serial.println("STOP: electrical-check preflight failed.");
    return;
  }
  ElectricalRecord records[24] = {};
  // LL, HL, LH, HH: D0 first, D1 second.
  const bool high0[] = {false, true, false, true};
  const bool high1[] = {false, false, true, true};
  const char *names[] = {"LL", "HL", "LH", "HH"};
  uint8_t used = 0;
  bool ok = true;
  for (uint8_t trial = 0; trial < 3 && ok; ++trial) {
    for (uint8_t order = 0; order < 2 && ok; ++order) {
      for (uint8_t state = 0; state < 4 && ok; ++state) {
        ElectricalRecord &record = records[used];
        record.state = state; record.trial = trial + 1; record.order = order;
        digitalWrite(D0, LOW); digitalWrite(D1, LOW);
        pinMode(D0, OUTPUT); pinMode(D1, OUTPUT);
        digitalWrite(D0, high0[state] ? HIGH : LOW);
        digitalWrite(D1, high1[state] ? HIGH : LOW);
        const unsigned long started = micros();
        waitPhaseTime(started, 3000);
        for (uint8_t step = 0; step < 4; ++step) {
          const uint8_t channel = order == 0 ? step : 3 - step;
          ok = differentialRead(MUX_BY_CHANNEL[channel], record.volts[channel]);
          record.endUs[channel] = micros() - started;
          if (!ok || !checkedRegister(ADS1X15_REG_POINTER_CONFIG, record.config[channel])) { ok = false; break; }
          const uint16_t expected = MUX_BY_CHANNEL[channel] |
            ADS1X15_REG_CONFIG_PGA_4_096V | ADS1X15_REG_CONFIG_MODE_SINGLE |
            RATE_ADS1115_860SPS | ADS1X15_REG_CONFIG_OS_SINGLE;
          const uint16_t mask = ADS1X15_REG_CONFIG_MUX_MASK |
            ADS1X15_REG_CONFIG_PGA_MASK | ADS1X15_REG_CONFIG_MODE_MASK |
            0x00E0 | ADS1X15_REG_CONFIG_OS_SINGLE;
          if ((record.config[channel] & mask) != (expected & mask) || micros() - started >= 20000) { ok = false; break; }
        }
        if (ok) waitPhaseTime(started, 20000);
        digitalWrite(D0, LOW); digitalWrite(D1, LOW);
        releaseDrive();
        record.pulseUs = micros() - started;
        if (record.pulseUs >= 22000) ok = false;
        ++used;
        delay(50);
      }
    }
  }
  releaseDrive();
  Serial.println("ELECTRICAL_BEGIN version=SIGNED_DIFF_V3_C1 temp_read=false same_wiring=true");
  for (uint8_t i = 0; i < used; ++i) {
    const ElectricalRecord &r = records[i];
    Serial.printf("ELECTRICAL trial=%u state=%s order=%s A0=%.6f A1=%.6f A2=%.6f A3=%.6f cfg0=%04x cfg1=%04x cfg2=%04x cfg3=%04x end0_us=%lu end1_us=%lu end2_us=%lu end3_us=%lu pulse_us=%lu\n",
      unsigned(r.trial), names[r.state], r.order == 0 ? "0123" : "3210",
      r.volts[0], r.volts[1], r.volts[2], r.volts[3],
      unsigned(r.config[0]), unsigned(r.config[1]), unsigned(r.config[2]), unsigned(r.config[3]),
      r.endUs[0], r.endUs[1], r.endUs[2], r.endUs[3], r.pulseUs);
  }
  Serial.println(ok ? "ELECTRICAL_END complete=true drive=INPUT" :
                      "STOP: electrical check conversion/config/timing failed; drive=INPUT");
}

// Current-derived response using R2 voltage, not the intermittent A0 sense.
// I*R2 = A1-A3, Vdrive=A2-A3. With R1=R2=1k:
// index=100*(R1+R2)/R2 * (A1-A3)/(A2-A3).
// This is a dimensionless, time-dependent response, not salinity percent.
// A0 conversion is retained only to preserve the historical A1 sampling time;
// its value does not enter the calculation. Existing m/s remain unchanged.
bool measureCurrentPhase(bool forward, float &response) {
  const uint8_t highPin = forward ? D0 : D1;
  const uint8_t lowPin = forward ? D1 : D0;
  pinMode(lowPin, OUTPUT);
  digitalWrite(lowPin, LOW);
  pinMode(highPin, OUTPUT);
  digitalWrite(highPin, HIGH);

  const unsigned long started = millis();
  delay(3);
  Readings readings;
  const bool ok = readChannels(readings);
  const unsigned long elapsed = millis() - started;
  if (ok && elapsed < pulseMs) delay(pulseMs - elapsed);
  digitalWrite(highPin, LOW);
  releaseDrive();
  if (!ok || elapsed > pulseMs) return false;

  const float driveHigh = readings.volts[forward ? 2 : 3];
  const float driveLow = readings.volts[forward ? 3 : 2];
  if (driveHigh < 2.8f || driveLow > 0.20f || driveLow < -0.05f) return false;
  if (readings.volts[1] < driveLow - 0.05f ||
      readings.volts[1] > driveHigh + 0.05f) return false;
  const float signedDrive = readings.volts[2] - readings.volts[3];
  const float signedSense = readings.volts[1] - readings.volts[3];
  const float ratio = signedSense / signedDrive;
  if (!isfinite(ratio) || ratio < -0.02f || ratio > 1.02f) return false;

  Serial.printf("PHASE %s A0=%.3f A1=%.3f A2=%.3f A3=%.3f V\n",
                forward ? "D0+" : "D1+", readings.volts[0], readings.volts[1],
                readings.volts[2], readings.volts[3]);
  // Do not absolute-value or clip the result: electrode transients can
  // produce values above100; those must remain visible in the record.
  response = 200.0f * ratio;
  return true;
}

float lastCurrentIndex = NAN;

void runCurrentMeasurement(float celsius) {
  lastCurrentIndex = NAN;
  // The weak-pull open-circuit check is not a reliable precondition for a
  // polarized immersed cell. Actual high/low drive and A1 range are checked
  // on every bounded measurement phase instead.
  releaseDrive();
  Wire.beginTransmission(adsAddress);
  if (Wire.endTransmission() != 0) {
    Serial.println("STOP: current measurement ADC not responding.");
    return;
  }
  float forwardTotal = 0.0f, reverseTotal = 0.0f;
  float minimum = 1e9f, maximum = -1e9f;
  for (uint8_t pair = 0; pair < pairCount; ++pair) {
    float forward, reverse;
    if (!measureCurrentPhase(true, forward) || !measureCurrentPhase(false, reverse)) {
      releaseDrive();
      Serial.println("STOP: current input, drive or pulse validation failed.");
      return;
    }
    forwardTotal += forward;
    reverseTotal += reverse;
    const float average = (forward + reverse) / 2.0f;
    minimum = min(minimum, average);
    maximum = max(maximum, average);
    delay(50);
  }
  const float forward = forwardTotal / pairCount;
  const float reverse = reverseTotal / pairCount;
  lastCurrentIndex = (forward + reverse) / 2.0f;
  Serial.printf("CURRENT_RESULT temp_C=%.2f index=%.5f D0+=%.5f D1+=%.5f range=%.5f..%.5f A0_in_calculation=false value_is_salinity=false\n",
                celsius, (forward + reverse) / 2.0f, forward, reverse, minimum, maximum);
}


double interpolateCalibration(double index) {
  unsigned int segment=0;
  while (segment<calibrationPointCount-2 && index>calibrationIndices[segment+1]) ++segment;
  const double x0=calibrationIndices[segment], x1=calibrationIndices[segment+1];
  const double y0=calibrationPercents[segment], y1=calibrationPercents[segment+1];
  return y0+(index-x0)*(y1-y0)/(x1-x0);
}

void printCalibration() {
  Serial.printf("CAL_TABLE id=%s points=4 aggregation=median3 temperature_compensated=false accuracy_independently_validated=false\n",calibrationId);
  for (unsigned int i=0;i<calibrationPointCount;++i)
    Serial.printf("CAL_POINT i=%u reference_percent=%.1f response_index=%.8f reference_temp_C=%.2f\n",i,calibrationPercents[i],calibrationIndices[i],calibrationTemperatures[i]);
}

void runCalibratedMeasurement() {
  float indices[3], temperatures[3];
  for (uint8_t i=0; i<3; ++i) {
    if (!readTemperature(temperatures[i])) return;
    runCurrentMeasurement(temperatures[i]);
    if (!isfinite(lastCurrentIndex)) return;
    indices[i]=lastCurrentIndex;
    delay(200);
  }
  if (indices[0]>indices[1]) { float t=indices[0]; indices[0]=indices[1]; indices[1]=t; }
  if (indices[1]>indices[2]) { float t=indices[1]; indices[1]=indices[2]; indices[2]=t; }
  if (indices[0]>indices[1]) { float t=indices[0]; indices[0]=indices[1]; indices[1]=t; }
  const double index=indices[1];
  if (!(index>0.0 && index<100.0)) {
    Serial.printf("SALINITY_RESULT response_index=%.5f status=OUTSIDE_MODEL_DOMAIN drive=INPUT\n",index);
    return;
  }
  const double estimatedPercent=interpolateCalibration(index);
  const char *status=index<calibrationIndexLow ? "BELOW_REFERENCE_SPAN" :
                     index>calibrationIndexHigh ? "ABOVE_REFERENCE_SPAN" : "IN_REFERENCE_SPAN";
  Serial.printf("SALINITY_RESULT estimate_percent=%.2f response_index=%.5f temp_C=%.2f status=%s calibration_id=%s median_of=3 temperature_compensated=false accuracy_independently_validated=false\n",
    estimatedPercent,index,temperatures[2],status,calibrationId);
}

void setup() {
  // R7.1: ESP32 core 3.3.12 requires GPIO registration before digitalWrite.
  // Boot chirp is accepted; set the active-HIGH buzzer LOW before peripheral setup.
  pinMode(D9, OUTPUT);
  digitalWrite(D9, LOW);
  releaseDrive();
  Serial.begin(115200);
  Wire.begin(5, 6);
  Wire.setClock(100000);
  Wire.setTimeOut(5);
  temperatureSensor.begin();
  temperatureFound = temperatureSensor.getAddress(temperatureAddress, 0) &&
                     temperatureAddress[0] == DS18B20MODEL;
  if (temperatureFound) temperatureSensor.setResolution(temperatureAddress, 12);
  ready = ads.begin(adsAddress, &Wire);
  if (ready) {
    ads.setGain(GAIN_ONE);
    ads.setDataRate(RATE_ADS1115_860SPS);
    Serial.println("READY SALINITY_CAL_4P_V1: m=calibrated estimate(median3), k=raw response, p=calibration table, t=temperature. Drive idle.");
  }
}

void loop() {
  if (!Serial.available()) { delay(1); return; }
  const char command=Serial.read();
  if (command=='p') { printCalibration(); return; }
  if (command!='m' && command!='k' && command!='t') return;
  if (command=='m') {
    if (ready) runCalibratedMeasurement();
    else Serial.println("STOP: ADS1115 missing.");
    return;
  }
  float celsius;
  if (!readTemperature(celsius)) return;
  if (command=='t') { Serial.printf("TEMP temp_C=%.2f\n",celsius); return; }
  if (!ready) { Serial.println("STOP: ADS1115 missing."); return; }
  runCurrentMeasurement(celsius);
}

