#pragma once
// R7 MVP wiring (hardware/perfboard/R7). Pin roles are unchanged from R7.1.
#include <Arduino.h>

namespace cfg {

constexpr char kFirmwareId[] = "SALINITY_APP_R8_0";

// Electrode drive and sensors (unchanged from SalinityMeterCalibrated R7.1).
constexpr uint8_t kPinDriveA = D0;    // GPIO1 -> R1 -> E1
constexpr uint8_t kPinDriveB = D1;    // GPIO2 -> R2 -> E2
constexpr uint8_t kPinTempDq = D3;    // GPIO4 DS18B20 DATA
constexpr uint8_t kPinSda = D4;       // GPIO5 shared I2C: ADS1115 / SSD1306 / VL53L5CX
constexpr uint8_t kPinScl = D5;       // GPIO6

// Buttons: external 10k pull-up (R9..R11) + 1k series (R12..R14) -> switch -> GND. Active LOW.
constexpr uint8_t kPinKeyMeasure = D6;  // GPIO43 KEY1 (also U0TXD during ROM boot)
constexpr uint8_t kPinKeyMode = D7;     // GPIO44 KEY2
constexpr uint8_t kPinKeySave = D8;     // GPIO7  KEY3

// ONE005 active buzzer, HIGH = sound (R15 1k series, R16 10k pull-down).
constexpr uint8_t kPinBuzzer = D9;      // GPIO8

// I2C addresses on the shared bus.
constexpr uint8_t kAdsAddress = 0x48;
constexpr uint8_t kOledAddress = 0x3C;
constexpr uint8_t kTofAddress = 0x29;

// The salinity calibration was recorded with the bus at 100 kHz. The response is
// time-dependent, so acquisition always runs at exactly that clock and timeout.
constexpr uint32_t kI2cMeasureHz = 100000;
constexpr uint16_t kI2cMeasureTimeoutMs = 5;
// Display / ToF firmware upload use a faster clock outside the acquisition window.
constexpr uint32_t kI2cFastHz = 400000;
constexpr uint16_t kI2cFastTimeoutMs = 50;

// OLED: SSD1306 0.91" 128x32.
constexpr uint8_t kOledWidth = 128;
constexpr uint8_t kOledHeight = 32;
constexpr uint32_t kOledSleepMs = 120000;  // blank after 2 min idle; any key wakes it

// Buttons.
constexpr uint16_t kDebounceMs = 25;
constexpr uint16_t kLongPressMs = 1000;

// Target salinity (percent) limits for the guidance screen.
constexpr float kTargetMin = 0.3f;
constexpr float kTargetMax = 3.0f;
constexpr float kTargetStep = 0.1f;
constexpr float kTargetDefault = 0.8f;
// Patent S700: target reached when |current-target| <= 0.05 %p.
constexpr float kTargetTolerance = 0.05f;
// Patent S700: after this many add/re-measure rounds, recommend manual adjustment
// or sensor calibration.
constexpr uint8_t kMaxAdjustRounds = 3;

// Patent eq.1: Wsalt[g] = (Starget - Scurrent)[%p] * Vbroth[L] * K, K = 10 g/(%p*L).
constexpr float kSaltKDefault = 10.0f;

// Temperature compensation S_ref = S_T / (1 + beta*(T - Tref)).
// The R7.1 table was recorded at 19.25..21.56 C without compensation, so the
// reference is the calibration temperature, not 25 C, and beta defaults to 0 (off)
// until it is measured for this probe.
constexpr float kTempRefC = 20.0f;
constexpr float kTempBetaDefault = 0.0f;
// One-point cell correction against a reference solution is bounded to this range.
constexpr float kCellGainMin = 0.7f;
constexpr float kCellGainMax = 1.3f;
// Provisional drift flag: spread (max-min) of the three trial indices. The
// calibration trials spread 0.06..0.39 index units. Not a validated limit.
constexpr float kTrialSpreadWarn = 0.8f;

// Default bowl profile (truncated cone): the 90 mm measuring cup used in tests.
// Inner dimensions were not measured; the user should set the real bowl.
constexpr float kBowlTopDefaultMm = 86.0f;
constexpr float kBowlBottomDefaultMm = 66.0f;
constexpr float kBowlDepthDefaultMm = 88.0f;

// A scan result is attached to a salinity record when it is this recent.
constexpr uint32_t kScanFreshMs = 5UL * 60UL * 1000UL;
// Broth volume pushed by the phone app (`broth` command) stays valid this long.
constexpr uint32_t kBrothOverrideMs = 30UL * 60UL * 1000UL;

// BLE: Nordic UART Service layout for newline-delimited JSON / text commands,
// plus a separate binary service for image chunks.
constexpr char kBleNamePrefix[] = "SaltMeter-";
constexpr char kNusService[] = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E";
constexpr char kNusRx[] = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E";  // phone -> device (write)
constexpr char kNusTx[] = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E";  // device -> phone (notify)
constexpr char kImgService[] = "5A17A000-6D2B-4E8C-9C3B-7E3F0A1C0001";
constexpr char kImgData[] = "5A17A001-6D2B-4E8C-9C3B-7E3F0A1C0001";  // notify, binary chunks
constexpr uint16_t kBleMtu = 517;

// Device history kept in NVS.
constexpr uint8_t kHistoryCapacity = 30;

}  // namespace cfg
