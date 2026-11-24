#include "SaltModel.h"

#include "Config.h"

namespace model {

Volume estimate(const store::Settings &s, float surfaceMm) {
  Volume v;
  if (!isfinite(s.floorMm)) { v.note = "floor reference not set"; return v; }
  if (!isfinite(surfaceMm)) { v.note = "no surface distance"; return v; }
  float h = s.floorMm - surfaceMm;
  if (h < -3.0f) { v.note = "surface below floor reference"; return v; }
  if (h > s.bowlDepthMm * 1.1f) { v.note = "fill above container depth"; return v; }
  h = constrain(h, 0.0f, s.bowlDepthMm);
  v.fillMm = h;

  double mm3;
  if (s.bowlShape == store::BowlShape::Rect) {
    mm3 = double(s.bowlAMm) * s.bowlBMm * h;
  } else {
    // Truncated cone: r(h) grows linearly from the bottom radius to the top radius.
    const double rb = s.bowlBMm / 2.0, rt = s.bowlAMm / 2.0;
    const double rh = rb + (rt - rb) * (s.bowlDepthMm > 0 ? h / s.bowlDepthMm : 0.0);
    mm3 = PI * h * (rb * rb + rb * rh + rh * rh) / 3.0;
  }
  v.totalMl = float(mm3 / 1000.0);
  const float alpha = constrain(s.solidsAlpha, 0.0f, 0.95f);
  const float gamma = constrain(s.solidsGamma, 0.0f, 2.0f);
  v.solidsMl = v.totalMl * alpha * gamma;
  v.brothMl = max(0.0f, v.totalMl - v.solidsMl);
  v.valid = true;
  return v;
}

Guide guide(const store::Settings &s, float currentPct, float brothMl) {
  Guide g;
  const float target = s.targetPct;
  if (!isfinite(currentPct) || !(target > 0.0f)) return g;
  g.deltaPct = target - currentPct;
  if (fabsf(g.deltaPct) <= cfg::kTargetTolerance) {
    g.kind = GuideKind::OnTarget;
    g.amount = 0.0f;
    return g;
  }
  g.perLiter = !(isfinite(brothMl) && brothMl > 0.0f);
  const float liters = g.perLiter ? 1.0f : brothMl / 1000.0f;
  if (g.deltaPct > 0.0f) {
    g.kind = GuideKind::AddSalt;
    g.amount = g.deltaPct * liters * s.saltK;                 // g
  } else {
    g.kind = GuideKind::AddWater;
    g.amount = liters * (currentPct / target - 1.0f) * 1000;  // mL
  }
  return g;
}

float correct(const store::Settings &s, float tablePct, float tempC) {
  if (!isfinite(tablePct)) return tablePct;
  float pct = tablePct * s.cellGain;
  if (s.tempBeta != 0.0f && isfinite(tempC)) {
    const float factor = 1.0f + s.tempBeta * (tempC - cfg::kTempRefC);
    if (factor > 0.2f) pct /= factor;
  }
  return pct;
}

const char *guideName(GuideKind kind) {
  switch (kind) {
    case GuideKind::AddSalt: return "ADD_SALT";
    case GuideKind::AddWater: return "ADD_WATER";
    case GuideKind::OnTarget: return "ON_TARGET";
    default: return "NO_DATA";
  }
}

}  // namespace model
