#include "TofSensor.h"

#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>

#include "Config.h"

namespace tof {
namespace {

SparkFun_VL53L5CX sensor;
VL53L5CX_ResultsData results;
bool ok = false;

constexpr uint8_t kFramesUsed = 3;   // after one discarded warm-up frame

// Status 5 = valid range, 9 = valid with large pulse (ST UM2884).
bool validStatus(uint8_t status) { return status == 5 || status == 9; }

void sortSmall(int16_t *values, uint8_t count) {
  for (uint8_t i = 1; i < count; ++i) {
    const int16_t v = values[i];
    int8_t j = i - 1;
    while (j >= 0 && values[j] > v) { values[j + 1] = values[j]; --j; }
    values[j + 1] = v;
  }
}

bool waitFrame(uint32_t started, uint32_t timeoutMs) {
  while (!sensor.isDataReady()) {
    if (millis() - started > timeoutMs) return false;
    delay(5);
  }
  return sensor.getRangingData(&results);
}

}  // namespace

bool begin() {
  // The library allocates its I2C helper inside begin(); calling
  // setWireMaxPacketSize() before that dereferences a null pointer and panics.
  ok = sensor.begin(cfg::kTofAddress, Wire);
  if (!ok) return false;
  sensor.setWireMaxPacketSize(128);
  ok = sensor.setResolution(8 * 8) && sensor.setRangingFrequency(15);
  return ok;
}

bool present() { return ok; }

bool capture(Frame &frame, uint32_t timeoutMs) {
  frame = Frame{};
  if (!ok) return false;
  if (!sensor.startRanging()) return false;

  int16_t samples[kZones][kFramesUsed];
  uint8_t counts[kZones] = {};
  const uint32_t started = millis();
  bool good = waitFrame(started, timeoutMs);  // discard first frame
  for (uint8_t f = 0; good && f < kFramesUsed; ++f) {
    good = waitFrame(started, timeoutMs);
    if (!good) break;
    for (uint8_t z = 0; z < kZones; ++z) {
      if (validStatus(results.target_status[z]) && results.distance_mm[z] > 0)
        samples[z][counts[z]++] = results.distance_mm[z];
    }
  }
  sensor.stopRanging();
  if (!good) return false;

  int16_t used[kZones];
  uint8_t usedCount = 0;
  int16_t all[kZones];
  uint8_t allCount = 0;
  for (uint8_t z = 0; z < kZones; ++z) {
    if (counts[z] == 0) { frame.mm[z] = -1; continue; }
    sortSmall(samples[z], counts[z]);
    frame.mm[z] = samples[z][counts[z] / 2];
    ++frame.validZones;
    all[allCount++] = frame.mm[z];
    const uint8_t row = z / 8, col = z % 8;
    if (row >= 2 && row <= 5 && col >= 2 && col <= 5) {
      used[usedCount++] = frame.mm[z];
      ++frame.centerValid;
    }
  }
  // Patent: statistical processing of the surface zones (centre median) to damp
  // tilt and noise. Fall back to all valid zones when the centre is mostly invalid.
  int16_t *pick = used;
  uint8_t pickCount = usedCount;
  if (usedCount < 4) { pick = all; pickCount = allCount; }
  if (pickCount < 4) return false;
  sortSmall(pick, pickCount);
  frame.surfaceMm = pick[pickCount / 2];
  frame.spreadMm = pick[(pickCount * 3) / 4] - pick[pickCount / 4];
  return true;
}

}  // namespace tof
