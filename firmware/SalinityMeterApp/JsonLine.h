#pragma once
// Minimal JSON line builder (fixed buffer, no heap). NaN/inf become null.
#include <Arduino.h>
#include <stdarg.h>

class JsonLine {
 public:
  explicit JsonLine(const char *type) {
    add("{\"type\":\"");
    add(type);
    add("\"");
  }
  JsonLine &s(const char *k, const char *v) {
    key(k);
    add("\"");
    for (; v && *v; ++v) {
      if (*v == '"' || *v == '\\') { const char e[3] = {'\\', *v, 0}; add(e); }
      else if (uint8_t(*v) >= 0x20) { const char c[2] = {*v, 0}; add(c); }
    }
    add("\"");
    return *this;
  }
  JsonLine &f(const char *k, double v, uint8_t digits) {
    key(k);
    if (!isfinite(v)) add("null");
    else addf("%.*f", int(digits), v);
    return *this;
  }
  JsonLine &f(const char *k, double v) { return f(k, v, 2); }
  JsonLine &i(const char *k, long v) { key(k); addf("%ld", v); return *this; }
  JsonLine &u(const char *k, unsigned long v) { key(k); addf("%lu", v); return *this; }
  JsonLine &b(const char *k, bool v) { key(k); add(v ? "true" : "false"); return *this; }
  JsonLine &raw(const char *k, const char *v) { key(k); add(v); return *this; }
  const char *finish() {
    if (!done) { add("}"); done = true; }
    return buf;
  }

 private:
  char buf[1100] = "";
  size_t n = 0;
  bool done = false;
  void key(const char *k) { add(",\""); add(k); add("\":"); }
  void add(const char *t) {
    while (*t && n < sizeof(buf) - 2) buf[n++] = *t++;
    buf[n] = '\0';
  }
  void addf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    const int w = vsnprintf(buf + n, sizeof(buf) - n - 1, fmt, ap);
    va_end(ap);
    if (w > 0) n = min(n + size_t(w), sizeof(buf) - 2);
  }
};
