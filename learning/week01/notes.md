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
