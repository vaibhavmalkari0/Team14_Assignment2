// doorbell_board_starter.ino -- Module 2 "The Doorbell's Ears"   (AI255TBD Edge AI)
// Board: ESP32-S3-DevKitC-1 N16R8
//
// Tools menu, to start with:  Board = ESP32S3 Dev Module,  USB CDC On Boot = Enabled.
// Leave everything else alone for now. Some of it will matter later; finding out which is your job.
// The board listens on BOTH USB-C ports (USB = native, COM = USB-UART bridge) at once.
//
// TEXT COMMANDS (one line each, one line back)
//   PING  INFO  BAUD <rate>  FREE
//   STREAM fs=16000 fmt=i16 scale=1.0 win=480 hop=320 nfft=512 mels=40 mfcc=0 feat=1 store=psram max=8000000
//        -> READY ...  then the port switches to BINARY mode until an END frame or 3 s of silence
//        (feat=0 skips the features: the board only receives and stores)
//   SAVE                     -> TODO (Mission 2): copy the stored stream to flash so it survives a power cut
//   DUMP <sram|psram|flash>  -> DATA <n>, then n raw bytes
//   CRC  <sram|psram|flash>  -> CRC where= n= crc=
//
// BINARY FRAMES (little-endian)
//   laptop -> board : A5 5A | type u8 | seq u32 | len u16 | payload[len] | crc32 u32
//                     type 'D' = samples (in the fmt given to STREAM), 'E' = end of stream
//   board -> laptop : B5 5B | type u8 | seq u32 | len u16 | payload[len] | crc32 u32
//                     'F' = one feature frame: first_sample u32, compute_us u32, float32[mels or mfcc]
//                     'S' = stream summary as text "key=value ..."; the port is back in TEXT mode after it
//   crc32 (same as Python's zlib.crc32) covers type, seq, len and payload.
//
// The feature maths lives in features.h. It is correct, and slow. See Mission 3.

#include <Arduino.h>
#include <LittleFS.h>
#include "esp_heap_caps.h"
#include "features.h"

static const uint32_t UART_BAUD_DEFAULT = 921600;
static const char *REC_PATH = "/rec.bin";
static const size_t MAX_PAYLOAD = 4096;

