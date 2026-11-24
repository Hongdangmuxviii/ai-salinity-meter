#pragma once
// Salinity acquisition ported from SalinityMeterCalibrated R7.1.
// Pulse timing, ADC sequence, validation limits, median-of-3 aggregation and the
// calibration table are unchanged. The legacy serial lines (PHASE, CURRENT_RESULT,
// SALINITY_RESULT, TEMP, CAL_*) are still printed so existing logs/scripts work.
#include <Arduino.h>

namespace probe {

enum class Span : uint8_t { Below, In, Above, OutsideDomain };

enum class Error : uint8_t {
  None,
  AdcMissing,        // ADS1115 did not answer
  TempMissing,       // DS18B20 not found / reading failed
  DriveInvalid,      // drive, input or pulse validation failed
};

struct SalinityResult {
  float percent = NAN;      // calibrated estimate (only valid when span != OutsideDomain)
  double index = NAN;       // median response index C = 200*(A1-A3)/(A2-A3)
  float trialIndex[3] = {NAN, NAN, NAN};
  float tempC = NAN;        // temperature of the last trial (same as legacy output)
  Span span = Span::OutsideDomain;
};

bool begin();               // ADS1115 + DS18B20; drive released
bool adcReady();
bool temperatureReady();

// Legacy 'm': three acquisitions, median, piecewise-linear table.
Error measureSalinity(SalinityResult &out);
// Legacy 'k': one raw acquisition (not salinity).
Error measureRawIndex(float &index, float &tempC);
// Legacy 't'.
bool readTemperature(float &celsius);
// Legacy 'p'.
void printCalibration();

void releaseDrive();
const char *spanName(Span span);
const char *errorCode(Error error);
const char *calibrationName();

}  // namespace probe
