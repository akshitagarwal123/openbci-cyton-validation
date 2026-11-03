// Week 2: read your ECG with an AD8232 module and the ESP32's ADC, send it to the laptop over USB.
// On the laptop, run:  python3 plot_ecg.py
//
// SAFETY: the laptop must run on BATTERY (charger unplugged), with nothing else plugged into it
// that goes to the wall socket (monitor, hub with its own power). Then there is no path from the
// mains to your body. The AD8232 module is for learning only, not a medical device.
//
// Wiring (ESP32 DevKit V1, 38 pins, USB at the bottom; left header counted from the top):
//   AD8232 GND    -> ESP32 GND     (left pin 14)
//   AD8232 3.3V   -> ESP32 3V3     (left pin 1)    NOT 5V: the module runs on 3.3 V
//   AD8232 OUTPUT -> ESP32 GPIO 34 (left pin 5)    analog ECG, 0..3.3 V, resting near 1.5 V
//   AD8232 LO-    -> ESP32 GPIO 33 (left pin 8)    goes HIGH when an electrode is off
//   AD8232 LO+    -> ESP32 GPIO 32 (left pin 7)    goes HIGH when an electrode is off
//   AD8232 SDN    -> not connected (the module keeps it on)

const int ECG_PIN = 34;          // ADC1 channel 6. ADC1 pins still work when Wi-Fi is on (ADC2 pins don't)
const int LO_MINUS_PIN = 33;     // leads-off detect, negative electrode
const int LO_PLUS_PIN = 32;      // leads-off detect, positive electrode
const int SAMPLE_RATE = 250;     // samples per second (ECG content is below ~40 Hz, so 250 is plenty)

uint32_t nextSampleUs;           // when the next sample is due (micros)

void setup() {
  Serial.begin(115200);          // 250 lines/s x ~8 bytes = 2 kB/s, well under 115200 baud (~11.5 kB/s)
  pinMode(LO_MINUS_PIN, INPUT);
  pinMode(LO_PLUS_PIN, INPUT);
  analogReadResolution(12);      // 12-bit ADC: values 0..4095
  analogSetPinAttenuation(ECG_PIN, ADC_11db);   // input range up to ~3.1 V, so the whole 0..3.3 V swing fits
  nextSampleUs = micros();
}

void loop() {
  if ((int32_t)(micros() - nextSampleUs) < 0) return;   // not time yet
  nextSampleUs += 1000000 / SAMPLE_RATE;                // every 4000 us -> exactly 250 Hz

  // Leads off? Then the OUTPUT pin is meaningless, so flag it (1) and the laptop shows a warning.
  int leadsOff = digitalRead(LO_MINUS_PIN) || digitalRead(LO_PLUS_PIN);
  int mv = analogReadMilliVolts(ECG_PIN);               // ADC reading, calibrated to millivolts

  // One line per sample: "millivolts,leadsOff"  e.g. "1532,0"
  Serial.print(mv);
  Serial.print(',');
  Serial.println(leadsOff);
}
