#pragma once
// Patent P2026-070 calculations: broth volume (S400) and addition guide (S500-S600).
#include <Arduino.h>

#include "Storage.h"

namespace model {

struct Volume {
  bool valid = false;
  float fillMm = NAN;      // H = Dfloor - Dsurface
  float totalMl = NAN;     // Vtotal from the container shape
  float solidsMl = NAN;    // Vsolid = Vtotal * alpha * gamma
  float brothMl = NAN;     // Vbroth = Vtotal - Vsolid
  const char *note = "";
};

Volume estimate(const store::Settings &s, float surfaceMm);

enum class GuideKind : uint8_t { NoData, AddSalt, AddWater, OnTarget };

struct Guide {
  GuideKind kind = GuideKind::NoData;
  float amount = NAN;      // g of salt or mL of water
  bool perLiter = false;   // true when the broth volume is unknown: amount per 1 L
  float deltaPct = NAN;    // target - current
};

// Eq.1 Wsalt = (St - Sc) * Vbroth[L] * K ; Eq.2 Vwater = Vbroth * (Sc/St - 1)
Guide guide(const store::Settings &s, float currentPct, float brothMl);

// Temperature (beta, Tref) and one-point cell correction applied to the table estimate.
float correct(const store::Settings &s, float tablePct, float tempC);

const char *guideName(GuideKind kind);

}  // namespace model
