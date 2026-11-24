// Ported from firmware/SalinityMeterCalibrated/SalinityMeterCalibrated.ino (R7.1).
// Only the m/k/t/p paths reachable from the R7.1 loop are kept; the unused
// diagnostic routines remain in the repository history.
// Measurement-critical code (readChannels, measureCurrentPhase,
// runCurrentMeasurement, interpolateCalibration, median of 3) is kept line-for-line,
// apart from returning an error code instead of only printing STOP.
#include "SalinityProbe.h"

#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#include "CalibrationTable.h"
#include "Config.h"

namespace probe {
namespace {

Adafruit_ADS1115 ads;
OneWire temperatureBus(cfg::kPinTempDq);
DallasTemperature temperatureSensor(&temperatureBus);
DeviceAddress temperatureAddress;
bool temperatureFound = false;
bool ready = false;
constexpr uint8_t adsAddress = cfg::kAdsAddress;
constexpr unsigned long pulseMs = 20;
constexpr uint8_t pairCount = 5;

struct Readings {
  float volts[4];
};

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

// Current-derived response using R2 voltage, not the intermittent A0 sense.
// I*R2 = A1-A3, Vdrive=A2-A3. With R1=R2=1k:
// index=100*(R1+R2)/R2 * (A1-A3)/(A2-A3).
// This is a dimensionless, time-dependent response, not salinity percent.
// A0 conversion is retained only to preserve the historical A1 sampling time.
bool measureCurrentPhase(bool forward, float &response) {
  const uint8_t highPin = forward ? cfg::kPinDriveA : cfg::kPinDriveB;
  const uint8_t lowPin = forward ? cfg::kPinDriveB : cfg::kPinDriveA;
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
  // produce values above 100; those must remain visible in the record.
  response = 200.0f * ratio;
  return true;
}

Error runCurrentMeasurement(float celsius, float &index) {
  index = NAN;
  releaseDrive();
  Wire.beginTransmission(adsAddress);
  if (Wire.endTransmission() != 0) {
    Serial.println("STOP: current measurement ADC not responding.");
    return Error::AdcMissing;
  }
  float forwardTotal = 0.0f, reverseTotal = 0.0f;
  float minimum = 1e9f, maximum = -1e9f;
  for (uint8_t pair = 0; pair < pairCount; ++pair) {
    float forward, reverse;
    if (!measureCurrentPhase(true, forward) || !measureCurrentPhase(false, reverse)) {
      releaseDrive();
      Serial.println("STOP: current input, drive or pulse validation failed.");
      return Error::DriveInvalid;
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
  index = (forward + reverse) / 2.0f;
  Serial.printf("CURRENT_RESULT temp_C=%.2f index=%.5f D0+=%.5f D1+=%.5f range=%.5f..%.5f A0_in_calculation=false value_is_salinity=false\n",
                celsius, (forward + reverse) / 2.0f, forward, reverse, minimum, maximum);
  return Error::None;
}

double interpolateCalibration(double index) {
  unsigned int segment = 0;
  while (segment < calibrationPointCount - 2 && index > calibrationIndices[segment + 1]) ++segment;
  const double x0 = calibrationIndices[segment], x1 = calibrationIndices[segment + 1];
  const double y0 = calibrationPercents[segment], y1 = calibrationPercents[segment + 1];
  return y0 + (index - x0) * (y1 - y0) / (x1 - x0);
}

}  // namespace

void releaseDrive() {
  pinMode(cfg::kPinDriveA, INPUT);
  pinMode(cfg::kPinDriveB, INPUT);
}

bool begin() {
  releaseDrive();
  temperatureSensor.begin();
  temperatureFound = temperatureSensor.getAddress(temperatureAddress, 0) &&
                     temperatureAddress[0] == DS18B20MODEL;
  if (temperatureFound) temperatureSensor.setResolution(temperatureAddress, 12);
  ready = ads.begin(adsAddress, &Wire);
  if (ready) {
    ads.setGain(GAIN_ONE);
    ads.setDataRate(RATE_ADS1115_860SPS);
  }
  return ready;
}

bool adcReady() { return ready; }
bool temperatureReady() { return temperatureFound; }

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

Error measureRawIndex(float &index, float &tempC) {
  index = NAN;
  if (!readTemperature(tempC)) return Error::TempMissing;
  if (!ready) {
    Serial.println("STOP: ADS1115 missing.");
    return Error::AdcMissing;
  }
  return runCurrentMeasurement(tempC, index);
}

Error measureSalinity(SalinityResult &out) {
  out = SalinityResult{};
  if (!ready) {
    Serial.println("STOP: ADS1115 missing.");
    return Error::AdcMissing;
  }
  float indices[3], temperatures[3];
  for (uint8_t i = 0; i < 3; ++i) {
    if (!readTemperature(temperatures[i])) return Error::TempMissing;
    const Error error = runCurrentMeasurement(temperatures[i], indices[i]);
    if (error != Error::None) return error;
    if (!isfinite(indices[i])) return Error::DriveInvalid;
    out.trialIndex[i] = indices[i];
    delay(200);
  }
  if (indices[0] > indices[1]) { float t = indices[0]; indices[0] = indices[1]; indices[1] = t; }
  if (indices[1] > indices[2]) { float t = indices[1]; indices[1] = indices[2]; indices[2] = t; }
  if (indices[0] > indices[1]) { float t = indices[0]; indices[0] = indices[1]; indices[1] = t; }
  const double index = indices[1];
  out.index = index;
  out.tempC = temperatures[2];
  if (!(index > 0.0 && index < 100.0)) {
    out.span = Span::OutsideDomain;
    Serial.printf("SALINITY_RESULT response_index=%.5f status=OUTSIDE_MODEL_DOMAIN drive=INPUT\n", index);
    return Error::None;
  }
  const double estimatedPercent = interpolateCalibration(index);
  out.percent = static_cast<float>(estimatedPercent);
  out.span = index < calibrationIndexLow ? Span::Below :
             index > calibrationIndexHigh ? Span::Above : Span::In;
  Serial.printf("SALINITY_RESULT estimate_percent=%.2f response_index=%.5f temp_C=%.2f status=%s calibration_id=%s median_of=3 temperature_compensated=false accuracy_independently_validated=false\n",
                estimatedPercent, index, temperatures[2], spanName(out.span), calibrationId);
  return Error::None;
}

void printCalibration() {
  Serial.printf("CAL_TABLE id=%s points=4 aggregation=median3 temperature_compensated=false accuracy_independently_validated=false\n", calibrationId);
  for (unsigned int i = 0; i < calibrationPointCount; ++i)
    Serial.printf("CAL_POINT i=%u reference_percent=%.1f response_index=%.8f reference_temp_C=%.2f\n",
                  i, calibrationPercents[i], calibrationIndices[i], calibrationTemperatures[i]);
}

const char *spanName(Span span) {
  switch (span) {
    case Span::Below: return "BELOW_REFERENCE_SPAN";
    case Span::In: return "IN_REFERENCE_SPAN";
    case Span::Above: return "ABOVE_REFERENCE_SPAN";
    default: return "OUTSIDE_MODEL_DOMAIN";
  }
}

const char *errorCode(Error error) {
  switch (error) {
    case Error::None: return "NONE";
    case Error::AdcMissing: return "ADC_MISSING";
    case Error::TempMissing: return "TEMP_MISSING";
    default: return "DRIVE_INVALID";
  }
}

const char *calibrationName() { return calibrationId; }

}  // namespace probe
