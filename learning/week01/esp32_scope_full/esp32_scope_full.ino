// Week 1: mini oscilloscope that sends EVERY sample (all 200 per wave at 50 Hz).
// View with scope_view.py (the Arduino Serial Plotter only shows 50 points).
//   G25 (DAC) sine into the RC filter; G35 reads the input, G34 the output.
// Each frame: "frame,<freq>,<n>" then n lines "in,out" (raw 0-4095 ADC counts).
// Send a frequency in Hz (5 to 1000) followed by a newline to change it.

#include <math.h>

const int DAC_PIN = 25, ADC_IN = 35, ADC_OUT = 34;
const float FS = 10000.0;                     // one sample every 100 µs
const int DAC_MID = 128, DAC_AMP = 70;
const int MAX_N = 4000;

float freq = 50;
double phase = 0;
uint32_t nextT;
int16_t bufIn[MAX_N], bufOut[MAX_N];

bool tick(int &vin, int &vout) {
  while ((int32_t)(micros() - nextT) < 0) {}
  nextT += 100;
  phase += 2 * M_PI * freq / FS;
  bool wrapped = phase >= 2 * M_PI;
  if (wrapped) phase -= 2 * M_PI;
  dacWrite(DAC_PIN, DAC_MID + (int)lround(DAC_AMP * sin(phase)));
  vin = analogRead(ADC_IN);
  vout = analogRead(ADC_OUT);
  return wrapped;
}

void setup() {
  Serial.begin(921600);                       // 8x faster than 115200
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
}

void loop() {
  if (Serial.available()) {
    float f = Serial.parseFloat();
    while (Serial.available()) Serial.read();
    if (f >= 5 && f <= 1000) freq = f;
  }
  int n = min(MAX_N, (int)lround(2 * FS / freq));   // two whole cycles, every sample
  int vin, vout;
  nextT = micros();
  for (int i = 0; i < max(300, (int)(3 * FS / freq)); i++) tick(vin, vout);
  while (!tick(vin, vout)) {}
  for (int i = 0; i < n; i++) { tick(vin, vout); bufIn[i] = vin; bufOut[i] = vout; }
  Serial.printf("frame,%.1f,%d\n", freq, n);
  for (int i = 0; i < n; i++) Serial.printf("%d,%d\n", bufIn[i], bufOut[i]);
}
