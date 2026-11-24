#include "Storage.h"

#include <Preferences.h>

#include "Config.h"

namespace store {
namespace {

constexpr uint32_t kSettingsVersion = 0x53410001;  // bump when Settings changes
constexpr char kNamespace[] = "saltmeter";

Preferences prefs;
Settings current;
Record ring[cfg::kHistoryCapacity];
uint8_t head = 0;    // next write position
uint8_t count = 0;
uint32_t seq = 0;

void defaults(Settings &s) {
  s.version = kSettingsVersion;
  s.targetPct = cfg::kTargetDefault;
  s.floorMm = NAN;
  s.bowlShape = BowlShape::Round;
  s.bowlAMm = cfg::kBowlTopDefaultMm;
  s.bowlBMm = cfg::kBowlBottomDefaultMm;
  s.bowlDepthMm = cfg::kBowlDepthDefaultMm;
  s.solidsAlpha = 0.0f;
  s.solidsGamma = 1.0f;
  s.tempBeta = cfg::kTempBetaDefault;
  s.cellGain = 1.0f;
  s.saltK = cfg::kSaltKDefault;
}

void saveHistory() {
  prefs.putBytes("hist", ring, sizeof(ring));
  prefs.putUChar("head", head);
  prefs.putUChar("count", count);
}

}  // namespace

void begin() {
  prefs.begin(kNamespace, false);
  defaults(current);
  Settings stored;
  if (prefs.getBytesLength("settings") == sizeof(Settings) &&
      prefs.getBytes("settings", &stored, sizeof(stored)) == sizeof(stored) &&
      stored.version == kSettingsVersion) {
    current = stored;
  }
  if (prefs.getBytesLength("hist") == sizeof(ring)) {
    prefs.getBytes("hist", ring, sizeof(ring));
    head = prefs.getUChar("head", 0) % cfg::kHistoryCapacity;
    count = min<uint8_t>(prefs.getUChar("count", 0), cfg::kHistoryCapacity);
  }
  seq = prefs.getUInt("seq", 0);
}

Settings &settings() { return current; }

void saveSettings() { prefs.putBytes("settings", &current, sizeof(current)); }

void resetSettings() {
  defaults(current);
  saveSettings();
}

uint32_t nextSeq() {
  ++seq;
  prefs.putUInt("seq", seq);
  return seq;
}

void appendRecord(const Record &record) {
  ring[head] = record;
  head = (head + 1) % cfg::kHistoryCapacity;
  if (count < cfg::kHistoryCapacity) ++count;
  saveHistory();
}

uint8_t recordCount() { return count; }

bool getRecord(uint8_t indexFromOldest, Record &record) {
  if (indexFromOldest >= count) return false;
  const uint8_t oldest = (head + cfg::kHistoryCapacity - count) % cfg::kHistoryCapacity;
  record = ring[(oldest + indexFromOldest) % cfg::kHistoryCapacity];
  return true;
}

void clearRecords() {
  head = 0;
  count = 0;
  memset(ring, 0, sizeof(ring));
  saveHistory();
}

}  // namespace store
