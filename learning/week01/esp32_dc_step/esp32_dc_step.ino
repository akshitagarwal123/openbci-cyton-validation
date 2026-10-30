// Week 1: DC step test for the RC filter.
// G25 goes from 0 V to a steady DC level and stays there. G35 (input) and G34 (output)
// are recorded every 0.5 ms for 300 ms, so you can watch the capacitor charge.
// Serial (115200 baud):  s = repeat the step   |   a number like 1.2 = new DC level in volts (0.1-3.1)

const int DAC_PIN = 25, ADC_IN = 35, ADC_OUT = 34;
const int N = 600, DT_US = 500;               // 600 samples x 0.5 ms = 300 ms
int16_t bufIn[N], bufOut[N];
float level = 1.65;

void step() {
  dacWrite(DAC_PIN, 0);                       // start from 0 V and let the capacitor empty
  delay(600);
  int code = constrain((int)lround(level / 3.3 * 255), 0, 255);
  uint32_t t = micros();
  dacWrite(DAC_PIN, code);                    // switch the DC on
  for (int i = 0; i < N; i++) {
    while ((int32_t)(micros() - t) < 0) {}
    t += DT_US;
    bufIn[i] = analogRead(ADC_IN);
    bufOut[i] = analogRead(ADC_OUT);
  }
  Serial.printf("step,%.2f\n", code * 3.3 / 255);
  Serial.println("t_ms,input_V,output_V");
  for (int i = 0; i < N; i++)
    Serial.printf("%.1f,%.3f,%.3f\n", i * DT_US / 1000.0, bufIn[i] * 3.3 / 4095, bufOut[i] * 3.3 / 4095);
  Serial.println("done");                     // G25 now stays at the DC level
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  delay(500);
  step();
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if (cmd == "s") step();
    else { float v = cmd.toFloat(); if (v >= 0.1 && v <= 3.1) { level = v; step(); } }
  }
}
