// Week 2: ESP32 joins Wi-Fi and sends FAKE 8-channel EEG to the Mac over UDP.
// It pretends to be an ADS1299: 8 channels, 250 samples per second, values in microvolts (uV).
// On the Mac, run:  python3 receive_fake8.py --plot
//
// Setup: copy secrets.example.h -> secrets.h and fill in your Wi-Fi name and password.

#include <WiFi.h>
#include <WiFiUdp.h>
#include "secrets.h"   // WIFI_SSID, WIFI_PASS (git-ignored)

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
const int   UDP_PORT = 12345;          // the Mac listens on this port
const int   SAMPLE_RATE = 250;         // samples per second, same as the Cyton's default
const int   SAMPLES_PER_PACKET = 10;   // send 10 samples together -> 25 packets per second
const int   NUM_CH = 8;

// Each fake channel = a sine wave (frequency in Hz, amplitude in uV) + a little noise.
// Real EEG bands: alpha 8-12 Hz, beta 13-30 Hz, theta 4-8 Hz.
const float FREQ_HZ[NUM_CH] = {10, 10, 20, 6, 12, 8, 15, 30};
const float AMP_UV[NUM_CH]  = {20, 15, 10, 25, 12, 18,  8,  5};
const float NOISE_UV = 2.0;

WiFiUDP udp;
IPAddress target;            // where we send: the network's broadcast address (reaches the Mac)
uint32_t sampleNum = 0;      // counts every sample, so the Mac can spot lost packets
uint32_t nextSampleUs;       // when the next sample is due (micros)
String packet;               // text being built for the next UDP packet
int inPacket = 0;            // how many samples are in `packet` so far

// ---------------------------------------------------------------------------
// Connect to Wi-Fi (blocks until connected, printing progress)
// ---------------------------------------------------------------------------
void connectWiFi() {
  Serial.printf("Connecting to Wi-Fi \"%s\"", WIFI_SSID);
  WiFi.mode(WIFI_STA);              // STA = station: join an existing network, like a phone does
  WiFi.setSleep(false);             // keep the radio awake for steady streaming
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  // Broadcast address = the network address with all "host" bits set, e.g. 192.168.1.255.
  // Every device on the network receives it, so we don't need to know the Mac's IP.
  target = WiFi.broadcastIP();
  Serial.printf("\nConnected. ESP32 IP %s, signal %d dBm, sending to %s:%d\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                target.toString().c_str(), UDP_PORT);
}

// ---------------------------------------------------------------------------
// Make one fake sample for channel ch at time t (seconds)
// ---------------------------------------------------------------------------
float fakeUv(int ch, float t) {
  float noise = NOISE_UV * (random(-1000, 1001) / 1000.0);   // random value in -2..+2 uV
  return AMP_UV[ch] * sin(2 * PI * FREQ_HZ[ch] * t) + noise;
}

// ---------------------------------------------------------------------------
// setup(): runs once
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);
  connectWiFi();
  udp.begin(UDP_PORT);
  nextSampleUs = micros();
}

// ---------------------------------------------------------------------------
// loop(): runs forever. Make one sample every 4 ms (1 / 250 Hz).
// ---------------------------------------------------------------------------
void loop() {
  // Wait until the next sample is due. Using a fixed schedule (+4000 us each time)
  // keeps the rate at exactly 250 Hz even if sending takes a little time.
  if ((int32_t)(micros() - nextSampleUs) < 0) return;
  nextSampleUs += 1000000 / SAMPLE_RATE;

  // One text line per sample:  sampleNum,ch1,ch2,...,ch8
  float t = sampleNum / (float)SAMPLE_RATE;
  packet += String(sampleNum);
  for (int ch = 0; ch < NUM_CH; ch++) {
    packet += ",";
    packet += String(fakeUv(ch, t), 2);   // 2 decimal places, in uV
  }
  packet += "\n";
  sampleNum++;
  inPacket++;

  // Every 10 samples, send them as one UDP packet.
  if (inPacket == SAMPLES_PER_PACKET) {
    udp.beginPacket(target, UDP_PORT);
    udp.print(packet);
    udp.endPacket();
    packet = "";
    inPacket = 0;
  }

  // Once a second, print a status line over USB.
  if (sampleNum % SAMPLE_RATE == 0) {
    Serial.printf("sent %lu samples, Wi-Fi %s, signal %d dBm\n", (unsigned long)sampleNum,
                  WiFi.status() == WL_CONNECTED ? "OK" : "LOST", WiFi.RSSI());
  }

  // If Wi-Fi drops, reconnect.
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
}
