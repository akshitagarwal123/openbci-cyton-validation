# ADS1299: pin table, power supplies and required capacitors

For BrainTech-8: ±2.5 V analog supplies and a 3.3 V digital supply. Every fact below is from TI's datasheet **SBAS499C** (January 2017); page numbers are in brackets. Where a row says **Decide**, the datasheet allows more than one answer and the choice is yours. This is the answer key for week 3, task 1 and assignment Q1: fill in your own table first, then compare.

## Supply limits (p.7, p.8)

| Limit | Datasheet | BrainTech-8 |
|---|---|---|
| AVDD to AVSS | 4.75 to 5.25 V (absolute max 5.5 V) | +2.5 − (−2.5) = 5.0 V |
| DVDD to DGND | 1.8 to 3.6 V (absolute max 3.9 V) | 3.3 V |
| AVDD − DVDD | −2.1 to +3.6 V | 2.5 − 3.3 = −0.8 V |
| AVSS to DGND | absolute max −3 V to +0.2 V | −2.5 V, inside the limit but close to it |

## Table 1: every power pin and the capacitor on it

| Supply | Pins | Capacitor | Page |
|---|---|---|---|
| AVDD | 19, 21, 22, 56 | 1 µF to AVSS | 6 |
| AVDD (charge pump) | 59, with AVSS pin 58 | 1 µF between pin 59 and pin 58 | 6 |
| AVDD1 | 54, with AVSS1 pin 53 | 1 µF to AVSS1 | 6 |
| DVDD | 48, 50 | 1 µF to DGND | 6 |
| VREFP / VREFN | 24 / 25 | at least 10 µF between them (Fig. 78 also shows 0.1 µF in parallel) | 7, 71 |
| VCAP1 | 28 | 100 µF to AVSS | 7, 71 |
| VCAP2 | 30 | 1 µF to AVSS | 7, 71 |
| VCAP3 | 55 | 1 µF ∥ 0.1 µF to AVSS | 7, 71 |
| VCAP4 | 26 | 1 µF to AVSS | 7, 71 |
| +2.5 V rail, at the supply | AVDD / AVDD1 | 1 µF ∥ 0.1 µF to ground (Fig. 78) | 71 |
| −2.5 V rail, at the supply | AVSS / AVSS1 | 1 µF ∥ 0.1 µF to ground (Fig. 78) | 71 |
| +3.3 V rail, at the supply | DVDD | 0.1 µF ∥ 1 µF to ground (Fig. 78) | 71 |

**Things to decide or watch**

1. **The datasheet disagrees with itself on the supply capacitors.** The text of section 11 (p.70) says to bypass each supply with 10 µF and 0.1 µF. The pin table (p.6) and Figure 78 (p.71) show 1 µF, and 1 µF ∥ 0.1 µF at the rails. The Cyton follows the figure. **Decide** which you follow, and write down why.
2. **VCAP1 (p.70).** X7R and X5R ceramics are piezoelectric and add noise when shaken, and noise on VCAP1 goes straight into the reference. The datasheet suggests C0G or tantalum in a system with vibration. The Cyton uses a 100 µF X5R. **Decide.**
3. **Placement (Figure 78 note, p.72).** Put the supply, reference and VCAP capacitors as close to the package as possible, on the same layer, with no vias between the capacitor and the pin.
4. **Star connections (p.70).** Connect AVDD1 to the AVDD pins and AVSS1 to the AVSS pins at one point, because AVDD1 feeds the charge pump and has transients at the clock frequency.

## Table 2: all 64 pins, grouped by job

