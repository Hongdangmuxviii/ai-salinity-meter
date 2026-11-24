#pragma once
// SparkFun SEN-19013 VL53L5CX (8x8 multizone ToF) on the shared I2C bus.
#include <Arduino.h>

namespace tof {

constexpr uint8_t kZones = 64;

struct Frame {
  int16_t mm[kZones];        // per-zone median of the retained frames, -1 = no valid target
  uint8_t validZones = 0;
  uint8_t centerValid = 0;   // valid zones in the central 4x4
  float surfaceMm = NAN;     // robust distance to the surface (median of centre zones)
  float spreadMm = NAN;      // interquartile range of the zones used (tilt / noise hint)
};

// Uploads the sensor firmware (~2-3 s at 400 kHz). Returns false if absent.
bool begin();
bool present();
// Ranges a few 8x8 frames and stops. Not used during salinity acquisition.
bool capture(Frame &frame, uint32_t timeoutMs = 2000);

}  // namespace tof
