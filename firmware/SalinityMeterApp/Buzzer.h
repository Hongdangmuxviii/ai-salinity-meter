#pragma once
// ONE005 active buzzer on D9 (HIGH = sound). Non-blocking pattern player.
#include <Arduino.h>

namespace buzzer {

enum class Pattern : uint8_t { Click, Long, Start, Done, Success, Error, Warn };

void begin();                 // drives D9 LOW (R7.1 order: pinMode then digitalWrite)
void play(Pattern pattern);
void update(uint32_t now);
void stop();                  // silence immediately
void finish();                // block until the current pattern ends (short patterns only)
bool busy();

}  // namespace buzzer
