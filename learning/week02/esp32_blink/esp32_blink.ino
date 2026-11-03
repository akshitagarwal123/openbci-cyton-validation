// Week 2: ESP32 DevKit V1 blink.
// The blue on-board LED is on GPIO 2.
// Optional external LED: GPIO 4 -> 330 ohm -> LED long leg; LED short leg -> GND.

const int ONBOARD_LED = 2;
const int EXTERNAL_LED = 4;

int count = 0;

void setup() {
  Serial.begin(115200);
  pinMode(ONBOARD_LED, OUTPUT);
  pinMode(EXTERNAL_LED, OUTPUT);
  Serial.println("BrainTech ESP32 blink started");
}

void loop() {
  digitalWrite(ONBOARD_LED, HIGH);
  digitalWrite(EXTERNAL_LED, HIGH);
  Serial.print("ON  ");
  Serial.println(++count);
  delay(500);

  digitalWrite(ONBOARD_LED, LOW);
  digitalWrite(EXTERNAL_LED, LOW);
  Serial.println("OFF");
  delay(500);
}
