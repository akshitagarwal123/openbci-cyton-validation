# Week 2 notes

## 3 Nov: LTspice non-inverting amplifier, gain 10

Files: `noninv_gain10.asc` (schematic), `noninv_gain10.net` (netlist), `noninv_gain10.png` (plot).

- Op amp: **LT1057** (JFET-input dual, the closest LTspice has to the TL072; there is no TL072 model in the library).
- Rf = 90.9 kΩ, Rg = 10 kΩ → gain = 1 + Rf/Rg = **10.09**.
- Supplies ±4.5 V (stand-in for the 9 V battery split in the middle).
- Input: SINE(0 0.2 100), 0.2 V peak at 100 Hz. `.tran 30m`.

| | Expected | Simulated |
|---|---|---|
| Vout peak | 2.018 V | **2.018 V** |
| Gain | 10.09 | **10.090** |
| V− vs V+ | equal (virtual short) | within **40 µV** |
| Phase | in phase (non-inverting) | in phase |

![simulation](noninv_gain10.png)

Lessons:
- Component picker opens in the last folder used (it was on Digital → "and"), so always search by name and check the preview.
- On this Mac the LTspice menu bar sits on the laptop screen, not the external monitor. Use the toolbar: `.t` = SPICE directive.
- Typing into LTspice via automation comes out as "aaaa"; type by hand.

Next: try amplitude 0.5 V to see clipping at the rails, then build it with the TL072 on the breadboard (Rf = 47k + 47k = 94k → gain 10.4).

## To do at home: TL072 gain-10 amplifier on the breadboard (9 V battery)

Parts: TL072, 9 V battery + snap, 2× 1 kΩ, 2× 100 µF electrolytic, 2× 0.1 µF ("104"), 10 kΩ, 2× 47 kΩ, 100 kΩ, 4.7 kΩ (and 22 kΩ for the clipping test).

1. **Split supply:** battery + → 1 kΩ → GND row → 1 kΩ → battery −. A 100 µF across each 1 kΩ (long leg toward the higher voltage). Check: red rail +4.5 V, blue rail −4.5 V (black probe on GND).
2. **TL072:** notch = pin 1. Pin 8 → +4.5 V, pin 4 → −4.5 V (double-check: swapped = dead chip). 0.1 µF from pin 8 to GND and from pin 4 to GND, close to the chip. Unused half: pin 5 → GND, pin 6 → pin 7.
3. **Amplifier:** +4.5 V → 100 kΩ → node → 4.7 kΩ → GND; node → pin 3 (Vin ≈ 0.20 V). Pin 2 → 10 kΩ → GND. Pin 2 → 47k + 47k → pin 1 (Rf = 94 kΩ, gain 10.4).
4. **Measure** (Ω first: Rf, Rg, 100k, 4.7k), then with power, black probe on GND:

| Point | Expected | Measured |
|---|---|---|
| + rail / − rail | +4.5 / −4.5 V | |
| Pin 3 (Vin) | ≈ 0.20 V | |
| Pin 2 (V−) | same as pin 3 | |
| Pin 1 (Vout) | ≈ 2.1 V | |
| Gain = pin 1 / pin 3 | ≈ 10.4 | |

5. **Clipping test:** swap 4.7 kΩ → 22 kΩ (Vin ≈ 0.81 V). Vout stops near +3 V; pins 2 and 3 no longer match.

Safety: battery only, nothing on the body. Chip hot → unplug (pins 4/8 swapped). Unplug the battery when done (the divider drains ~4.5 mA). If the TL072 misbehaves at ±4.5 V, try the LM358.
