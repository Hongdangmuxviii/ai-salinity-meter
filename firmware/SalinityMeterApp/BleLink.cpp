#include "BleLink.h"

#include <NimBLEDevice.h>

#include "Config.h"

namespace blelink {
namespace {

constexpr size_t kLineMax = 160;
constexpr uint8_t kQueueDepth = 8;

struct Line {
  char text[kLineMax];
};

NimBLEServer *server = nullptr;
NimBLECharacteristic *rxChr = nullptr;
NimBLECharacteristic *txChr = nullptr;
NimBLECharacteristic *imgChr = nullptr;
QueueHandle_t queue = nullptr;
char name[24] = "";
volatile bool isConnected = false;
volatile bool txOn = false;
volatile bool imgOn = false;
volatile uint16_t currentMtu = 23;

void enqueue(const char *start, size_t len) {
  while (len > 0 && (start[len - 1] == '\r' || start[len - 1] == ' ')) --len;
  while (len > 0 && (*start == ' ' || *start == '\r')) { ++start; --len; }
  if (len == 0) return;
  Line line;
  len = min(len, kLineMax - 1);
  memcpy(line.text, start, len);
  line.text[len] = '\0';
  xQueueSend(queue, &line, 0);  // drop when full rather than block the BLE host
}

class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer *s, NimBLEConnInfo &info) override {
    isConnected = true;
    currentMtu = info.getMTU();
    // 7.5..30 ms interval for faster image transfer; the phone may refuse.
    s->updateConnParams(info.getConnHandle(), 6, 24, 0, 400);
  }
  void onDisconnect(NimBLEServer *, NimBLEConnInfo &, int) override {
    isConnected = false;
    txOn = false;
    imgOn = false;
    currentMtu = 23;
  }
  void onMTUChange(uint16_t value, NimBLEConnInfo &) override { currentMtu = value; }
};

class CharCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *c, NimBLEConnInfo &) override {
    NimBLEAttValue value = c->getValue();
    const char *data = reinterpret_cast<const char *>(value.data());
    const size_t length = value.length();
    size_t start = 0;
    for (size_t i = 0; i < length; ++i) {
      if (data[i] == '\n') {
        enqueue(data + start, i - start);
        start = i + 1;
      }
    }
    if (start < length) enqueue(data + start, length - start);
  }
  void onSubscribe(NimBLECharacteristic *c, NimBLEConnInfo &, uint16_t subValue) override {
    const bool on = (subValue & 0x0001) != 0;
    if (c == txChr) txOn = on;
    else if (c == imgChr) imgOn = on;
  }
};

ServerCallbacks serverCallbacks;
CharCallbacks charCallbacks;

bool notifyWithRetry(NimBLECharacteristic *c, const uint8_t *data, size_t len) {
  // notify() fails when the host has no free buffers; wait and retry (flow control).
  for (uint8_t attempt = 0; attempt < 100; ++attempt) {
    if (!isConnected) return false;
    if (c->notify(data, len)) return true;
    delay(3);
  }
  return false;
}

void startAdvertising() {
  NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
  NimBLEAdvertisementData advData;
  advData.setFlags(BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP);
  advData.addServiceUUID(NimBLEUUID(cfg::kNusService));
  NimBLEAdvertisementData scanData;
  scanData.setName(name);
  adv->setAdvertisementData(advData);
  adv->setScanResponseData(scanData);
  adv->start();
}

}  // namespace

void begin() {
  queue = xQueueCreate(kQueueDepth, sizeof(Line));
  const uint64_t mac = ESP.getEfuseMac();
  snprintf(name, sizeof(name), "%s%02X%02X", cfg::kBleNamePrefix,
           unsigned((mac >> 32) & 0xFF), unsigned((mac >> 40) & 0xFF));

  NimBLEDevice::init(name);
  NimBLEDevice::setMTU(cfg::kBleMtu);
  server = NimBLEDevice::createServer();
  server->setCallbacks(&serverCallbacks);

  NimBLEService *nus = server->createService(cfg::kNusService);
  rxChr = nus->createCharacteristic(cfg::kNusRx, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  txChr = nus->createCharacteristic(cfg::kNusTx, NIMBLE_PROPERTY::NOTIFY);
  rxChr->setCallbacks(&charCallbacks);
  txChr->setCallbacks(&charCallbacks);

  NimBLEService *img = server->createService(cfg::kImgService);
  imgChr = img->createCharacteristic(cfg::kImgData, NIMBLE_PROPERTY::NOTIFY);
  imgChr->setCallbacks(&charCallbacks);

  startAdvertising();
}

void loop() {
  if (!isConnected && !NimBLEDevice::getAdvertising()->isAdvertising()) startAdvertising();
}

const char *deviceName() { return name; }
bool connected() { return isConnected; }
bool textSubscribed() { return isConnected && txOn; }
bool imageSubscribed() { return isConnected && imgOn; }
uint16_t mtu() { return currentMtu; }

bool popCommand(char *out, size_t length) {
  Line line;
  if (!queue || xQueueReceive(queue, &line, 0) != pdTRUE) return false;
  strlcpy(out, line.text, length);
  return true;
}

bool sendLine(const char *line) {
  if (!textSubscribed()) return false;
  const size_t chunk = max<int>(20, int(currentMtu) - 3);
  const size_t len = strlen(line);
  size_t offset = 0;
  while (offset < len) {
    const size_t n = min(chunk, len - offset);
    if (!notifyWithRetry(txChr, reinterpret_cast<const uint8_t *>(line) + offset, n)) return false;
    offset += n;
  }
  const uint8_t newline = '\n';
  return notifyWithRetry(txChr, &newline, 1);
}

size_t imagePayloadBytes() { return max<int>(16, int(currentMtu) - 3 - 4); }

bool sendImageChunk(uint16_t imageId, uint16_t index, const uint8_t *data, size_t length) {
  if (!imageSubscribed()) return false;
  uint8_t packet[cfg::kBleMtu];
  length = min(length, imagePayloadBytes());
  packet[0] = imageId & 0xFF;
  packet[1] = imageId >> 8;
  packet[2] = index & 0xFF;
  packet[3] = index >> 8;
  memcpy(packet + 4, data, length);
  return notifyWithRetry(imgChr, packet, length + 4);
}

}  // namespace blelink
