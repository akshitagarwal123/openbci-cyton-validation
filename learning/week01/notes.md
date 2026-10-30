# Week 1: electronics basics and RC filters (24–31 Oct 2026)

## Done
- Read Practical Electronics for Inventors Ch 1 and Ch 2 (current, voltage, resistance, grounds, Ohm's law, Kirchhoff, AC, capacitors).
- Installed KiCad 10.0.4 and LTspice 26.
- **First LTspice simulation:** RC low-pass, R = 10 kΩ, C = 0.47 µF, AC sweep 1 Hz – 1 kHz (`rc_lowpass.cir`).
  - Result: flat at 0 dB below ~10 Hz, **−3 dB at ≈ 34 Hz**, phase −45° there, then −20 dB per decade (−29 dB at 1 kHz). Matches theory f_c = 1/(2πRC) = 33.9 Hz.
- Placed the ESP32 DevKit V1 on the breadboard (`esp32_on_breadboard.jpg`); planned the ESP32 test rig (DAC sine on G25 → RC filter → ADC G35/G34) to measure a real Bode plot.

## What I learned
- **dB** is a ratio: 20·log10(Vout/Vin). −3 dB = 71 % (half power), −6 dB = half, −20 dB = one tenth.
- **Capacitor = frequency-dependent resistance:** X_C = 1/(2πfC). Low-pass cutoff is where X_C equals R.
- Rules of thumb: well below f_c → ~100 % passes; at f_c → 70 %; well above → f_c / f.
- For EEG with this filter: alpha (10 Hz) 96 %, beta (20 Hz) 86 %, mains (50 Hz) 56 %. One RC is not enough to remove mains noise.
- LTspice units: `u` = micro, `n` = nano, `k` = kilo, `meg` = mega (`M` means milli!). "0.47C" was read as 0.47 F.
- LTspice 26 on Mac: move parts with Edit → Move (F7 does not work), Edit → Stretch keeps wires attached.

## Next
- Measure the 10 kΩ resistor with the multimeter, find the 0.47 µF (code 474) capacitor.
- Wire the RC filter to the ESP32, run the DAC sweep, compare measured vs LTspice curve.
- KiCad beginner tutorial → practice board with 0 DRC errors.
- Week 1 assignment in the tracker.

## 30 Oct: G25 as a 50 Hz source, and its internal resistance

Sketch: `esp32_ac50/` (continuous 50 Hz sine on G25, 0.25–3.1 V around 1.65 V).

| Measurement | Result |
|---|---|
| G25 to GND, DC V, no load | 1.64 V (meter shows the average of the 50 Hz sine) |
| Resistor value (Ω 200 range) | 10.1 Ω (brown-black-black-gold). Ω 2000 range read "32": range too coarse |
| G25 with 10 Ω load | 0.34 V |
| G25 to GND through the ammeter (≈ short) | 34–38 mA |
| R = V / I with 10 Ω in circuit | ≈ 10.5 Ω (matches 10.1 Ω) |

G25 internal resistance (Thévenin):
- From the sag: 10.1 × (1.65 / 0.34 − 1) ≈ 39 Ω
- From open voltage ÷ short current: 1.64 / 0.034–0.038 ≈ 43–48 Ω
- **≈ 40–50 Ω**

Lessons:
- A signal pin is not a power supply. Heavy loads (10 Ω) make it sag; light loads (10 kΩ) don't.
- One open-circuit reading can't give internal resistance; you need a second, loaded reading.
- Use the lowest meter range that doesn't read "1".
- Ammeter across a pin is a short circuit: 38 mA is at the ESP32 pin limit (~40 mA). Never across a battery.
- Fix for driving loads: op-amp voltage follower (buffer), coming in week 2.

## 30 Oct: breadboard RC low-pass filter works

Final circuit: G25 → 1 kΩ → row 34 → 47 µF electrolytic (+ to row 34, stripe to GND). G35 reads input, G34 reads output.
f_c = 1 / (2π × 1 kΩ × 47 µF) = 3.4 Hz. Measured with `esp32_scope/sweep.py`:

| Freq | Output measured | Theory | Delay measured | Theory |
|---|---|---|---|---|
| 5 Hz | 58 % | 56 % | −56° | −56° |
| 10 Hz | 30 % | 32 % | −67° | −71° |
| 20 Hz | 18 % | 17 % | −86° | −80° |
| 50 Hz | 8 % | 7 % | −99° | −86° |
| 100 Hz | 5 % | 3 % | −93° | −88° |

Debugging lessons (why it took several tries):
1. Capacitor marked "100" is **10 pF**, not 0.1 µF (0.1 µF = "104"). f_c was ~159 kHz → no filtering.
2. Capacitor's − leg was in a **split half of the power rail**, not GND → no current, output = input. Clue: 0 V DC across the capacitor.
3. Wrong resistor (~500 kΩ instead of 1 kΩ) → f_c 0.007 Hz → output flat.
4. DC meter readings: across R ≈ 0 (leak only), across C ≈ input average; they add up to the input (Kirchhoff).
5. Input amplitude sags from 1.7 V to ~0.5 V under this load: G25 is weak; an op-amp buffer fixes this.

## 31 Oct: DC step into the RC filter (capacitor charging)

Sketch `esp32_dc_step/` switches G25 from 0 V to steady DC (1.65 V target) and records input/output every 0.5 ms; `dc_step_plot.py` plots it (`dc_step.png`).
RC = 1 kΩ × 47 µF = 47 ms.

| t | input | output (across C) | across R |
|---|---|---|---|
| 0 ms | 1.51 V | 0.38 V | 1.13 V |
| 47 ms (1 RC) | 1.51 V | 1.09 V | 0.43 V |
| 100 ms | 1.52 V | 1.37 V | 0.15 V |
| 250 ms (≈5 RC) | 1.52 V | 1.51 V | 0.01 V |

- DC passes a low-pass filter 100% once the capacitor is charged; the current and the voltage across R fall to ~0.
- Output started at 0.38 V, not 0 (capacitor not fully emptied / DAC and ADC not reaching true 0 V). Using that start, V = 1.52 − 1.14·e^(−t/47 ms) matches every point (47 ms → 1.10 V predicted, 1.09 V measured).
- DC input read 1.52 V instead of 1.65 V: ESP32 ADC/DAC calibration error of ~0.1 V is normal.
