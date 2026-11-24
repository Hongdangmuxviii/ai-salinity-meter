#include "CameraCapture.h"

#include "esp_camera.h"

namespace cam {
namespace {

bool ok = false;
uint8_t *buffer = nullptr;
size_t length = 0;
uint16_t imageId = 0;
uint32_t checksum = 0;
uint16_t w = 0, h = 0;
const char *error = "not captured";

// Seeed XIAO ESP32-S3 Sense camera connector. None of these pins are used by R7.
camera_config_t makeConfig(framesize_t frameSize) {
  camera_config_t c = {};
  c.pin_pwdn = -1;
  c.pin_reset = -1;
  c.pin_xclk = 10;
  c.pin_sccb_sda = 40;
  c.pin_sccb_scl = 39;
  c.pin_d7 = 48;
  c.pin_d6 = 11;
  c.pin_d5 = 12;
  c.pin_d4 = 14;
  c.pin_d3 = 16;
  c.pin_d2 = 18;
  c.pin_d1 = 17;
  c.pin_d0 = 15;
  c.pin_vsync = 38;
  c.pin_href = 47;
  c.pin_pclk = 13;
  c.xclk_freq_hz = 20000000;
  c.ledc_timer = LEDC_TIMER_0;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = frameSize;
  c.jpeg_quality = 12;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  c.sccb_i2c_port = 1;  // Wire (R7 sensors) uses port 0
  return c;
}

framesize_t parseSize(const char *name) {
  if (!name || !*name) return FRAMESIZE_VGA;
  if (!strcasecmp(name, "qvga")) return FRAMESIZE_QVGA;
  if (!strcasecmp(name, "svga")) return FRAMESIZE_SVGA;
  if (!strcasecmp(name, "xga")) return FRAMESIZE_XGA;
  if (!strcasecmp(name, "uxga")) return FRAMESIZE_UXGA;
  return FRAMESIZE_VGA;
}

}  // namespace

uint32_t crc32Of(const uint8_t *data, size_t len) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (uint8_t b = 0; b < 8; ++b) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
  }
  return ~crc;
}

bool detect() {
  if (!psramFound()) {
    error = "no PSRAM (build with PSRAM=opi)";
    ok = false;
    return false;
  }
  camera_config_t c = makeConfig(FRAMESIZE_QVGA);
  ok = esp_camera_init(&c) == ESP_OK;
  if (ok) esp_camera_deinit();
  else error = "camera init failed";
  return ok;
}

bool present() { return ok; }

bool capture(const char *sizeName) {
  if (!ok) return false;
  camera_config_t c = makeConfig(parseSize(sizeName));
  if (esp_camera_init(&c) != ESP_OK) {
    error = "camera init failed";
    return false;
  }
  // Let auto exposure / white balance settle.
  for (uint8_t i = 0; i < 5; ++i) {
    camera_fb_t *warm = esp_camera_fb_get();
    if (warm) esp_camera_fb_return(warm);
  }
  camera_fb_t *fb = esp_camera_fb_get();
  bool captured = false;
  if (!fb) {
    error = "no frame";
  } else if (fb->format != PIXFORMAT_JPEG || fb->len == 0) {
    error = "frame is not JPEG";
  } else {
    if (buffer) free(buffer);
    buffer = static_cast<uint8_t *>(ps_malloc(fb->len));
    if (!buffer) {
      length = 0;
      error = "PSRAM allocation failed";
    } else {
      memcpy(buffer, fb->buf, fb->len);
      length = fb->len;
      w = fb->width;
      h = fb->height;
      checksum = crc32Of(buffer, length);
      ++imageId;
      if (imageId == 0) imageId = 1;
      captured = true;
      error = "";
    }
  }
  if (fb) esp_camera_fb_return(fb);
  esp_camera_deinit();  // stop XCLK / DMA between captures (power, ADC quiet)
  return captured;
}

const uint8_t *data() { return buffer; }
size_t size() { return length; }
uint16_t id() { return imageId; }
uint32_t crc32() { return checksum; }
uint16_t width() { return w; }
uint16_t height() { return h; }
const char *lastError() { return error; }

}  // namespace cam
