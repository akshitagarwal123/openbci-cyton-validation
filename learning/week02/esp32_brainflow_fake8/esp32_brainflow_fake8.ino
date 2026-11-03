// Week 2: ESP32 pretends to be an OpenBCI Cyton + Wi-Fi Shield, sending FAKE 8-channel EEG.
// BrainFlow (board CYTON_WIFI) and the OpenBCI GUI can then connect to it with no changes.
// On the Mac, run:  python3 brainflow_fake8.py --ip <ESP32 IP>
//
// How BrainFlow talks to a Wi-Fi Shield (from BrainFlow's openbci_wifi_shield_board.cpp):
//   1. BrainFlow opens a TCP server on the Mac.
//   2. GET  /board                    -> we say "I'm a Cyton with 8 channels"
//   3. POST /tcp {"ip","port",...}    -> we connect to the Mac's TCP server (we are the client)
//   4. POST /command {"command":"~4"} -> set the sample rate (~4 = 1000 Hz), then "d" = defaults
//   5. GET  /stream/start             -> we start sending 33-byte Cyton packets over TCP
//   6. GET  /stream/stop              -> we stop
//
// Setup: copy secrets.example.h -> secrets.h and fill in your Wi-Fi name and password.

#include <WiFi.h>        // join the Wi-Fi network
#include <WebServer.h>   // small HTTP server: answers BrainFlow's /board, /tcp, /command ...
#include "secrets.h"     // WIFI_SSID, WIFI_PASS (git-ignored)

// ---------------------------------------------------------------------------
// Fake signals (same as the UDP sketch): a sine wave per channel + noise, in microvolts
// ---------------------------------------------------------------------------
const int   NUM_CH = 8;
const float FREQ_HZ[NUM_CH] = {10, 10, 20, 6, 12, 8, 15, 30};   // wave speed of ch1..ch8
const float AMP_UV[NUM_CH]  = {20, 15, 10, 25, 12, 18,  8,  5};  // wave height of ch1..ch8
const float NOISE_UV = 2.0;                                      // random noise up to +/-2 uV

// ADS1299 conversion, the same formula BrainFlow uses to turn counts back into uV:
//   uV = counts x 4.5 V / (2^23 - 1) / gain x 1,000,000
const float GAIN = 24;                                            // Cyton default gain
const float UV_PER_COUNT = 4.5 / 8388607.0 / GAIN * 1e6;          // = 0.02235 uV per count

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
WebServer http(80);          // HTTP server on port 80 (the normal web port)
WiFiClient tcp;              // TCP connection to BrainFlow on the Mac
int sampleRate = 250;        // changed by "~4" (1000), "~5" (500), "~6" (250)
bool streaming = false;      // true between /stream/start and /stream/stop
uint32_t sampleCount = 0;    // total samples made (for the fake waves' time)
uint8_t sampleNum = 0;       // Cyton packet counter: 0..255, then wraps to 0
uint32_t nextSampleUs;       // when the next sample is due (micros)

const int PACKETS_PER_WRITE = 10;              // send 10 packets per TCP write (fewer, bigger writes)
uint8_t outBuf[33 * PACKETS_PER_WRITE];        // packets waiting to be sent
int outCount = 0;                              // how many packets are in outBuf

// ---------------------------------------------------------------------------
// Tiny JSON readers (BrainFlow sends small JSON bodies like {"ip":"192.168.1.8","port":6677})
// ---------------------------------------------------------------------------
String jsonString(const String &body, const char *key) {          // value of "key":"..."
  int k = body.indexOf(String("\"") + key + "\"");                 // find "key"
  if (k < 0) return "";
  int a = body.indexOf('"', body.indexOf(':', k) + 1);             // opening quote of the value
  int b = body.indexOf('"', a + 1);                                // closing quote
  return (a < 0 || b < 0) ? "" : body.substring(a + 1, b);
}
long jsonInt(const String &body, const char *key) {               // value of "key":123
  int k = body.indexOf(String("\"") + key + "\"");
  return k < 0 ? -1 : body.substring(body.indexOf(':', k) + 1).toInt();
}

// ---------------------------------------------------------------------------
// Start / stop streaming
// ---------------------------------------------------------------------------
void startStream() {
  streaming = true;
  sampleNum = 0;              // Cyton restarts its packet counter at 0
  outCount = 0;
  nextSampleUs = micros();    // first sample due now
  Serial.printf("Streaming started at %d Hz\n", sampleRate);
}
void stopStream() {
  streaming = false;
  Serial.println("Streaming stopped");
}

// ---------------------------------------------------------------------------
// Cyton text commands (sent by BrainFlow's config_board / the GUI)
// ---------------------------------------------------------------------------
String handleCommand(const String &s) {
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == 'b') startStream();                                   // b = begin streaming
    else if (c == 's') stopStream();                               // s = stop streaming
    else if (c == 'v') return "OpenBCI V3 8-16 channel\nBrainTech fake Cyton$$$";   // v = version / reset
    else if (c == '~' && i + 1 < s.length()) {                     // ~N = sample rate
      char r = s[++i];
      if (r == '4') sampleRate = 1000;
      else if (r == '5') sampleRate = 500;
      else if (r == '6') sampleRate = 250;
      Serial.printf("Sample rate set to %d Hz\n", sampleRate);
    }
    // Everything else (channel settings, test signals, "d" defaults) is accepted and ignored:
    // our data is fake, so there are no real ADS1299 registers to change.
  }
  return "Success$$$";       // "$$$" is how a Cyton marks the end of a reply
}

