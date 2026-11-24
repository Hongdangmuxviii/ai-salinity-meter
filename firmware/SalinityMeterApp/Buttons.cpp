#include "Buttons.h"

#include "Config.h"

namespace buttons {
namespace {

struct State {
  uint8_t pin;
  bool stablePressed;
  bool lastRaw;
  uint32_t rawChanged;
  uint32_t pressedAt;
  bool longFired;
};

State states[3] = {
  {cfg::kPinKeyMeasure, false, false, 0, 0, false},
  {cfg::kPinKeyMode, false, false, 0, 0, false},
  {cfg::kPinKeySave, false, false, 0, 0, false},
};

bool readPressed(uint8_t pin) { return digitalRead(pin) == LOW; }

}  // namespace

void begin() {
  // R9..R11 (10k) are the designed pull-ups. The internal pull-up is enabled as
  // well so a partly assembled board (no button harness) reads "released"
  // instead of floating and firing random measurements. In parallel with 10k it
  // changes nothing on the finished board. GPIO43 carries ROM boot log output
  // before this point; it is an input from here on.
  for (State &s : states) {
    pinMode(s.pin, INPUT_PULLUP);
    s.lastRaw = readPressed(s.pin);
    s.stablePressed = s.lastRaw;
    s.rawChanged = millis();
    s.longFired = s.stablePressed;  // a key held through boot does not fire
  }
}

bool poll(Event &event) {
  const uint32_t now = millis();
  for (uint8_t i = 0; i < 3; ++i) {
    State &s = states[i];
    const bool raw = readPressed(s.pin);
    if (raw != s.lastRaw) {
      s.lastRaw = raw;
      s.rawChanged = now;
    }
    if (raw != s.stablePressed && now - s.rawChanged >= cfg::kDebounceMs) {
      s.stablePressed = raw;
      if (raw) {
        s.pressedAt = now;
        s.longFired = false;
      } else if (!s.longFired) {
        event = {static_cast<Key>(i), Press::Short};
        return true;
      }
    }
    if (s.stablePressed && !s.longFired && now - s.pressedAt >= cfg::kLongPressMs) {
      s.longFired = true;
      event = {static_cast<Key>(i), Press::Long};
      return true;
    }
  }
  return false;
}

void flush() {
  for (State &s : states) {
    s.lastRaw = readPressed(s.pin);
    s.stablePressed = s.lastRaw;
    s.rawChanged = millis();
    s.longFired = s.stablePressed;
  }
}

bool anyHeld() {
  for (const State &s : states)
    if (s.stablePressed) return true;
  return false;
}

}  // namespace buttons
