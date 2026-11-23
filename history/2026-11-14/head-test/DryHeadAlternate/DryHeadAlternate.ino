// Dry test with the 1 kOhm resistor still installed at D14–D18.
// XIAO D0 -> B10 (ADS A2), XIAO D1 -> B22 (ADS A3).
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;
constexpr uint8_t adsAddress = 0x48;

struct Readings {
  float volts[4];
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
      if (millis() - started >= 50) return false;
      delay(1);
    }
    readings.volts[channel] = ads.computeVolts(ads.getLastConversionResults());
  }
  return true;
}

void printReadings(const char *label, const Readings &readings) {
  Serial.printf("%s | A0=%.3f V  A1=%.3f V  A2=%.3f V  A3=%.3f V\n", label,
                readings.volts[0], readings.volts[1], readings.volts[2], readings.volts[3]);
}

bool checkDriveWiring() {
  Readings idle, pullD0, pullD1;
  delay(10);
  if (!readChannels(idle)) return false;
  printReadings("Precheck idle", idle);
  // The existing 10 kOhm resistors pull both drive nodes to ground.
  if (idle.volts[2] > 0.20f || idle.volts[3] > 0.20f) return false;

  // Weak pulls test the two connections before either pin drives an output.
  pinMode(D0, INPUT_PULLUP);
  delay(10);
  const bool readD0 = readChannels(pullD0);
  releaseDrive();
  if (!readD0) return false;
  printReadings("Precheck D0 weak pull", pullD0);
  if (pullD0.volts[2] - pullD0.volts[3] < 0.08f) return false;

  pinMode(D1, INPUT_PULLUP);
  delay(10);
  const bool readD1 = readChannels(pullD1);
  releaseDrive();
  if (!readD1) return false;
  printReadings("Precheck D1 weak pull", pullD1);
  return pullD1.volts[3] - pullD1.volts[2] >= 0.08f;
}

bool measurePhase(bool forward) {
  const uint8_t highPin = forward ? D0 : D1;
  const uint8_t lowPin = forward ? D1 : D0;
  pinMode(lowPin, OUTPUT);
  digitalWrite(lowPin, LOW);
  pinMode(highPin, OUTPUT);
  digitalWrite(highPin, HIGH);
  delay(10);

  Readings readings;
  const bool ok = readChannels(readings);
  digitalWrite(highPin, LOW);
  releaseDrive();
  if (!ok) {
    Serial.println("STOP: ADS1115 read failed.");
    return false;
  }

  printReadings(forward ? "D0 HIGH / D1 LOW " : "D0 LOW  / D1 HIGH", readings);
  const float high = readings.volts[forward ? 2 : 3];
  const float low = readings.volts[forward ? 3 : 2];
  const float span = high - low;
  const float nearHigh = readings.volts[forward ? 0 : 1];
  const float nearLow = readings.volts[forward ? 1 : 0];
  return high > 2.8f && low < 0.20f &&
         fabsf(nearHigh - (low + span * 2.0f / 3.0f)) <= 0.25f &&
         fabsf(nearLow - (low + span / 3.0f)) <= 0.25f;
}

bool ready = false;

void setup() {
  releaseDrive();
  Serial.begin(115200);
  Wire.begin(5, 6);
  Wire.setClock(100000);
  delay(1000);
  if (!ads.begin(adsAddress, &Wire)) {
    Serial.println("STOP: ADS1115 not found at 0x48.");
    return;
  }
  ads.setGain(GAIN_ONE);
  ready = checkDriveWiring();
  if (!ready) Serial.println("STOP: check D0 -> B10, D1 -> B22 and remove both temporary jumpers.");
}

void loop() {
  if (!ready) {
    Serial.println("Drive disabled. Press RESET after checking wiring to retry.");
    delay(2000);
    return;
  }

  ready = measurePhase(true);
  if (ready) {
    delay(50);
    ready = measurePhase(false);
  }
  Serial.println(ready ? "PASS: both directions match the dry resistor test."
                       : "STOP: measured voltages did not match the dry resistor test.");
  delay(1200);
}
