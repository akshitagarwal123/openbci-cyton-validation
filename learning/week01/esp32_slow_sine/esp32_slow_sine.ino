// Week 1: a very slow sine on G25 so a multimeter can follow it.
// Default: one full wave every 10 s (0.1 Hz), from about 0.25 V up to 3.1 V and back.
// Also prints the voltage being output 5 times a second (Serial Monitor / Plotter, 115200 baud).
// Type a frequency in Hz (0.02 to 2) and press Enter to change it.

#include <math.h>

const int DAC_PIN = 25;
const int DAC_MID = 128, DAC_AMP = 110;       // bigger swing: about 0.25 V to 3.1 V
float freq = 0.1;                             // waves per second (0.1 = one wave every 10 s)
double phase = 0;
uint32_t lastT, lastPrint;

void setup() {
  Serial.begin(115200);
  lastT = lastPrint = millis();
}

void loop() {
  if (Serial.available()) {
    float f = Serial.parseFloat();
    while (Serial.available()) Serial.read();
    if (f >= 0.02 && f <= 2) freq = f;
  }
  uint32_t now = millis();
  phase += 2 * M_PI * freq * (now - lastT) / 1000.0;   // advance by the time that passed
  lastT = now;
  if (phase >= 2 * M_PI) phase -= 2 * M_PI;
  int code = DAC_MID + (int)lround(DAC_AMP * sin(phase));
  dacWrite(DAC_PIN, code);
  if (now - lastPrint >= 200) {
    lastPrint = now;
    Serial.printf("G25_volts:%.2f\n", code * 3.3 / 255);
  }
  delay(5);
}