// ---------------------------------------------------------------------------
// HTTP routes: the Wi-Fi Shield's web API that BrainFlow calls
// ---------------------------------------------------------------------------
void setupHttp() {
  http.on("/board", HTTP_GET, [] {                                 // step 2: what board are you?
    http.send(200, "application/json",
              "{\"board_connected\":true,\"board_type\":\"cyton\","
              "\"gains\":[24,24,24,24,24,24,24,24],\"num_channels\":8}");
  });
  http.on("/tcp", HTTP_POST, [] {                                  // step 3: connect to me here
    String body = http.arg("plain");                               // the JSON body
    String ip = jsonString(body, "ip");                            // Mac's IP
    uint16_t port = (uint16_t)jsonInt(body, "port");               // Mac's TCP port
    tcp.stop();                                                    // drop any old connection
    bool ok = tcp.connect(ip.c_str(), port);                       // connect to BrainFlow
    tcp.setNoDelay(true);                                          // send small packets right away
    Serial.printf("TCP to %s:%u %s\n", ip.c_str(), port, ok ? "connected" : "FAILED");
    http.send(ok ? 200 : 500, "application/json",
              String("{\"connected\":") + (ok ? "true" : "false") + "}");
  });
  http.on("/command", HTTP_POST, [] {                              // step 4: Cyton commands
    String c = jsonString(http.arg("plain"), "command");
    Serial.printf("Command \"%s\"\n", c.c_str());
    http.send(200, "text/plain", handleCommand(c));
  });
  http.on("/stream/start", HTTP_GET, [] { startStream(); http.send(200, "text/plain", "Stream started"); });
  http.on("/stream/stop",  HTTP_GET, [] { stopStream();  http.send(200, "text/plain", "Stream stopped"); });
  http.begin();                                                    // start listening on port 80
}

// ---------------------------------------------------------------------------
// Build one 33-byte Cyton packet for the current sample and add it to outBuf
//   byte 0      0xA0 (start byte)
//   byte 1      sample number 0..255
//   bytes 2-25  8 channels x 3 bytes, 24-bit signed, most significant byte first
//   bytes 26-31 accelerometer (zeros here)
//   byte 32     0xC0 (end byte)
// ---------------------------------------------------------------------------
void addPacket() {
  uint8_t *p = outBuf + 33 * outCount;                             // where this packet goes
  float t = sampleCount / (float)sampleRate;                       // this sample's time in seconds
  p[0] = 0xA0;
  p[1] = sampleNum;
  for (int ch = 0; ch < NUM_CH; ch++) {
    float noise = NOISE_UV * (random(-1000, 1001) / 1000.0);      // -2..+2 uV
    float uv = AMP_UV[ch] * sin(2 * PI * FREQ_HZ[ch] * t) + noise; // fake EEG value in uV
    int32_t counts = lroundf(uv / UV_PER_COUNT);                   // uV -> ADC counts
    p[2 + 3 * ch] = (counts >> 16) & 0xFF;                         // top byte
    p[3 + 3 * ch] = (counts >> 8) & 0xFF;                          // middle byte
    p[4 + 3 * ch] = counts & 0xFF;                                 // bottom byte
  }
  memset(p + 26, 0, 6);                                            // no accelerometer
  p[32] = 0xC0;
  outCount++;
  sampleNum++;                                                     // uint8_t wraps 255 -> 0 by itself
  sampleCount++;
}

// ---------------------------------------------------------------------------
// setup(): runs once
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.printf("Connecting to Wi-Fi \"%s\"", WIFI_SSID);
  WiFi.mode(WIFI_STA);                  // join an existing network
  WiFi.setSleep(false);                 // radio always on, for steady streaming
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  // BrainFlow needs this IP address: python3 brainflow_fake8.py --ip <this>
  Serial.printf("\nConnected. ESP32 IP %s  (use this in BrainFlow), signal %d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
  setupHttp();
}

// ---------------------------------------------------------------------------
// loop(): runs forever
// ---------------------------------------------------------------------------
void loop() {
  http.handleClient();                                             // answer any HTTP request waiting

  if (!streaming) return;                                          // nothing to send yet
  if (!tcp.connected()) { stopStream(); return; }                  // BrainFlow went away

  // Make every sample that is due (catches up if a write took a moment).
  while ((int32_t)(micros() - nextSampleUs) >= 0) {
    nextSampleUs += 1000000 / sampleRate;                          // 1000 us at 1000 Hz
    addPacket();
    if (outCount == PACKETS_PER_WRITE) {                           // 10 packets ready
      tcp.write(outBuf, 33 * outCount);                            // send 330 bytes at once
      outCount = 0;
    }
  }
}
