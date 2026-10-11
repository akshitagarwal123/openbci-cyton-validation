// BrainTech-16 firmware outline (ESP32-S3, Arduino core).
// Reads two ADS1299s (16 channels) and builds OpenBCI Cyton/Daisy packets.
// STATUS: structure + ADS1299 driver; the Wi-Fi Shield-compatible network layer is a TODO.
// Register values follow the OpenBCI Cyton defaults (gain 24, SRB2, BIAS on, 250 SPS).

#include <Arduino.h>
#include <SPI.h>

// ---------- pins (match your schematic) ----------
constexpr int PIN_SCLK = 12, PIN_MOSI = 11, PIN_MISO = 13;
constexpr int PIN_CS1 = 10, PIN_CS2 = 9;       // ADS1299 #1 (ch 1-8, clock master), #2 (ch 9-16)
constexpr int PIN_DRDY = 14;                    // DRDY of ADS1299 #1
constexpr int PIN_START = 15, PIN_RESET = 16, PIN_PWDN = 17;
constexpr int PIN_LED = 48, PIN_VBAT = 1;       // battery divider to ADC

// ---------- ADS1299 opcodes / registers ----------
enum : uint8_t { WAKEUP = 0x02, STANDBY = 0x04, RESET_CMD = 0x06, START_CMD = 0x08, STOP_CMD = 0x0A,
                 RDATAC = 0x10, SDATAC = 0x11, RDATA = 0x12, RREG = 0x20, WREG = 0x40 };
enum : uint8_t { CONFIG1 = 0x01, CONFIG2 = 0x02, CONFIG3 = 0x03, LOFF = 0x04, CH1SET = 0x05,
                 BIAS_SENSP = 0x0D, BIAS_SENSN = 0x0E, MISC1 = 0x15 };

SPISettings ads(4000000, MSBFIRST, SPI_MODE1);   // ADS1299 uses CPOL=0, CPHA=1
volatile bool dataReady = false;
uint8_t sampleCounter = 0;

void IRAM_ATTR onDrdy() { dataReady = true; }

void cmd(int cs, uint8_t c) {
  SPI.beginTransaction(ads); digitalWrite(cs, LOW); SPI.transfer(c); delayMicroseconds(3);
  digitalWrite(cs, HIGH); SPI.endTransaction(); delayMicroseconds(5);
}

void wreg(int cs, uint8_t reg, uint8_t val) {
  SPI.beginTransaction(ads); digitalWrite(cs, LOW);
  SPI.transfer(WREG | reg); SPI.transfer(0x00); SPI.transfer(val);
  delayMicroseconds(3); digitalWrite(cs, HIGH); SPI.endTransaction(); delayMicroseconds(5);
}

uint8_t rreg(int cs, uint8_t reg) {
  SPI.beginTransaction(ads); digitalWrite(cs, LOW);
  SPI.transfer(RREG | reg); SPI.transfer(0x00); uint8_t v = SPI.transfer(0x00);
  digitalWrite(cs, HIGH); SPI.endTransaction(); return v;
}

void configure(int cs, bool clockMaster) {
  cmd(cs, SDATAC);
  // CONFIG1: 250 SPS; master also outputs its clock to chip #2 (CLK_EN)
  wreg(cs, CONFIG1, clockMaster ? 0xB6 : 0x96);
  wreg(cs, CONFIG2, 0xC0);                       // test signals off (0xD0 = 1x slow test, as Cyton '-')
  wreg(cs, CONFIG3, clockMaster ? 0xEC : 0xE0);  // internal ref on; BIAS amp only on the master [verify]
  for (uint8_t ch = 0; ch < 8; ch++) wreg(cs, CH1SET + ch, 0x68);  // gain 24, normal input, SRB2 on
  wreg(cs, BIAS_SENSP, 0xFF);                    // all channels drive BIAS (as Cyton)
  wreg(cs, BIAS_SENSN, 0xFF);
  wreg(cs, MISC1, 0x00);                         // SRB1 off (SRB2 mode)
}

