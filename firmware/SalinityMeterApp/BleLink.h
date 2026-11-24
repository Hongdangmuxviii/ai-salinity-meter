#pragma once
// BLE GATT link to the phone (NimBLE-Arduino 2.x).
//  - Nordic UART Service: RX (write) = text commands, TX (notify) = newline-delimited JSON.
//    Generic BLE terminal apps (nRF Connect, nRF Toolbox UART, Serial Bluetooth Terminal)
//    can drive the device before the dedicated app exists.
//  - Image service: one notify characteristic with binary JPEG chunks
//    [u16 imageId LE][u16 chunkIndex LE][payload].
#include <Arduino.h>

namespace blelink {

void begin();
void loop();                       // keeps advertising while disconnected
const char *deviceName();
bool connected();
bool textSubscribed();
bool imageSubscribed();
uint16_t mtu();

// Commands written by the phone, one line at a time (queued from the BLE task).
bool popCommand(char *out, size_t length);

// Sends `line` + '\n' split into MTU-sized notifications. No-op when not subscribed.
bool sendLine(const char *line);
size_t imagePayloadBytes();        // payload per image chunk for the current MTU
bool sendImageChunk(uint16_t imageId, uint16_t index, const uint8_t *data, size_t length);

}  // namespace blelink
