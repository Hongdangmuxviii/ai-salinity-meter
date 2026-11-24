#include "Display.h"

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "Config.h"

namespace display {
namespace {

// clkDuring/clkAfter are both the fast clock. Salinity acquisition switches the
// bus to 100 kHz itself and never draws while it runs.
Adafruit_SSD1306 oled(cfg::kOledWidth, cfg::kOledHeight, &Wire, -1,
                      cfg::kI2cFastHz, cfg::kI2cFastHz);
bool ok = false;
bool on = true;

}  // namespace

bool begin() {
  // periphBegin=false: Wire is already started on D4/D5 by the sketch.
  ok = oled.begin(SSD1306_SWITCHCAPVCC, cfg::kOledAddress, true, false);
  if (!ok) return false;
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextWrap(false);
  oled.clearDisplay();
  oled.display();
  return true;
}

bool present() { return ok; }

void draw(const View &view) {
  if (!ok || !on) return;
  oled.clearDisplay();

  // Title: inverted block on the left, status text on the right.
  oled.setTextSize(1);
  const int titleWidth = int(strlen(view.title)) * 6 + 2;
  oled.fillRect(0, 0, titleWidth, 8, SSD1306_WHITE);
  oled.setTextColor(SSD1306_BLACK);
  oled.setCursor(1, 0);
  oled.print(view.title);
  oled.setTextColor(SSD1306_WHITE);
  const int rightWidth = int(strlen(view.right)) * 6;
  oled.setCursor(cfg::kOledWidth - rightWidth, 0);
  oled.print(view.right);

  oled.setTextSize(2);
  oled.setCursor(0, 9);
  oled.print(view.big);

  oled.setTextSize(1);
  if (view.progress > 0) {
    const int width = (cfg::kOledWidth - 2) * min<int>(view.progress, 100) / 100;
    oled.drawRect(0, 26, cfg::kOledWidth, 6, SSD1306_WHITE);
    oled.fillRect(1, 27, width, 4, SSD1306_WHITE);
  } else {
    oled.setCursor(0, 25);
    oled.print(view.foot);
  }
  oled.display();
}

void setPower(bool power) {
  if (!ok || power == on) return;
  on = power;
  oled.ssd1306_command(power ? SSD1306_DISPLAYON : SSD1306_DISPLAYOFF);
}

bool powered() { return on; }

}  // namespace display
