#pragma once
// Settings and measurement history in NVS (Preferences).
#include <Arduino.h>

namespace store {

enum class BowlShape : uint8_t { Round = 0, Rect = 1 };

struct Settings {
  uint32_t version;
  float targetPct;
  // ToF reference offset (patent: empty-container distance to the floor, Dfloor). NAN = unset.
  float floorMm;
  BowlShape bowlShape;
  // Round: top inner diameter, bottom inner diameter, depth (truncated cone).
  // Rect : width, length, depth (bottom ignored).
  float bowlAMm, bowlBMm, bowlDepthMm;
  // Solids correction from image analysis: Vsolid = Vtotal * alpha * gamma.
  float solidsAlpha, solidsGamma;
  float tempBeta;   // per degC; 0 = temperature compensation off
  float cellGain;   // one-point reference-solution correction, 1 = off
  float saltK;      // g per (%p * L)
};

struct Record {
  uint32_t seq;
  uint32_t epoch;      // 0 when the phone has not set the time
  float percent;       // reported (corrected) salinity
  float index;         // median response index
  float tempC;
  float brothMl;       // NAN when no recent scan
  float targetPct;
  uint8_t span;        // probe::Span
  uint8_t flags;       // bit0 temp-compensated, bit1 cell-corrected, bit2 unstable
  uint8_t reserved[2];
};

void begin();
Settings &settings();
void saveSettings();
void resetSettings();

uint32_t nextSeq();
void appendRecord(const Record &record);
uint8_t recordCount();
bool getRecord(uint8_t indexFromOldest, Record &record);
void clearRecords();

}  // namespace store
