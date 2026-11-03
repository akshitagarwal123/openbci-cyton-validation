// Week 2: ESP32 joins Wi-Fi and sends FAKE 8-channel EEG to the Mac over UDP.
// It pretends to be an ADS1299: 8 channels, 250 samples per second, values in microvolts (uV).
// On the Mac, run:  python3 receive_fake8.py --plot
//
// Setup: copy secrets.example.h -> secrets.h and fill in your Wi-Fi name and password.

#include <WiFi.h>      // ESP32 Wi-Fi library: join a network, get an IP address
#include <WiFiUdp.h>   // UDP library: send small "fire and forget" packets over the network
#include "secrets.h"   // our file with WIFI_SSID and WIFI_PASS (git-ignored, never on GitHub)

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
const int   UDP_PORT = 12345;          // "door number" on the Mac; the receiver listens on this port
const int   SAMPLE_RATE = 250;         // samples per second, same as the Cyton's default
const int   SAMPLES_PER_PACKET = 10;   // group 10 samples into one packet -> 25 packets per second
const int   NUM_CH = 8;                // 8 channels, like one ADS1299

// Where to send. "" = broadcast to every device on the Wi-Fi (simple, but broadcast packets are
// never confirmed or resent, so many get lost). An IP = send to that one device (unicast):
// Wi-Fi confirms each packet and resends lost ones, so almost nothing is lost.
// Your Mac's IP: System Settings -> Wi-Fi -> Details, or run `ipconfig getifaddr en0`.
const char *TARGET_IP = "192.168.1.8";

// Each fake channel = a sine wave (frequency in Hz, amplitude in uV) + a little noise.
// Real EEG bands: theta 4-8 Hz, alpha 8-12 Hz, beta 13-30 Hz.
const float FREQ_HZ[NUM_CH] = {10, 10, 20, 6, 12, 8, 15, 30};   // wave speed of ch1..ch8
const float AMP_UV[NUM_CH]  = {20, 15, 10, 25, 12, 18,  8,  5};  // wave height of ch1..ch8, in uV
const float NOISE_UV = 2.0;                                      // random noise added: up to +/-2 uV

// ---------------------------------------------------------------------------
// Variables that live for the whole program
// ---------------------------------------------------------------------------
WiFiUDP udp;                 // the UDP "sender" object
IPAddress target;            // where we send: the Mac's IP, or the broadcast address
uint32_t sampleNum = 0;      // counts every sample, so the Mac can spot lost packets
uint32_t nextSampleUs;       // the time (in microseconds) when the next sample is due
String packet;               // text being built up for the next UDP packet
int inPacket = 0;            // how many samples are in `packet` so far (0..10)

// ---------------------------------------------------------------------------
// connectWiFi(): join the Wi-Fi network. Waits here until connected.
// ---------------------------------------------------------------------------
void connectWiFi() {
  Serial.printf("Connecting to Wi-Fi \"%s\"", WIFI_SSID);   // show which network we're trying
  WiFi.mode(WIFI_STA);              // STA = "station": join an existing network, like a phone does
  WiFi.setSleep(false);             // keep the radio always awake, for steady streaming
  WiFi.begin(WIFI_SSID, WIFI_PASS); // start connecting with the name and password
  while (WiFi.status() != WL_CONNECTED) {   // repeat until the router says "you're in"
    delay(500);                     // wait half a second
    Serial.print(".");              // print a dot so you can see it is still trying
  }
  if (strlen(TARGET_IP) > 0) {
    target.fromString(TARGET_IP);   // unicast: send only to this device (e.g. the Mac)
  } else {
    // Broadcast address = the network address with the last part set to 255, e.g. 192.168.1.255.
    // Every device on the network receives it, so we don't need to know the Mac's IP.
    target = WiFi.broadcastIP();
  }
  // Print our IP, the signal strength (dBm: -30 great, -80 weak) and where we send to.
  Serial.printf("\nConnected. ESP32 IP %s, signal %d dBm, sending to %s:%d\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                target.toString().c_str(), UDP_PORT);
}

// ---------------------------------------------------------------------------
// fakeUv(): make one fake value for channel `ch` at time `t` (seconds)
// ---------------------------------------------------------------------------
float fakeUv(int ch, float t) {
  // random(-1000, 1001) gives a whole number from -1000 to 1000; /1000 -> -1.0..+1.0; x 2 uV.
  float noise = NOISE_UV * (random(-1000, 1001) / 1000.0);
  // Sine wave: height AMP_UV, FREQ_HZ waves per second, plus the noise.
  return AMP_UV[ch] * sin(2 * PI * FREQ_HZ[ch] * t) + noise;
}

// ---------------------------------------------------------------------------
// setup(): runs ONCE, at power-on or reset
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);       // start the USB serial link (Serial Monitor at 115200 baud)
  delay(200);                 // give the Serial Monitor a moment to connect
  connectWiFi();              // join Wi-Fi (waits until connected)
  udp.begin(UDP_PORT);        // open our UDP socket
  nextSampleUs = micros();    // the first sample is due right now
}

// ---------------------------------------------------------------------------
// loop(): runs FOREVER. Makes one sample every 4 ms (1 / 250 Hz = 0.004 s).
// ---------------------------------------------------------------------------
void loop() {
  // Not time for the next sample yet? Leave loop() now; Arduino calls it again straight away.
  // (int32_t)(a - b) < 0 is a safe way to compare times, even when micros() wraps around.
  if ((int32_t)(micros() - nextSampleUs) < 0) return;

  // Schedule the next sample exactly 4000 us later. Adding to the schedule (not to "now")
  // keeps the rate at exactly 250 Hz even if sending a packet takes a little time.
  nextSampleUs += 1000000 / SAMPLE_RATE;

  float t = sampleNum / (float)SAMPLE_RATE;   // this sample's time in seconds (sample 250 = 1.0 s)

  // Build one text line for this sample:  sampleNum,ch1,ch2,...,ch8
  packet += String(sampleNum);                // start the line with the sample number
  for (int ch = 0; ch < NUM_CH; ch++) {       // for each of the 8 channels:
    packet += ",";                            //   add a comma separator
    packet += String(fakeUv(ch, t), 2);       //   add the fake value, 2 decimal places, in uV
  }
  packet += "\n";                             // end the line
  sampleNum++;                                // next sample gets the next number
  inPacket++;                                 // one more sample waiting in `packet`

  // Once 10 samples are waiting, send them as one UDP packet.
  if (inPacket == SAMPLES_PER_PACKET) {
    udp.beginPacket(target, UDP_PORT);        // address the packet: broadcast IP, port 12345
    udp.print(packet);                        // put the 10 lines of text in it
    udp.endPacket();                          // send it over Wi-Fi
    packet = "";                              // empty the text for the next 10 samples
    inPacket = 0;                             // reset the count
  }

  // Once a second (every 250 samples), print a status line to the Serial Monitor.
  if (sampleNum % SAMPLE_RATE == 0) {         // % = remainder; 0 means a multiple of 250
    Serial.printf("sent %lu samples, Wi-Fi %s, signal %d dBm\n", (unsigned long)sampleNum,
                  WiFi.status() == WL_CONNECTED ? "OK" : "LOST", WiFi.RSSI());
  }

  // If the Wi-Fi connection dropped, join again.
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
}
