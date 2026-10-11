// BrainTech-16 firmware (ESP32-S3, Arduino core 3.x).
// Two ADS1299s (16 channels) streamed as an OpenBCI Cyton+Daisy behind an OpenBCI Wi-Fi Shield,
// so BrainFlow board CYTON_DAISY_WIFI and the OpenBCI GUI connect without changes.
//
// Wi-Fi protocol (from BrainFlow openbci_wifi_shield_board.cpp):
//   GET  /board                     -> board info (HTTP 200)
//   POST /tcp {"ip","port",...}      -> we connect as a TCP *client* to the laptop and send raw packets
//   POST /command {"command":"..."}  -> Cyton single-character commands
//   GET  /stream/start, /stream/stop
// Packet: 0xA0, sample#, 24 bytes (8 x 24-bit), 6 aux bytes, 0xC0  (33 bytes).
// Daisy convention (BrainFlow cyton_daisy_wifi.cpp): channels 1-8 then 9-16 in two packets with the SAME sample#.
//
// Electrode wiring is a referential montage: electrodes on INxP, reference on SRB1 + all INxN
// -> CHnSET = 0x60 (gain 24, normal input, SRB2 open), MISC1 = 0x20 (SRB1 closed).

#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <WebServer.h>
#include "secrets.h"   // #define WIFI_SSID "...", WIFI_PASS "..."  (not committed)

// ---------- pins (match hardware/kicad/circuit.py) ----------
constexpr int PIN_SCLK = 12, PIN_MOSI = 11, PIN_MISO = 13;
constexpr int PIN_CS1 = 10, PIN_CS2 = 9;
constexpr int PIN_DRDY1 = 14, PIN_DRDY2 = 8;
constexpr int PIN_START = 15, PIN_RESET = 16, PIN_PWDN = 17;
constexpr int PIN_LED_G = 4, PIN_LED_B = 5, PIN_VBAT = 1;   // VBAT_SENSE = VSYS / 2

// ---------- ADS1299 ----------
enum : uint8_t { RESET_CMD = 0x06, START_CMD = 0x08, STOP_CMD = 0x0A, RDATAC = 0x10, SDATAC = 0x11,
                 RREG = 0x20, WREG = 0x40 };
enum : uint8_t { ID_REG = 0x00, CONFIG1 = 0x01, CONFIG2 = 0x02, CONFIG3 = 0x03, CH1SET = 0x05,
                 BIAS_SENSP = 0x0D, BIAS_SENSN = 0x0E, MISC1 = 0x15 };
SPISettings ads(4000000, MSBFIRST, SPI_MODE1);

uint8_t rateBits = 0x06;           // DR[2:0]: 6 = 250 SPS, 5 = 500, 4 = 1000 (Cyton '~6','~5','~4')
uint8_t chSet[16];                 // current CHnSET per channel
bool streaming = false;
volatile bool dataReady = false;
uint8_t sampleNum = 0;

WebServer http(80);
WiFiClient tcp;
String tcpIp; uint16_t tcpPort = 0;

void IRAM_ATTR onDrdy() { dataReady = true; }

void csLow(int cs) { digitalWrite(cs, LOW); }
void csHigh(int cs) { digitalWrite(cs, HIGH); }

void cmd(int cs, uint8_t c) {
  SPI.beginTransaction(ads); csLow(cs); SPI.transfer(c); delayMicroseconds(3); csHigh(cs);
  SPI.endTransaction(); delayMicroseconds(5);
}

void wreg(int cs, uint8_t reg, uint8_t val) {
  SPI.beginTransaction(ads); csLow(cs);
  SPI.transfer(WREG | reg); SPI.transfer(0x00); SPI.transfer(val);
  delayMicroseconds(3); csHigh(cs); SPI.endTransaction(); delayMicroseconds(5);
}

uint8_t rreg(int cs, uint8_t reg) {
  SPI.beginTransaction(ads); csLow(cs);
  SPI.transfer(RREG | reg); SPI.transfer(0x00); uint8_t v = SPI.transfer(0x00);
  csHigh(cs); SPI.endTransaction(); return v;
}

void writeConfig1() {
  wreg(PIN_CS1, CONFIG1, 0xB0 | rateBits);   // CLK_EN = 1: chip 1 drives chip 2's clock
  wreg(PIN_CS2, CONFIG1, 0x90 | rateBits);
}

void applyChannel(int ch) {          // ch 0..15
  int cs = ch < 8 ? PIN_CS1 : PIN_CS2;
  wreg(cs, CH1SET + (ch % 8), chSet[ch]);
}

