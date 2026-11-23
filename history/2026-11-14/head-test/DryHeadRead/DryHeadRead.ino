// Dry resistor test only. No probes or water; D0 and D1 stay disconnected.
// Board: XIAO ESP32S3 Sense. Libraries: Adafruit ADS1X15 and Adafruit BusIO.
// B10 -> 3V3, B22 -> GND, with a 1 kOhm test resistor at D14-D18.
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;
bool connected = false;

void setup() {
  Serial.begin(115200);
  Wire.begin(5, 6);  // XIAO D4 = GPIO5 SDA; D5 = GPIO6 SCL.
  Wire.setClock(100000);
  delay(1000);
  connected = ads.begin(0x48, &Wire);
  if (connected) ads.setGain(GAIN_ONE);
}

void loop() {
  if (!connected) {
    Serial.println("ADS1115 not found at 0x48: check ADDR and four wires.");
    delay(1000);
    return;
  }
  Serial.print("Dry test: ");
  for (uint8_t ch = 0; ch < 4; ++ch) {
    const int16_t raw = ads.readADC_SingleEnded(ch);
    Serial.printf("A%u=%.3f V  ", (unsigned)ch, (double)ads.computeVolts(raw));
  }
  Serial.println();
  delay(1000);
}
