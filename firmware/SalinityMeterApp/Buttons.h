#pragma once
// KEY1..KEY3: external pull-up, active LOW. Debounced short / long press.
#include <Arduino.h>

namespace buttons {

enum class Key : uint8_t { Measure = 0, Mode = 1, Save = 2, Count = 3 };
enum class Press : uint8_t { None, Short, Long };

struct Event {
  Key key;
  Press press;
};

void begin();
// Returns true and fills `event` when a press completes (Short on release,
// Long as soon as the hold time is reached).
bool poll(Event &event);
// Drop presses that happened while the main loop was blocked.
void flush();
bool anyHeld();

}  // namespace buttons