void defaults() {
  for (int cs : {PIN_CS1, PIN_CS2}) cmd(cs, SDATAC);
  writeConfig1();
  wreg(PIN_CS1, CONFIG2, 0xC0); wreg(PIN_CS2, CONFIG2, 0xC0);   // test signal off
  wreg(PIN_CS1, CONFIG3, 0xEC);                                // ref buffer on, bias amp on, BIASREF internal
  wreg(PIN_CS2, CONFIG3, 0xE0);                                // ref buffer on, bias amp off (unused)
  for (int ch = 0; ch < 16; ch++) { chSet[ch] = 0x60; applyChannel(ch); }
  wreg(PIN_CS1, BIAS_SENSP, 0xFF); wreg(PIN_CS1, BIAS_SENSN, 0xFF);
  wreg(PIN_CS2, BIAS_SENSP, 0x00); wreg(PIN_CS2, BIAS_SENSN, 0x00);
  wreg(PIN_CS1, MISC1, 0x20); wreg(PIN_CS2, MISC1, 0x20);     // SRB1 -> all negative inputs
}

void testSignal(uint8_t config2) {   // Cyton '-' '=' '[' ']'
  for (int cs : {PIN_CS1, PIN_CS2}) { cmd(cs, SDATAC); wreg(cs, CONFIG2, config2); }
  for (int ch = 0; ch < 16; ch++) { chSet[ch] = (chSet[ch] & 0xF8) | 0x05; applyChannel(ch); }
}

void startStream() {
  for (int cs : {PIN_CS1, PIN_CS2}) cmd(cs, RDATAC);
  digitalWrite(PIN_START, HIGH);
  streaming = true; sampleNum = 0;
  digitalWrite(PIN_LED_G, HIGH);
}

void stopStream() {
  digitalWrite(PIN_START, LOW);
  for (int cs : {PIN_CS1, PIN_CS2}) cmd(cs, SDATAC);
  streaming = false;
  digitalWrite(PIN_LED_G, LOW);
}

// Cyton channel letters: 1-8 then Q,W,E,R,T,Y,U,I for 9-16
int channelIndex(char c) {
  if (c >= '1' && c <= '8') return c - '1';
  const char *daisy = "QWERTYUI";
  for (int i = 0; i < 8; i++) if (c == daisy[i]) return 8 + i;
  return -1;
}

const char *OFF_KEYS = "12345678qwertyui", *ON_KEYS = "!@#$%^&*QWERTYUI";

// returns a short reply for /command
String handleCommand(const String &s) {
  bool wasStreaming = streaming;
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == 'b') startStream();
    else if (c == 's') stopStream();
    else if (c == 'd') { stopStream(); defaults(); }
    else if (c == 'v') { stopStream(); defaults(); return "OpenBCI V3 8-16 channel\nBrainTech-16 rev A$$$"; }
    else if (c == '-') testSignal(0xD0);   // 1x amplitude, slow
    else if (c == '=') testSignal(0xD1);   // 1x amplitude, fast
    else if (c == '[') testSignal(0xD4);   // 2x, slow
    else if (c == ']') testSignal(0xD5);   // 2x, fast
    else if (c == 'C' || c == 'c') { }     // 16-channel mode always on
    else if (c == '~' && i + 1 < s.length()) {
      char r = s[++i];
      if (r >= '4' && r <= '6') { if (streaming) stopStream(); rateBits = r - '0'; writeConfig1(); }
      // 250 SPS ('~6'), 500 ('~5') or 1000 ('~4'); faster rates are not supported over Wi-Fi here
    }
    else if (c == 'x' && i + 8 < s.length() && s[i + 8] == 'X') {
      // x (channel) (power down) (gain 0-6) (input 0-7) (bias) (srb2) (srb1) X
      int ch = channelIndex(s[i + 1]);
      if (ch >= 0) {
        uint8_t pd = s[i + 2] - '0', gain = s[i + 3] - '0', mux = s[i + 4] - '0', srb2 = s[i + 6] - '0';
        chSet[ch] = (pd << 7) | ((gain & 7) << 4) | (srb2 << 3) | (mux & 7);
        if (streaming) stopStream();
        applyChannel(ch);
      }
      i += 8;
    }
    else {
      const char *p = strchr(OFF_KEYS, c);
      const char *q = strchr(ON_KEYS, c);
      if (p) { int ch = p - OFF_KEYS; chSet[ch] |= 0x80; if (streaming) stopStream(); applyChannel(ch); }
      else if (q) { int ch = q - ON_KEYS; chSet[ch] &= 0x7F; if (streaming) stopStream(); applyChannel(ch); }
    }
  }
  if (wasStreaming && !streaming && s.indexOf('s') < 0) startStream();
  return "Success$$$";
}

// ---------- tiny JSON field readers (avoid a library dependency) ----------
String jsonString(const String &body, const char *key) {
  int k = body.indexOf(String("\"") + key + "\"");
  if (k < 0) return "";
  int a = body.indexOf('"', body.indexOf(':', k) + 1), b = body.indexOf('"', a + 1);
  return (a < 0 || b < 0) ? "" : body.substring(a + 1, b);
}
long jsonInt(const String &body, const char *key) {
  int k = body.indexOf(String("\"") + key + "\"");
  return k < 0 ? -1 : body.substring(body.indexOf(':', k) + 1).toInt();
}

