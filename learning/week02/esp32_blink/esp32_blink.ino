// Week 2: ESP32 DevKit V1 blink.
// The blue on-board LED is on GPIO 2 (right header, pin 15). No wiring needed.

const int LED = 2;

int count = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
  Serial.println("BrainTech ESP32 blink started");
}

void loop() {
  digitalWrite(LED, HIGH);   // 3.3 V on GPIO 2 -> LED on
  Serial.print("ON  ");
  Serial.println(++count);
  delay(500);

  digitalWrite(LED, LOW);    // 0 V -> LED off
  Serial.println("OFF");
  delay(500);
}
