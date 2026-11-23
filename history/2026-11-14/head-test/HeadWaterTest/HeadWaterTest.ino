// Head response test. Send 'm' over USB to measure five polarity pairs.
// D0 -> B10 (ADS A2), D1 -> B22 (ADS A3), probe -> C14/C18 (ADS A0/A1).
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>

Adafruit_ADS1115 ads;
OneWire temperatureBus(D3);
DallasTemperature temperatureSensor(&temperatureBus);
DeviceAddress temperatureAddress;
bool temperatureFound = false;
constexpr uint8_t adsAddress = 0x48;
constexpr unsigned long pulseMs = 20;
constexpr uint8_t pairCount = 5;

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

void setup() {
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
    Serial.println("READY: t=temperature only, m=temperature and probe response. Drive idle between commands.");
  }
}

void loop() {
  if (!Serial.available()) {
    delay(1);
    return;
  }
  const char command = Serial.read();
  if (command != 't' && command != 'm') return;

  float celsius;
  if (!readTemperature(celsius)) return;
  if (command == 't') {
    Serial.printf("TEMP temp_C=%.2f\n", celsius);
    return;
  }
  if (!ready) {
    Serial.println("STOP: ADS1115 missing at 0x48. Check wiring and reset.");
    return;
  }
  runMeasurement(celsius);
}
