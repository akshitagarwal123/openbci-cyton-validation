// Week 1: measure a real Bode plot of a breadboard RC filter with an ESP32 DevKit V1.
//   G25 (DAC) -> sine wave into the filter;  G35 (ADC) reads the filter input;  G34 (ADC) reads the output.
// For each test frequency the ESP32 plays the sine, samples both pins at 10 kHz, and uses a
// lock-in (multiply by sin and cos, then average) to get each wave's size and timing.
// Prints one CSV line per frequency: freq_hz,gain,phase_deg   (gain = output size / input size)

#include <math.h>

const int DAC_PIN = 25, ADC_IN = 35, ADC_OUT = 34;
const float FS = 10000.0;                       // samples per second (one every 100 µs)
const int DAC_MID = 128, DAC_AMP = 70;          // sine around 1.65 V, about ±0.9 V
const float FREQS[] = {5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 700, 1000};

void measure(float f, float &gain, float &phaseDeg) {
  int cycles = max(5, (int)(f * 0.5));          // at least 5 cycles, about half a second
  int settle = (int)(2 * FS / f);               // first 2 cycles let the filter settle
  int n = (int)lround(cycles * FS / f);
  double si = 0, ci = 0, so = 0, co = 0;
  uint32_t t0 = micros();
  for (int i = 0; i < settle + n; i++) {
    while ((uint32_t)(micros() - t0) < (uint32_t)(i * 1e6 / FS)) {}   // wait for this sample's time
    double ph = 2 * M_PI * f * i / FS;
    dacWrite(DAC_PIN, DAC_MID + (int)lround(DAC_AMP * sin(ph)));
    int vin = analogRead(ADC_IN), vout = analogRead(ADC_OUT);
    if (i >= settle) {
      si += vin * sin(ph);  ci += vin * cos(ph);
      so += vout * sin(ph); co += vout * cos(ph);
    }
  }
  double ain = hypot(si, ci), aout = hypot(so, co);
  gain = aout / ain;
  phaseDeg = (atan2(co, so) - atan2(ci, si)) * 180 / M_PI;
  if (phaseDeg > 180) phaseDeg -= 360;
  if (phaseDeg < -180) phaseDeg += 360;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);               // ADC range about 0–3.1 V
  delay(2000);
}

void loop() {
  Serial.println("start");
  Serial.println("freq_hz,gain,phase_deg");
  for (float f : FREQS) {
    float g, p;
    measure(f, g, p);
    Serial.printf("%.1f,%.4f,%.1f\n", f, g, p);
  }
  Serial.println("done");
  dacWrite(DAC_PIN, DAC_MID);
  delay(5000);                                  // repeat the sweep every few seconds
}
