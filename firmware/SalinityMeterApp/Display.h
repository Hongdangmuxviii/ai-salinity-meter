#pragma once
// SSD1306 128x32 at 0x3C. Three rows: title (8 px), large value (16 px), footer (8 px).
#include <Arduino.h>

namespace display {

struct View {
  const char *title = "";   // left of the top row, drawn inverted
  const char *right = "";   // right of the top row (link / temperature)
  const char *big = "";     // 2x text, up to 10 characters
  const char *foot = "";    // bottom row, up to 21 characters
  uint8_t progress = 0;     // 0 = none, 1..100 draws a bar instead of the footer
};

bool begin();
bool present();
void draw(const View &view);
void setPower(bool on);
bool powered();

}  // namespace display