// read status (3 bytes) + 8 channels x 24-bit from one chip
void readChip(int cs, uint8_t out[24]) {
  SPI.beginTransaction(ads); digitalWrite(cs, LOW);
  for (int i = 0; i < 3; i++) SPI.transfer(0x00);
  for (int i = 0; i < 24; i++) out[i] = SPI.transfer(0x00);
  digitalWrite(cs, HIGH); SPI.endTransaction();
}

// OpenBCI Cyton packet: 0xA0, sample#, 24 bytes EEG, 6 bytes aux, 0xC0 (33 bytes)
void buildPacket(uint8_t pkt[33], uint8_t sample, const uint8_t eeg[24]) {
  pkt[0] = 0xA0; pkt[1] = sample;
  memcpy(pkt + 2, eeg, 24);
  memset(pkt + 26, 0, 6);                        // TODO: accelerometer (LIS3DH) as Cyton does
  pkt[32] = 0xC0;
}

void sendPacket(const uint8_t pkt[33]) {
  // TODO: network layer emulating the OpenBCI Wi-Fi Shield HTTP/TCP API so BrainFlow
  // board CYTON_DAISY_WIFI connects (shield firmware is open source: OpenBCI_WIFI repo).
  // Until then: stream over native USB serial for bench testing.
  Serial.write(pkt, 33);
}

void startStreaming() {
  digitalWrite(PIN_START, HIGH);
  cmd(PIN_CS1, RDATAC); cmd(PIN_CS2, RDATAC);
}

void stopStreaming() {
  digitalWrite(PIN_START, LOW);
  cmd(PIN_CS1, SDATAC); cmd(PIN_CS2, SDATAC);
}

void setup() {
  Serial.begin(115200);
  for (int p : {PIN_CS1, PIN_CS2, PIN_START, PIN_RESET, PIN_PWDN, PIN_LED}) pinMode(p, OUTPUT);
  digitalWrite(PIN_CS1, HIGH); digitalWrite(PIN_CS2, HIGH);
  pinMode(PIN_DRDY, INPUT);
  SPI.begin(PIN_SCLK, PIN_MISO, PIN_MOSI);

  // power-up sequence per ADS1299 datasheet: PWDN/RESET high, wait for clocks + reference
  digitalWrite(PIN_PWDN, HIGH); digitalWrite(PIN_RESET, HIGH); delay(150);
  digitalWrite(PIN_RESET, LOW); delayMicroseconds(10); digitalWrite(PIN_RESET, HIGH); delay(10);

  configure(PIN_CS1, true);    // master: outputs 2.048 MHz clock
  configure(PIN_CS2, false);   // slave: CLKSEL pin tied low in hardware, uses master's clock
  Serial.printf("ADS1299 IDs: 0x%02X 0x%02X (expect 0x3E)\n", rreg(PIN_CS1, 0x00), rreg(PIN_CS2, 0x00));

  attachInterrupt(digitalPinToInterrupt(PIN_DRDY), onDrdy, FALLING);
}

void loop() {
  // single-character commands, same as Cyton: b = start, s = stop, d = defaults, - = test signal
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'b') startStreaming();
    else if (c == 's') stopStreaming();
    else if (c == 'd') { stopStreaming(); configure(PIN_CS1, true); configure(PIN_CS2, false); }
    else if (c == '-') { wreg(PIN_CS1, CONFIG2, 0xD0); wreg(PIN_CS2, CONFIG2, 0xD0);
                         for (uint8_t ch = 0; ch < 8; ch++) { wreg(PIN_CS1, CH1SET + ch, 0x65); wreg(PIN_CS2, CH1SET + ch, 0x65); } }
    // TODO: x...X channel settings, z...Z lead-off, as in the OpenBCI Cyton firmware
  }

  if (dataReady) {
    dataReady = false;
    uint8_t a[24], b[24], pkt[33];
    readChip(PIN_CS1, a);
    readChip(PIN_CS2, b);
    // Cyton+Daisy convention: board channels and daisy channels in consecutive packets
    // (odd / even sample numbers), so BrainFlow's CYTON_DAISY parser reassembles 16 channels.
    buildPacket(pkt, sampleCounter++, a); sendPacket(pkt);
    buildPacket(pkt, sampleCounter++, b); sendPacket(pkt);
  }
}
