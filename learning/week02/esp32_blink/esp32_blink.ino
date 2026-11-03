// Week 2: ESP32 DevKit V1 blink.
// The blue on-board LED is on GPIO 2 (right header, pin 15). No wiring needed.
// Anything after "//" is a comment: the compiler ignores it, it never goes onto the chip.

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

// Name the pin. Inside the board, GPIO 2 -> resistor -> blue LED -> GND.
// "const" means it can never change; the compiler errors if you try.
// Naming it means you change only this line if the LED moves to another pin.
const int LED = 2;

// Counts how many times the LED has turned on.
// It lives OUTSIDE the functions, so it keeps its value between loops.
// (Declared inside loop(), it would reset to 0 every time.)
int count = 0;

// ---------------------------------------------------------------------------
// setup(): runs ONCE, when the board powers on or is reset
// ---------------------------------------------------------------------------
void setup() {
  // Start the serial link over the USB cable to the Mac.
  // 115200 = baud rate (bits per second). The Serial Monitor must use the
  // same number, or you see garbage characters.
  Serial.begin(115200);

  // A GPIO pin can be an INPUT (read a voltage) or an OUTPUT (drive a voltage).
  // Make GPIO 2 an output so the chip can push it to 3.3 V or pull it to 0 V.
  pinMode(LED, OUTPUT);

  // Print once, so you can see the board has started.
  // println = print the text, then a newline.
  Serial.println("BrainTech ESP32 blink started");
}

// ---------------------------------------------------------------------------
// loop(): runs FOREVER. Behind the scenes Arduino does:
//   setup();  while (true) { loop(); }
// ---------------------------------------------------------------------------
void loop() {
  // 3.3 V on GPIO 2 -> current flows through the resistor and LED to GND -> LED on.
  digitalWrite(LED, HIGH);

  // print (no newline) then println, so this shows as one line: "ON  1".
  // ++count adds 1 FIRST, then prints, so the first loop shows 1, not 0.
  Serial.print("ON  ");
  Serial.println(++count);

  // Wait 500 ms (0.5 s) with the LED on.
  // Without delays the LED would switch millions of times a second
  // and just look dimly on.
  delay(500);

  // 0 V on GPIO 2 -> both ends of the LED at 0 V -> no current -> LED off.
  digitalWrite(LED, LOW);
  Serial.println("OFF");

  // Wait 500 ms with the LED off.
  // One full cycle = 0.5 s on + 0.5 s off = 1 s, so it blinks once a second (1 Hz).
  delay(500);
}  // End of loop(): jump straight back to the top of loop().