// ---------------------------------------------------------------- CRC-32
static uint32_t crcTable[256];
static void crcInit() {
  for (uint32_t i = 0; i < 256; i++) {
    uint32_t c = i;
    for (int k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
    crcTable[i] = c;
  }
}
static inline uint32_t crcRaw(uint32_t c, const uint8_t *p, size_t n) {   // c is the inverted running value
  while (n--) c = crcTable[(c ^ *p++) & 0xFF] ^ (c >> 8);
  return c;
}
static uint32_t crc32(const uint8_t *p, size_t n) { return ~crcRaw(0xFFFFFFFFu, p, n); }

// ---------------------------------------------------------------- storage
static uint8_t *storeBuf = nullptr; static size_t storeCap = 0, storeLen = 0;
static char storeWhere[8] = "none";
static bool fsOk = false;
static void freeStore() { free(storeBuf); storeBuf = nullptr; storeCap = storeLen = 0; strcpy(storeWhere, "none"); }

// ---------------------------------------------------------------- stream state
static FeaturePipeline feat;
static float *fbuf = nullptr; static int fcount = 0;   // window being filled
static float *fout = nullptr;
struct Stats {
  uint32_t framesOk, badCrc, badLen, seqGaps, dup, samples, storeFull, featSent;
  uint32_t maxUs, uartOverflow; uint64_t sumUs; uint32_t t0, tLast; int32_t lastSeq;
} st;
static int fmtBytes = 2; static float qmaxInv = 1.0f / 32767.0f, scale = 1.0f;
static char fmtName[4] = "i16";
static bool featOn = true;
static volatile uint32_t uartErrors = 0;

static void sendFrame(Stream &s, char type, uint32_t seq, const uint8_t *payload, uint16_t len) {
  uint8_t hdr[9] = {0xB5, 0x5B, (uint8_t)type};
  memcpy(hdr + 3, &seq, 4); memcpy(hdr + 7, &len, 2);
  uint32_t c = crcRaw(0xFFFFFFFFu, hdr + 2, 7); c = ~crcRaw(c, payload, len);
  s.write(hdr, 9); if (len) s.write(payload, len); s.write((uint8_t *)&c, 4);
}

static void pushSamples(Stream &s, const uint8_t *p, size_t nbytes) {
  size_t n = nbytes / fmtBytes;
  for (size_t i = 0; i < n; i++) {
    float x;
    if (fmtBytes == 4) memcpy(&x, p + 4 * i, 4);
    else if (fmtBytes == 2) { int16_t q; memcpy(&q, p + 2 * i, 2); x = q * qmaxInv * scale; }
    else x = (int8_t)p[i] * qmaxInv * scale;
    if (!featOn) continue;
    fbuf[fcount++] = x;
    if (fcount == feat.c.win) {
      uint32_t t = micros();
      feat.compute(fbuf, fout);
      uint32_t us = micros() - t;
      st.maxUs = max(st.maxUs, us); st.sumUs += us;
      uint32_t first = st.samples + i + 1 - feat.c.win;   // index of the frame's first sample
      uint32_t frameNo = st.featSent++;
      static uint8_t pay[8 + 4 * 128];                     // first_sample, compute_us, features
      memcpy(pay, &first, 4); memcpy(pay + 4, &us, 4); memcpy(pay + 8, fout, 4 * feat.outSize());
      sendFrame(s, 'F', frameNo, pay, 8 + 4 * feat.outSize());
      memmove(fbuf, fbuf + feat.c.hop, sizeof(float) * (feat.c.win - feat.c.hop));
      fcount -= feat.c.hop;
    }
  }
  st.samples += n;
}

static void finishStream(Stream &s, const char *why) {
  char txt[400];
  uint32_t secs_ms = st.tLast - st.t0;
  int n = snprintf(txt, sizeof(txt),
    "why=%s frames_ok=%u bad_crc=%u bad_len=%u seq_gaps=%u dup=%u samples=%u stored=%u where=%s store_full=%u "
    "features=%u max_us=%u avg_us=%u uart_errors=%u ms=%u",
    why, st.framesOk, st.badCrc, st.badLen, st.seqGaps, st.dup, st.samples, (unsigned)storeLen, storeWhere,
    st.storeFull, st.featSent, st.maxUs, st.featSent ? (unsigned)(st.sumUs / st.featSent) : 0,
    (unsigned)uartErrors, secs_ms);
  sendFrame(s, 'S', 0, (const uint8_t *)txt, n);
  feat.end(); free(fbuf); fbuf = nullptr; free(fout); fout = nullptr;
}

static bool kv(const char *line, const char *key, char *out, size_t cap) {
  char pat[16]; snprintf(pat, sizeof(pat), " %s=", key);
  const char *p = strstr(line, pat); if (!p) return false;
  p += strlen(pat); size_t i = 0;
  while (*p && *p != ' ' && i < cap - 1) out[i++] = *p++;
  out[i] = 0; return true;
}

// Runs the whole binary session on one port. Returns when the stream ends.
static void runStream(Stream &s, const char *line) {
  char v[24]; FeatCfg c;
  if (kv(line, "fs", v, sizeof v)) c.fs = atoi(v);
  if (kv(line, "win", v, sizeof v)) c.win = atoi(v);
  if (kv(line, "hop", v, sizeof v)) c.hop = atoi(v);
  if (kv(line, "nfft", v, sizeof v)) c.nfft = atoi(v);
  if (kv(line, "mels", v, sizeof v)) c.mels = atoi(v);
  if (kv(line, "mfcc", v, sizeof v)) c.mfcc = atoi(v);
  strcpy(fmtName, "i16"); if (kv(line, "fmt", v, sizeof v)) { strncpy(fmtName, v, 3); fmtName[3] = 0; }
  scale = 1.0f; if (kv(line, "scale", v, sizeof v)) scale = atof(v);
  featOn = true; if (kv(line, "feat", v, sizeof v)) featOn = atoi(v) != 0;
  if (!strcmp(fmtName, "f32")) { fmtBytes = 4; qmaxInv = 1; }
  else if (!strcmp(fmtName, "i16")) { fmtBytes = 2; qmaxInv = 1.0f / 32767.0f; }
  else if (!strcmp(fmtName, "i8")) { fmtBytes = 1; qmaxInv = 1.0f / 127.0f; }
  else { s.printf("ERR fmt must be f32, i16 or i8\n"); return; }
  if (!feat.begin(c)) { s.printf("ERR feature settings (nfft power of 2, win<=nfft, mels<=128, mfcc<=mels)\n"); return; }
  fbuf = (float *)malloc(sizeof(float) * c.win); fout = (float *)malloc(sizeof(float) * feat.outSize());
  fcount = 0;

  char where[8] = "none"; size_t want = 0;
  kv(line, "store", where, sizeof where);
  if (kv(line, "max", v, sizeof v)) want = strtoul(v, nullptr, 10);
  freeStore();
  if (strcmp(where, "none")) {
    if (!want) { s.printf("ERR store needs max=<bytes>\n"); feat.end(); return; }
    uint32_t caps = !strcmp(where, "psram") ? (MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)
                  : !strcmp(where, "sram") ? (MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT) : 0;
    if (!caps) { s.printf("ERR store must be none, sram or psram\n"); feat.end(); return; }
    if (caps & MALLOC_CAP_SPIRAM && !psramFound()) { s.printf("ERR no psram (Tools > PSRAM)\n"); feat.end(); return; }
    storeBuf = (uint8_t *)heap_caps_malloc(want, caps);
    if (!storeBuf) {
      s.printf("ERR alloc %s want=%u largest=%u\n", where, (unsigned)want,
               (unsigned)heap_caps_get_largest_free_block(caps));
      feat.end(); return;
    }
    storeCap = want; strcpy(storeWhere, where);
  }
  memset(&st, 0, sizeof st); st.lastSeq = -1; uartErrors = 0;
  s.printf("READY fs=%d fmt=%s win=%d hop=%d nfft=%d out=%d feat=%d store=%s cap=%u\n",
           c.fs, fmtName, c.win, c.hop, c.nfft, feat.outSize(), (int)featOn, storeWhere, (unsigned)storeCap);

  static uint8_t buf[9 + MAX_PAYLOAD + 4];
  size_t have = 0; uint32_t lastByte = millis(); bool started = false;
  while (true) {
    int av = s.available();
    if (av <= 0) {
      if (millis() - lastByte > 3000) { finishStream(s, "timeout"); return; }
      delay(0); continue;
    }
    lastByte = millis();
    if (!started) { st.t0 = millis(); started = true; }
    // fill the frame buffer as far as needed
    if (have < 2) {                                   // hunt for magic A5 5A
      int b = s.read(); if (b < 0) continue;
      if (have == 0 && b == 0xA5) buf[have++] = b;
      else if (have == 1 && b == 0x5A) buf[have++] = b;
      else have = (b == 0xA5) ? 1 : 0;
      continue;
    }
    size_t need = 9;
    if (have >= 9) { uint16_t len; memcpy(&len, buf + 7, 2); if (len > MAX_PAYLOAD) { st.badLen++; have = 0; continue; } need = 9 + len + 4; }
    size_t r = s.readBytes(buf + have, min((size_t)av, need - have));
    have += r;
    if (have < 9 || have < need || need == 9) continue;
    // a whole frame
    uint16_t len; uint32_t seq, crc; memcpy(&len, buf + 7, 2); memcpy(&seq, buf + 3, 4); memcpy(&crc, buf + 9 + len, 4);
    char type = buf[2]; have = 0;
    if (crc32(buf + 2, 7 + len) != crc) { st.badCrc++; continue; }
    if ((int32_t)seq <= st.lastSeq) { st.dup++; continue; }
    if (st.lastSeq >= 0 && (int32_t)seq != st.lastSeq + 1) st.seqGaps += seq - st.lastSeq - 1;
    st.lastSeq = seq; st.framesOk++; st.tLast = millis();
    if (type == 'E') { finishStream(s, "end"); return; }
    if (type != 'D') continue;
    if (storeBuf) {
      size_t room = storeCap - storeLen, k = len < room ? len : room;
      memcpy(storeBuf + storeLen, buf + 9, k); storeLen += k;
      if (k < len) st.storeFull++;
    }
    pushSamples(s, buf + 9, len);
  }
}

// ---------------------------------------------------------------- other commands
static void writeAll(Stream &s, const uint8_t *p, size_t n) {
  while (n) { size_t w = s.write(p, n > 1024 ? 1024 : n); if (!w) { delay(1); continue; } p += w; n -= w; }
}

static void cmdInfo(Stream &s) {
  s.printf("INFO cpu_mhz=%u heap_free=%u heap_largest=%u psram_size=%u psram_free=%u psram_largest=%u "
           "flash_chip=%u fs_total=%u fs_used=%u stored=%u where=%s\n",
           (unsigned)getCpuFrequencyMhz(),
           (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT),
           (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT),
           (unsigned)ESP.getPsramSize(), (unsigned)ESP.getFreePsram(),
           (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM), (unsigned)ESP.getFlashChipSize(),
           (unsigned)(fsOk ? LittleFS.totalBytes() : 0), (unsigned)(fsOk ? LittleFS.usedBytes() : 0),
           (unsigned)storeLen, storeWhere);
}

static void cmdSave(Stream &s) {
  // TODO Mission 2: write storeBuf (storeLen bytes) to the file REC_PATH with LittleFS,
  // so the recording survives a power cut. Reply  OK SAVE n=<bytes> us=<time taken> crc=<crc32 hex>
  // Clues: LittleFS.open(REC_PATH, "w"), f.write(ptr, len) in chunks, f.close(), crc32(storeBuf, storeLen).
  // Before you write: does INFO's fs_total leave room? If not, which Tools settings decide it?
  s.printf("ERR SAVE not written yet\n");
}

static void cmdDump(Stream &s, const char *where, bool crcOnly) {
  if (!strcmp(where, "sram") || !strcmp(where, "psram")) {
    size_t n = strcmp(where, storeWhere) ? 0 : storeLen;
    if (crcOnly) s.printf("CRC where=%s n=%u crc=%08x\n", where, (unsigned)n, (unsigned)(n ? crc32(storeBuf, n) : 0));
    else { s.printf("DATA %u\n", (unsigned)n); writeAll(s, storeBuf, n); }
    return;
  }
  if (!strcmp(where, "flash")) {
    if (!fsOk || !LittleFS.exists(REC_PATH)) { s.printf(crcOnly ? "CRC where=flash n=0 crc=00000000\n" : "DATA 0\n"); return; }
    File f = LittleFS.open(REC_PATH, "r"); size_t len = f.size(); uint32_t c = 0xFFFFFFFFu; static uint8_t ch[4096];
    if (!crcOnly) s.printf("DATA %u\n", (unsigned)len);
    while (f.available()) { size_t r = f.read(ch, sizeof ch); if (crcOnly) c = crcRaw(c, ch, r); else writeAll(s, ch, r); }
    f.close();
    if (crcOnly) s.printf("CRC where=flash n=%u crc=%08x\n", (unsigned)len, (unsigned)~c);
    return;
  }
  s.printf("ERR where must be sram, psram or flash\n");
}

static void handle(Stream &s, char *line) {
  char cmd[12] = {0}, a[16] = {0};
  if (sscanf(line, "%11s %15s", cmd, a) <= 0) return;
  if (!strcmp(cmd, "PING")) s.printf("PONG\n");
  else if (!strcmp(cmd, "INFO")) cmdInfo(s);
  else if (!strcmp(cmd, "BAUD")) {
    uint32_t r = strtoul(a, nullptr, 10); s.printf("OK BAUD %u\n", (unsigned)r); s.flush(); delay(20);
#if ARDUINO_USB_CDC_ON_BOOT
    if (&s == (Stream *)&Serial0) Serial0.updateBaudRate(r);
#else
    Serial.updateBaudRate(r);
#endif
  }
  else if (!strcmp(cmd, "STREAM")) runStream(s, line);
  else if (!strcmp(cmd, "SAVE")) cmdSave(s);
  else if (!strcmp(cmd, "DUMP")) cmdDump(s, a, false);
  else if (!strcmp(cmd, "CRC")) cmdDump(s, a, true);
  else if (!strcmp(cmd, "FREE")) { freeStore(); s.printf("OK FREE\n"); }
  else s.printf("ERR unknown command: %s\n", line);
}

static bool readLine(Stream &s, char *acc, size_t &n, char *out, size_t cap) {
  while (s.available()) {
    char c = (char)s.read();
    if (c == '\r') continue;
    if (c == '\n') { acc[n] = 0; strncpy(out, acc, cap); out[cap - 1] = 0; n = 0; return true; }
    if (n < 159) acc[n++] = c;
  }
  return false;
}

void setup() {
  crcInit();
  Serial.setRxBufferSize(32768);
  Serial.begin(UART_BAUD_DEFAULT);
#if ARDUINO_USB_CDC_ON_BOOT
  Serial0.setRxBufferSize(32768);
  Serial0.begin(UART_BAUD_DEFAULT);
  Serial0.onReceiveError([](hardwareSerial_error_t) { uartErrors++; });
#endif
  fsOk = LittleFS.begin(true);
}

void loop() {
  static char acc0[160], acc1[160], line[160]; static size_t n0 = 0, n1 = 0;
  if (readLine(Serial, acc0, n0, line, sizeof line)) handle(Serial, line);
#if ARDUINO_USB_CDC_ON_BOOT
  if (readLine(Serial0, acc1, n1, line, sizeof line)) handle(Serial0, line);
#endif
  delay(0);
}