void setupHttp() {
  http.on("/board", HTTP_GET, [] {
    http.send(200, "application/json",
              "{\"board_connected\":true,\"board_type\":\"daisy\",\"gains\":[24,24,24,24,24,24,24,24,24,24,24,24,24,24,24,24],"
              "\"num_channels\":16}");
  });
  http.on("/tcp", HTTP_POST, [] {
    String body = http.arg("plain");
    tcpIp = jsonString(body, "ip");
    tcpPort = (uint16_t)jsonInt(body, "port");
    tcp.stop();
    bool ok = tcp.connect(tcpIp.c_str(), tcpPort);
    tcp.setNoDelay(true);
    http.send(ok ? 200 : 500, "application/json",
              String("{\"connected\":") + (ok ? "true" : "false") + ",\"ip\":\"" + tcpIp + "\",\"port\":" + tcpPort + "}");
  });
  http.on("/command", HTTP_POST, [] {
    String c = jsonString(http.arg("plain"), "command");
    http.send(200, "text/plain", handleCommand(c));
  });
  http.on("/stream/start", HTTP_GET, [] { startStream(); http.send(200, "text/plain", "Stream started"); });
  http.on("/stream/stop", HTTP_GET, [] { stopStream(); http.send(200, "text/plain", "Stream stopped"); });
  http.on("/battery", HTTP_GET, [] {
    float v = analogReadMilliVolts(PIN_VBAT) * 2.0f / 1000.0f;
    http.send(200, "application/json", String("{\"vsys\":") + v + "}");
  });
  http.begin();
}

void readChip(int cs, uint8_t out[24]) {
  SPI.beginTransaction(ads); csLow(cs);
  for (int i = 0; i < 3; i++) SPI.transfer(0x00);         // status word
  for (int i = 0; i < 24; i++) out[i] = SPI.transfer(0x00);
  csHigh(cs); SPI.endTransaction();
}

void sendPacket(uint8_t sample, const uint8_t eeg[24]) {
  uint8_t pkt[33];
  pkt[0] = 0xA0; pkt[1] = sample;
  memcpy(pkt + 2, eeg, 24);
  memset(pkt + 26, 0, 6);                                   // TODO: LIS3DH accelerometer as Cyton does
  pkt[32] = 0xC0;
  if (tcp.connected()) tcp.write(pkt, 33);
  else Serial.write(pkt, 33);                               // USB fallback for bench testing
}

void setup() {
  Serial.begin(115200);
  for (int p : {PIN_CS1, PIN_CS2, PIN_START, PIN_RESET, PIN_PWDN, PIN_LED_G, PIN_LED_B}) pinMode(p, OUTPUT);
  csHigh(PIN_CS1); csHigh(PIN_CS2); digitalWrite(PIN_START, LOW);
  pinMode(PIN_DRDY1, INPUT); pinMode(PIN_DRDY2, INPUT);
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI);

  // ADS1299 power-up (datasheet 10.1.2): PWDN + RESET high, wait for supplies/reference, reset pulse
  digitalWrite(PIN_PWDN, HIGH); digitalWrite(PIN_RESET, HIGH); delay(150);
  digitalWrite(PIN_RESET, LOW); delayMicroseconds(10); digitalWrite(PIN_RESET, HIGH); delay(10);
  defaults();
  Serial.printf("ADS1299 IDs: 0x%02X 0x%02X (expect 0x3E)\n", rreg(PIN_CS1, ID_REG), rreg(PIN_CS2, ID_REG));

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);                                       // lowest latency while streaming
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) { delay(250); digitalWrite(PIN_LED_B, i & 1); }
  digitalWrite(PIN_LED_B, WiFi.status() == WL_CONNECTED);
  Serial.printf("Wi-Fi: %s  IP %s\n", WiFi.status() == WL_CONNECTED ? "connected" : "FAILED",
                WiFi.localIP().toString().c_str());
  setupHttp();
  attachInterrupt(digitalPinToInterrupt(PIN_DRDY1), onDrdy, FALLING);
}

void loop() {
  http.handleClient();
  if (Serial.available()) {                                   // same commands over USB for bench tests
    String s = Serial.readString();
    Serial.println(handleCommand(s));
  }
  if (streaming && dataReady) {
    dataReady = false;
    uint8_t a[24], b[24];
    readChip(PIN_CS1, a);
    readChip(PIN_CS2, b);
    sendPacket(sampleNum, a);                                 // channels 1-8
    sendPacket(sampleNum, b);                                 // channels 9-16, same sample number
    sampleNum++;
  }
}
