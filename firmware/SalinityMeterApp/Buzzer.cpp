#include "Buzzer.h"

#include "Config.h"

namespace buzzer {
namespace {

// Alternating on/off durations in ms, terminated by 0.
const uint16_t kClick[] = {25, 0};
const uint16_t kLong[] = {120, 0};
const uint16_t kStart[] = {40, 0};
const uint16_t kDone[] = {70, 70, 70, 0};
const uint16_t kSuccess[] = {60, 60, 60, 60, 250, 0};
const uint16_t kError[] = {450, 0};
const uint16_t kWarn[] = {150, 100, 150, 0};

const uint16_t *current = nullptr;
uint8_t step = 0;
uint32_t stepStarted = 0;

void output(bool on) { digitalWrite(cfg::kPinBuzzer, on ? HIGH : LOW); }

const uint16_t *lookup(Pattern pattern) {
  switch (pattern) {
    case Pattern::Click: return kClick;
    case Pattern::Long: return kLong;
    case Pattern::Start: return kStart;
    case Pattern::Done: return kDone;
    case Pattern::Success: return kSuccess;
    case Pattern::Error: return kError;
    default: return kWarn;
  }
}

}  // namespace

void begin() {
  pinMode(cfg::kPinBuzzer, OUTPUT);
  digitalWrite(cfg::kPinBuzzer, LOW);
}

void play(Pattern pattern) {
  current = lookup(pattern);
  step = 0;
  stepStarted = millis();
  output(true);
}

void update(uint32_t now) {
  if (!current) return;
  if (now - stepStarted < current[step]) return;
  ++step;
  stepStarted = now;
  if (current[step] == 0) {
    stop();
    return;
  }
  output((step % 2) == 0);
}

void stop() {
  current = nullptr;
  output(false);
}

bool busy() { return current != nullptr; }

void finish() {
  const uint32_t started = millis();
  while (busy() && millis() - started < 1500) {
    update(millis());
    delay(1);
  }
  stop();
}

}  // namespace buzzer
