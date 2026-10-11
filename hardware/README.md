# BrainTech-16: 16-channel wireless EEG board (design pack, revision A)

A 16-channel EEG amplifier with a built-in battery, derived from the open-source OpenBCI Cyton + Daisy, redesigned as **one board** with a modern **ESP32-S3** (Wi-Fi + Bluetooth) instead of the discontinued PIC32 + RFduino. It streams in the **OpenBCI Cyton+Daisy Wi-Fi format**, so BrainFlow, the OpenBCI GUI and every script in this repo work unchanged.

> **Status (rev A, 12 Oct 2026):** KiCad schematic (ERC clean except one documented false positive), 4-layer 80 × 76 mm PCB **fully routed with 0 copper DRC errors**, Gerbers, drill, pick-and-place, BOM and STEP model generated, firmware compiles for the ESP32-S3. Not yet reviewed by a second engineer, not yet built. See [DESIGN_LOG.md](DESIGN_LOG.md) for every step and decision, and *Before ordering* below.

<img src="images/pcb_3d_iso.png" width="70%">

**Licence:** based on the [OpenBCI V3 hardware design files](https://github.com/OpenBCI/V3_Hardware_Design_Files), released under **Creative Commons BY-SA 3.0**. This design is therefore also CC BY-SA 3.0 and must credit OpenBCI.

---

## 1. Requirements

| Requirement | Target |
|---|---|
| Channels | 16 EEG + SRB (reference) + BIAS (driven ground) |
| Resolution / gain | 24-bit, gain 24 (same as Cyton), ±187.5 mV input range |
| Noise floor (inputs shorted) | ≤ 0.15 µV RMS (Cyton measures 0.09–0.14; ours 0.10) |
| Sample rate | 250 Hz on all 16 channels (500 Hz possible over Wi-Fi) |
| Wireless | Wi-Fi (primary, OpenBCI Wi-Fi protocol) and Bluetooth LE (later) |
| Battery | built-in 1S LiPo, ≥ 8 h streaming, USB-C charging |
| Safety | battery-powered while worn; never connected to mains-powered equipment while on the head |
| Size | board 80 × 76 mm, 4 layers; case ≈ 88 × 84 × 30 mm incl. battery |
| Compatibility | BrainFlow `CYTON_DAISY_WIFI`, OpenBCI GUI, this repo's tools |

## 2. Block diagram

```
 16 electrodes ─┐                                   ┌──────────────┐
 SRB (earlobe) ─┤   ┌──────────────┐   SPI (shared   │              │   Wi-Fi  ─▶ laptop
 BIAS ──────────┤   │ ADS1299 #1   │◀─ SCLK, DIN,    │  ESP32-S3    │   (BrainFlow /
                ├──▶│ ch 1-8 (master)  START, RESET) │  module      │    OpenBCI GUI)
  20-pin        │   │ CLK out ─────┼──┐             │              │
  harness  ─────┤   └──────┬───────┘  │ 2.048 MHz   │  DRDY ◀──────┤
  connector     │   ┌──────┴───────┐  │             │  CS1, CS2 ──▶│
                └──▶│ ADS1299 #2   │◀─┘             │  LED, button │
                    │ ch 9-16      │                │  LIS3DH (opt)│
                    └──────────────┘                └──────┬───────┘
                         ▲ ±2.5 V analog (ultra-low-noise)  │ 3.3 V digital
             ┌───────────┴──────────────────────────────────┴──────┐
             │ Power: USB-C ─▶ charger ─▶ 1S LiPo (protected) ─▶     │
             │   • +2.5 V LDO (AVDD)   • −2.5 V (charge pump + LDO)   │
             │   • 3.3 V regulator (DVDD + ESP32)                     │
             └──────────────────────────────────────────────────────┘
```

## 3. Circuit blocks

### 3.1 Analog front end: 2 × TI ADS1299 (copy from Cyton + Daisy)
The Cyton (8 ch) and Daisy (8 ch) each use one ADS1299 at gain 24 with a bipolar ±2.5 V supply. We place **both on one board**:

- **Supplies:** AVDD = +2.5 V, AVSS = −2.5 V, DVDD = 3.3 V (as Cyton). Decouple every supply pin with 0.1 µF + 1 µF close to the pin.
- **Reference and internal caps** (datasheet pin table, identical on Cyton): VREFP–VREFN 10 µF ∥ 0.1 µF; VCAP1 100 µF to AVSS; VCAP2 1 µF; VCAP3 1 µF ∥ 0.1 µF; VCAP4 1 µF. RESV1 to DGND, DAISY_IN to DGND, GPIO1–4 to DGND through 10 kΩ, CLKSEL through 10 kΩ.
- **Clock:** chip #1 uses its internal 2.048 MHz oscillator (CLKSEL = 1) and outputs it (CONFIG1.CLK_EN = 1) to chip #2's CLK pin (chip #2 CLKSEL = 0), so both sample in lock-step.
- **SPI:** SCLK, DIN, START, RESET, PWDN shared; **separate chip selects CS1 / CS2** (as OpenBCI does for board/Daisy), DOUT lines joined to the ESP32 MISO (only the selected chip drives it). DRDY of chip #1 to an ESP32 interrupt pin. SPI clock ≤ 4 MHz.
- **Electrode inputs (as Cyton):** bidirectional TVS at the connector, **2.2 kΩ** series resistor, **1 nF** to ground at the ADC pin. Electrodes on **INxP**; the reference **SRB** goes to **SRB1 and every INxN** (TI's referential montage, datasheet Fig. 73), so every channel = electrode − SRB with no SRB2 ambiguity. Firmware: CHnSET = 0x60, MISC1 = 0x20.
- **BIAS (driven right leg):** chip #1's bias amplifier with **1 MΩ ∥ 1.5 nF** between BIASINV and BIASOUT (datasheet Fig. 68), BIASIN = BIASOUT, BIASREF to AVSS (internal reference); BIASOUT → 2.2 kΩ → TVS → BIAS electrode. Chip #2's bias amplifier is powered down: BIASOUT/BIASINV floating, BIASIN and BIASREF to AVSS (datasheet 10.1.1).
- **Lead-off detection** kept (impedance checks in the GUI work).

### 3.2 Digital: ESP32-S3 module
- **Module:** **ESP32-S3-WROOM-1U-N8** (u.FL connector + small stick-on antenna inside the case). The PCB-antenna version needs a 48 × 21 mm copper keep-out, which does not fit an 80 mm board full of electrode wiring.
- **Pins:** SPI (SCLK, MOSI, MISO), CS1, CS2, DRDY (interrupt), START, RESET, PWDN; I²C for LIS3DH; status LED (RGB); one button; battery voltage sense (resistor divider to an ADC pin); USB D+/D− to the S3's native USB (programming + development only).
- **Optional:** LIS3DH accelerometer (Cyton has one; useful for motion-artifact rejection), micro-SD slot (offline recording).

### 3.3 Power
| Rail | Part (example, all available from LCSC/JLC) | Notes |
|---|---|---|
| Charging | **MCP73831** (500 mA) or **BQ24075** (with power-path) from USB-C 5 V | BQ24075 lets the board run while charging (bench use only) |
| Battery | 1S LiPo 2000 mAh, **with protection board** (or DW01A + FS8205 on board) | ~60 × 40 × 7 mm |
| +3.3 V (ESP32 + DVDD) | **TLV62569** buck, 100 k / 22.1 k feedback → 3.31 V | ESP32 Wi-Fi peaks ~400 mA → buck |
| +2.5 V (AVDD) | **LP5907-2.5** (6.5 µV RMS noise) from 3.3 V | same topology as Cyton (TLV70025 there) |
| −2.5 V (AVSS) | **LM2776** charge-pump inverter (−3.3 V) → **ADP7182-2.5** negative LDO | same topology as Cyton (LM2664 + TPS72325) |
| Power switch | slide switch in the battery line + soft power via button (optional) | |

**Power budget (estimate):** 2 × ADS1299 ≈ 2 × 40 mW = 80 mW (≈ 25 mA from the battery after regulation losses); ESP32-S3 streaming Wi-Fi ≈ 100–150 mA average; LEDs/misc ≈ 5 mA. **Total ≈ 150–180 mA → 2000 mAh ≈ 11–13 h** (Bluetooth LE mode would roughly double it).

### 3.4 Connectors
- **Electrode harness:** one **2 × 10 shrouded 2.54 mm IDC header** (keyed): 16 inputs + SRB + BIAS + 2 × AGND (shield/drain). One plug for the whole cap.
- **USB-C:** charging; data lines for firmware upload only.
- **Battery:** JST-PH 2-pin.

## 4. PCB guidelines (where noise is won or lost)
1. **4 layers:** top signals, inner 1 solid ground plane (no tracks), inner 2 signals + power, bottom signals.
2. **Separate analog and digital areas** by placement over one continuous ground plane: ADS1299s and input network on the left, ESP32 and buck regulator on the right. Every ground pad has its own via to the plane.
3. **Input traces:** short, equal, away from the clock, SPI and switching regulators; guard with ground.
4. **Antenna:** WROOM-1U with an external u.FL antenna inside the plastic case.
5. **Charge pump / buck:** as far from the analog inputs as possible, with LC filtering on the analog rails.
6. **Copy the Cyton layout** for the analog section where possible: it is proven to reach 0.1 µV.

## 5. Firmware (`firmware/eeg16_esp32/`, compiles for ESP32-S3)
- Configure both ADS1299s like the Cyton firmware (gain 24, BIAS on, 250 Hz) but with the SRB1 referential montage above, respond to the **same single-character commands** (`b` start, `s` stop, `d` defaults, `x...X` channel settings, `-` `=` test signals, `z...Z` lead-off).
- On each DRDY: read 27 bytes from each chip (status + 8 × 24-bit).
- Packetise in the **Cyton+Daisy format** and serve it like the **OpenBCI Wi-Fi Shield** (its firmware is open source and also ran on an Espressif chip), so BrainFlow `CYTON_DAISY_WIFI` and the OpenBCI GUI connect directly.
- Battery monitoring, status LED (charging / streaming / low battery), auto-off at low voltage.

## 6. Mechanical
- Board stack inside the back-of-head case from `design/` (enlarged to ≈ 88 × 84 × 30 mm): board on 4 nylon standoffs, divider, 2000 mAh LiPo underneath, USB-C and switch on the side, harness connector on top.
- Cap: stretchy cap or printed frame with 16 holders (layout below), harness sewn along the seams.

### Suggested 16-channel layout (motor-imagery focused)
| Row | Positions |
|---|---|
| Frontal | F3, Fz, F4 |
| Fronto-central | FC3, FCz, FC4 |
| **Central (motor)** | **C3, Cz, C4** |
| Centro-parietal | CP3, CPz, CP4 |
| Parietal | P3, Pz, P4 |
| Occipital | Oz |
| Reference / bias | SRB on left earlobe or mastoid, BIAS on right earlobe or mastoid |

## 7. Validation plan
Run this repo's battery on the new board: `integrity`, `hardware` (shorted inputs ≤ 0.15 µV, internal test signal ±1,875 µV within 2 %), external short, ECG vs oximeter, blinks, jaw, alpha, SSVEP, then the motor test. Pass = same criteria as the Cyton.

## 8. Files
| File | What it is |
|---|---|
| [DESIGN_LOG.md](DESIGN_LOG.md) | every step, decision, problem and fix, in order |
| `kicad/build.sh` | one command rebuilds everything below (`--pcb` also re-places and re-routes) |
| `kicad/circuit.py` | the circuit, one place: every part, value, footprint, pin → net, with the source of each value |
| `kicad/gen_schematic.py` | generates `braintech16.kicad_sch` from circuit.py (net labels on every pin) |
| `kicad/set_rules.py` | fab design rules + net classes into `braintech16.kicad_pro` |
| `kicad/gen_pcb.py` | generates `braintech16.kicad_pcb`: 80 × 76 mm, 4 layers, placement by zones, GND plane on In1 |
| `kicad/gnd_vias.py`, `route_prep.py`, `import_ses.py` | ground vias, Freerouting export, import of the routed result |
| `kicad/braintech16_schematic.pdf` | printable schematic (A1) |
| `kicad/braintech16_bom.csv`, `kicad/braintech16.net` | full BOM and netlist exported by KiCad |
| `kicad/erc.rpt`, `kicad/drc.rpt` | rule-check reports |
| `kicad/fab/` | **ordering files:** Gerbers + drill zip, pick-and-place, BOM, STEP 3D model |
| `images/` | 3D renders and copper-layer plots |
| `BOM.csv` | purchasing-level parts list with notes |
| `firmware/eeg16_esp32/` | ESP32-S3 firmware (compiles; Wi-Fi Shield protocol for BrainFlow) |

## 9. Before ordering (must do)
1. **Review by an experienced PCB designer**, especially analog routing and grounding (see DESIGN_LOG).
2. **Clean up the analog section by hand** where the review asks: decoupling caps right at the ADS1299 pins, short and similar input traces, charge pump and buck loops tight. The routing is complete and DRC-clean, but it is autorouted.
3. Check every footprint against the part you actually buy (USB-C, slide switch, inductor, TVS package).
4. Check ADS1299 stock and price; order 2–3 prototypes with assembly.

## 10. Next steps
1. ~~KiCad schematic with the Cyton/datasheet values~~ done (rev A).
2. ~~Power and ESP32 sections, ERC~~ done.
3. ~~Placement, routing, DRC, Gerbers + BOM + pick-and-place~~ done (rev A). **Remaining:** human review and clean-up of the analog layout, then re-run `build.sh` and upload `kicad/fab/` to an assembly service (JLCPCB / PCBWay / an Indian fab).
4. Order 2–3 prototypes; bring up power rails first, then one ADS1299, then both; then firmware; then validation (section 7).
5. Expect one revision (B) to fix noise or layout issues.

## References
- [OpenBCI V3 hardware design files (Cyton schematic and PCB), CC BY-SA 3.0](https://github.com/OpenBCI/V3_Hardware_Design_Files)
- [TI ADS1299 datasheet (daisy-chain, power, pin caps)](https://www.ti.com/lit/ds/symlink/ads1299.pdf)
- [cyton-hardware: an open custom Cyton clone](https://github.com/AbhijithSriram/cyton-hardware)
- [Cerelog ESP-EEG 16-channel (dual ADS1299 + ESP32, BrainFlow/OpenBCI GUI compatible)](https://www.cerelog.com/esp_eeg_16ch.html)
- [TI E2E: multiple ADS1299 in cascade mode](https://e2e.ti.com/support/data-converters-group/data-converters/f/data-converters-forum/501787/multiple-divice-ads1299-in-cascaded-mode/1819596)
