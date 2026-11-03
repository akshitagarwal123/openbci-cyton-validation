// Week 2: ESP32 DevKit V1 blink.
// GPIO 2 = right header, pin 15. (This clone has no LED on GPIO 2:
// check it with a multimeter, red probe on pin 15, black on pin 1 GND.)
// Anything after "//" is a comment: the compiler ignores it.

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

// The pin we switch. "const" = can never change.
const int LED = 2;

// How long each half of the blink lasts, in milliseconds (5000 ms = 5 s).
const unsigned long HALF_MS = 5000;

// How often to print while waiting (200 ms = 5 lines per second).
const unsigned long PRINT_EVERY_MS = 200;

// Counts the blinks. Lives outside the functions, so it keeps its value.
int count = 0;

// ---------------------------------------------------------------------------
// holdAndPrint(): stay in the current state for `durationMs`,
// printing `label` every PRINT_EVERY_MS so the Serial Monitor shows it live.
// ---------------------------------------------------------------------------
void holdAndPrint(const char *label, unsigned long durationMs) {
  // millis() = milliseconds since the board started. It keeps counting up.
  unsigned long start = millis();

  // Keep going until durationMs has passed since `start`.
  while (millis() - start < durationMs) {
    // Print e.g. "ON   blink 3   1.2 s"
    Serial.print(label);
    Serial.print("   blink ");
    Serial.print(count);
    Serial.print("   ");
    Serial.print((millis() - start) / 1000.0, 1);  // seconds, 1 decimal place
    Serial.println(" s");

    // Short wait between lines, so we don't flood the Mac.
    delay(PRINT_EVERY_MS);
  }
}

// ---------------------------------------------------------------------------
// setup(): runs ONCE, at power-on or reset
// ---------------------------------------------------------------------------
void setup() {
  // Start the USB serial link. The Serial Monitor must also be on 115200 baud.
  Serial.begin(115200);

  // Make GPIO 2 an output, so the chip can drive it to 3.3 V or 0 V.
  pinMode(LED, OUTPUT);

  Serial.println("BrainTech ESP32 blink started");
}

// ---------------------------------------------------------------------------
// loop(): runs FOREVER
// ---------------------------------------------------------------------------
void loop() {
  count++;  // one more blink

  // 3.3 V on GPIO 2 -> LED on (if one is wired). Print "ON" for 5 s.
  digitalWrite(LED, HIGH);
  holdAndPrint("ON ", HALF_MS);

  // 0 V on GPIO 2 -> LED off. Print "OFF" for 5 s.
  digitalWrite(LED, LOW);
  holdAndPrint("OFF", HALF_MS);

  // One full cycle = 5 s on + 5 s off = 10 s.
}
