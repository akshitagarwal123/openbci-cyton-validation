// Week 1: a mini oscilloscope for the Arduino IDE Serial Plotter (Tools > Serial Plotter, 115200 baud).
//   G25 (DAC) plays a sine into the RC filter; G35 reads the filter input, G34 the output.
// Each screen shows real samples of a few whole cycles of both waves, in volts.
// Type a frequency in Hz (5 to 1000) in the plotter's message box and press Enter to change it.

#include <math.h>

const int DAC_PIN = 25, ADC_IN = 35, ADC_OUT = 34;
const float FS = 10000.0;                     // sample rate: one sample every 100 µs
const int DAC_MID = 128, DAC_AMP = 70;        // sine around 1.65 V, about ±0.9 V
const int POINTS = 50;                        // points per screen (the plotter shows about 50)
const int MAX_N = 4000;

float freq = 50;
double phase = 0;
uint32_t nextT;
int16_t bufIn[MAX_N], bufOut[MAX_N];

// one 100 µs tick: advance the sine, update the DAC, read both pins
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
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  nextT = micros();
}

void loop() {
  if (Serial.available()) {                   // new frequency typed by the user
    float f = Serial.parseFloat();
    while (Serial.available()) Serial.read();
    if (f >= 5 && f <= 1000) freq = f;
  }
  int cycles = max(2, (int)ceil(POINTS * freq / FS));
  int n = min(MAX_N, (int)lround(cycles * FS / freq));
  int vin, vout;
  nextT = micros();
  for (int i = 0; i < max(300, (int)(3 * FS / freq)); i++) tick(vin, vout);   // let the filter settle
  while (!tick(vin, vout)) {}                                                // start at the top of a cycle
  for (int i = 0; i < n; i++) { tick(vin, vout); bufIn[i] = vin; bufOut[i] = vout; }
  for (int k = 0; k < POINTS; k++) {
    int i = (long)k * n / POINTS;
    Serial.printf("input_V:%.3f,output_V:%.3f,freq_Hz_div1000:%.3f\n",
                  bufIn[i] * 3.3 / 4095, bufOut[i] * 3.3 / 4095, freq / 1000);
  }
}
