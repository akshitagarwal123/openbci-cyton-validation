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
