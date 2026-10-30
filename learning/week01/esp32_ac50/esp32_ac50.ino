// Week 1: a clean, continuous 50 Hz sine wave on G25 (like mains AC, but tiny and safe).
// The DAC is updated 10,000 times a second = 200 steps per wave, with no pauses.
// Swing: about 0.25 V to 3.1 V around 1.65 V (DAC can't go below 0 V).
//   AC part = about 1.42 V peak = about 1.0 V RMS.
// For a true AC signal that swings above AND below 0 V, put a capacitor in series (see notes).
// Type a frequency in Hz (1 to 1000) in the Serial Monitor (115200 baud) to change it.

#include <math.h>

const int DAC_PIN = 25;
const float FS = 10000.0;                     // DAC updates per second
const int DAC_MID = 128, DAC_AMP = 110;
float freq = 50;
double phase = 0;
uint32_t nextT, lastPrint;

void setup() {
  Serial.begin(115200);
  nextT = micros();
  lastPrint = millis();
}

void loop() {
  while ((int32_t)(micros() - nextT) < 0) {}  // wait for the next 100 µs slot
  nextT += 100;
  phase += 2 * M_PI * freq / FS;
  if (phase >= 2 * M_PI) phase -= 2 * M_PI;
  dacWrite(DAC_PIN, DAC_MID + (int)lround(DAC_AMP * sin(phase)));

  if (Serial.available()) {                   // new frequency typed by the user
    float f = Serial.parseFloat();
    while (Serial.available()) Serial.read();
    if (f >= 1 && f <= 1000) freq = f;
    nextT = micros();
  }
  if (millis() - lastPrint >= 1000) {         // short status line once a second
    lastPrint = millis();
    Serial.printf("G25: %.1f Hz sine, 0.25-3.1 V (about 1.0 V RMS AC part)\n", freq);
  }
}
