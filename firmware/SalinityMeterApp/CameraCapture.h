#pragma once
// XIAO ESP32-S3 Sense camera (OV2640 / OV3660) -> JPEG kept in PSRAM until the
// next capture so the phone can request missing chunks again.
// Requires the board option PSRAM = "OPI PSRAM".
#include <Arduino.h>

namespace cam {

bool detect();               // init + deinit once at boot
bool present();
// size: "qvga" 320x240, "vga" 640x480 (default), "svga" 800x600, "xga" 1024x768, "uxga" 1600x1200
bool capture(const char *size);
const uint8_t *data();
size_t size();
uint16_t id();               // increments per successful capture
uint32_t crc32();            // standard CRC-32 (zlib) of the JPEG
uint16_t width();
uint16_t height();
const char *lastError();

uint32_t crc32Of(const uint8_t *data, size_t length);

}  // namespace cam
