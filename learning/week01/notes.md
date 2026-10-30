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