| Group | Pins | Pin names | Datasheet rule | BrainTech-8 |
|---|---|---|---|---|
| Electrode inputs | 1–16 | IN8N 1, IN8P 2, IN7N 3, IN7P 4, IN6N 5, IN6P 6, IN5N 7, IN5P 8, IN4N 9, IN4P 10, IN3N 11, IN3P 12, IN2N 13, IN2P 14, IN1N 15, IN1P 16 | Unused analog inputs go directly to AVDD (p.6, p.61). A capacitor across each differential pair, C0G is best (p.72). | All 8 are used. TVS, then series resistor, then the input, with your 47 pF C0G. |
| Reference electrode | 17, 18 | SRB1 17, SRB2 18 | Unused: tie to AVSS or float (p.61). SRB1 routes to all N inputs (MISC1 register), SRB2 per channel (CHnSET). | **Decide.** Cyton default is SRB2 on the P side; TI's referential example uses SRB1 on the N side. |
| Bias amplifier | 60–64 | BIASREF 60, BIASINV 61, BIASIN 62, BIASOUT 63, Reserved 64 | Unused bias amp: power it down, float BIASOUT and BIASINV, BIASIN floats or ties to AVSS, BIASREF to AVSS or float (p.61). Pin 64: leave open (p.6). | Used. BIASOUT through R5 ∥ C16 and your 2 × 100 kΩ to the BIAS electrode. BIASINV to a test pin only, as on the Cyton. Set CONFIG3 BIASREF_INT = 1. |
| Analog supply | 19, 21, 22, 56, 59, 54 | AVDD 19, 21, 22, 56 · AVDD 59 (charge pump) · AVDD1 54 | Star-connect AVDD1 to AVDD (p.70). Capacitors: see table 1. | +2.5 V from its own LDO. |
| Analog ground | 20, 23, 32, 57, 58, 53 | AVSS 20, 23, 32, 57 · AVSS 58 (charge pump) · AVSS1 53 | Star-connect AVSS1 to AVSS (p.70). Capacitors: see table 1. | −2.5 V from the inverter + LDO. |
| Digital supply and ground | 48, 50, 33, 49, 51 | DVDD 48, 50 · DGND 33, 49, 51 | 1 µF to DGND (p.6). Keep digital return currents away from the analog return (p.70). | +3.3 V rail; DGND joins the analog ground at the chip (p.72). |
| Reference | 24, 25 | VREFP 24, VREFN 25 | Internal reference: VREFN to AVSS, at least 10 µF from VREFP to VREFN (p.7, p.24). | As the datasheet; enable the buffer in firmware (CONFIG3 bit 7). |
| Internal bypass | 26, 28, 30, 55 | VCAP4 26, VCAP1 28, VCAP2 30, VCAP3 55 | Capacitors: see table 1. | **Decide** the VCAP1 dielectric (p.70 warning). |
| SPI | 34, 39, 40, 43 | DIN 34, CS 39, SCLK 40, DOUT 43 | Digital inputs must not float (p.61). | ESP32-S3 SPI bus. |
| Data ready | 47 | DRDY 47 | Active low. Pull up weakly if unused (p.61). | Interrupt input on the ESP32-S3. |
| Convert / reset / power | 35, 36, 38 | PWDN 35, RESET 36, START 38 | PWDN low powers everything down; RESET low or the RESET command resets (p.35). With the START command, hold the START pin low (p.35). | **Decide** (task 8): RESET and START from MCU pins; PWDN to DVDD or an MCU pin. |
| Clock | 52, 37 | CLKSEL 52, CLK 37 | CLKSEL 1 = internal oscillator, 0 = external clock (Table 6, p.27). Tie two-state pins to DVDD or DGND through ≥10 kΩ (p.6). With CLKSEL = 1 and CLK_EN = 0, CLK is 3-state. | CLKSEL to DVDD through ≥10 kΩ (internal clock); CLK left open. |
| Daisy chain | 41 | DAISY_IN 41 | Not daisy-chaining: tie directly to DGND (p.61). | To DGND. |
| GPIO | 42, 44, 45, 46 | GPIO1 42, GPIO2 44, GPIO3 45, GPIO4 46 | Unused: ≥10 kΩ to DGND (p.6). | ≥10 kΩ to DGND each. |
| Not connected / reserved | 27, 29, 31 | NC 27, 29 · RESV1 31 | NC: leave open. RESV1: connect directly to DGND (p.6). | The Cyton schematic marks RESV1 "CHECK AGAINST DS"; the datasheet answer is DGND. |

All 64 pins are covered once (checked by script). Power-up order and timing: section 11.1 (p.70); the reference and CONFIG3: section 9.3.1.3.4 (p.24-25).

## Questions this answers

- **Q1** (every power pin and its capacitor): table 1.
- **Q4** (CLKSEL floating): CLKSEL is a two-state pin, and the datasheet says never to float unused digital inputs, because of excessive supply leakage current (p.6, p.61). A floating CLKSEL also leaves the clock source undefined (internal or external), so the chip may not run. Tie it through ≥10 kΩ.
