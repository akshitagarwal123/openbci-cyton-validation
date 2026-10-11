# BrainTech-16: 16-channel wireless EEG board (design pack, revision A)

A 16-channel EEG amplifier with a built-in battery, derived from the open-source OpenBCI Cyton + Daisy, redesigned as **one board** with a modern **ESP32-S3** (Wi-Fi + Bluetooth) instead of the discontinued PIC32 + RFduino. It streams in the **OpenBCI Cyton+Daisy Wi-Fi format**, so BrainFlow, the OpenBCI GUI and every script in this repo work unchanged.

> **Status: design specification, not yet a manufacturable PCB.** This pack defines the architecture, every circuit block, the parts list and the firmware structure. The next step is schematic capture and layout in KiCad (see *Next steps*). Values marked **[verify]** must be checked against the TI ADS1299 datasheet and the OpenBCI reference schematic before ordering.

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
| Size | board ≤ 60 × 60 mm, 4 layers; case ≈ 80 × 75 × 28 mm incl. battery |
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
- **Reference and internal caps** (per ADS1299, from the datasheet pin table) **[verify]**: VREFP–VREFN 10 µF; VCAP1 100 µF to AVSS; VCAP2 1 µF; VCAP3 1 µF ∥ 0.1 µF; VCAP4 1 µF. Internal 4.5 V reference enabled.
- **Clock:** chip #1 uses its internal 2.048 MHz oscillator (CLKSEL = 1) and outputs it (CONFIG1.CLK_EN = 1) to chip #2's CLK pin (chip #2 CLKSEL = 0), so both sample in lock-step.
- **SPI:** SCLK, DIN, START, RESET, PWDN shared; **separate chip selects CS1 / CS2** (as OpenBCI does for board/Daisy), DOUT lines joined to the ESP32 MISO (only the selected chip drives it). DRDY of chip #1 to an ESP32 interrupt pin. SPI clock ≤ 4 MHz.
- **Electrode inputs:** each INxP through the **same series resistor and filter network as the Cyton schematic** (current-limiting resistor + small capacitor) **[verify values in reference]**. INxN pins tied together to **SRB2** routing as on Cyton (default "SRB2 on" mode: every channel = electrode − SRB).
- **SRB:** one shared SRB connector pin wired to SRB1/SRB2 of both chips (jumper-selectable like Cyton's SRB1/SRB2 header).
- **BIAS (driven right leg):** BIASOUT of chip #1 drives the BIAS electrode through the Cyton's series resistor; chip #2's BIAS amplifier powered down, its BIASIN tied to chip #1's BIAS network per datasheet daisy guidance **[verify]**.
- **Lead-off detection** kept (impedance checks in the GUI work).

### 3.2 Digital: ESP32-S3 module
- **Module:** ESP32-S3-WROOM-1 (N8R2 or similar), on-board antenna, placed at the **board edge away from the analog section**; keep-out zone under the antenna.
- **Pins:** SPI (SCLK, MOSI, MISO), CS1, CS2, DRDY (interrupt), START, RESET, PWDN; I²C for LIS3DH; status LED (RGB); one button; battery voltage sense (resistor divider to an ADC pin); USB D+/D− to the S3's native USB (programming + development only).
- **Optional:** LIS3DH accelerometer (Cyton has one; useful for motion-artifact rejection), micro-SD slot (offline recording).

### 3.3 Power
| Rail | Part (example, all available from LCSC/JLC) | Notes |
|---|---|---|
| Charging | **MCP73831** (500 mA) or **BQ24075** (with power-path) from USB-C 5 V | BQ24075 lets the board run while charging (bench use only) |
| Battery | 1S LiPo 2000 mAh, **with protection board** (or DW01A + FS8205 on board) | ~60 × 40 × 7 mm |
| +3.3 V (ESP32 + DVDD) | **TLV62569** buck or **AP2112K-3.3** LDO | ESP32 Wi-Fi peaks ~400 mA → buck preferred |
| +2.5 V (AVDD) | **TPS7A2025** / **TPS7A4901** ultra-low-noise LDO from the battery | Analog rail must be quiet |
| −2.5 V (AVSS) | **LM2776 / TPS60403** charge-pump inverter → **TPS7A3001** negative LDO | Charge pump far from ADS1299; heavy filtering |
| Power switch | slide switch in the battery line + soft power via button (optional) | |

**Power budget (estimate):** 2 × ADS1299 ≈ 2 × 40 mW = 80 mW (≈ 25 mA from the battery after regulation losses); ESP32-S3 streaming Wi-Fi ≈ 100–150 mA average; LEDs/misc ≈ 5 mA. **Total ≈ 150–180 mA → 2000 mAh ≈ 11–13 h** (Bluetooth LE mode would roughly double it).

### 3.4 Connectors
- **Electrode harness:** one **2 × 10 shrouded 2.54 mm IDC header** (keyed): 16 inputs + SRB + BIAS + 2 × AGND (shield/drain). One plug for the whole cap.
- **USB-C:** charging; data lines for firmware upload only.
- **Battery:** JST-PH 2-pin.

## 4. PCB guidelines (where noise is won or lost)
1. **4 layers:** top signals, inner 1 solid ground, inner 2 power planes, bottom signals.
2. **Separate analog and digital areas:** ADS1299s and input network on one side; ESP32, buck regulator and charge pump on the other. Single connection point between analog and digital ground under the ADS1299s (as the datasheet recommends).
3. **Input traces:** short, equal, away from the clock, SPI and switching regulators; guard with ground.
4. **Antenna:** ESP32 antenna at the board edge, no copper underneath, case plastic only.
5. **Charge pump / buck:** as far from the analog inputs as possible, with LC filtering on the analog rails.
6. **Copy the Cyton layout** for the analog section where possible: it is proven to reach 0.1 µV.

## 5. Firmware (outline in `firmware/eeg16_esp32/`)
- Configure both ADS1299s exactly as the Cyton firmware does (gain 24, SRB2, BIAS on, 250 Hz), respond to the **same single-character commands** (`b` start, `s` stop, `d` defaults, `x...X` channel settings, `-` `=` test signals, `z...Z` lead-off).
- On each DRDY: read 27 bytes from each chip (status + 8 × 24-bit).
- Packetise in the **Cyton+Daisy format** and serve it like the **OpenBCI Wi-Fi Shield** (its firmware is open source and also ran on an Espressif chip), so BrainFlow `CYTON_DAISY_WIFI` and the OpenBCI GUI connect directly.
- Battery monitoring, status LED (charging / streaming / low battery), auto-off at low voltage.

## 6. Mechanical
- Board stack inside the back-of-head case from `design/` (enlarged to ≈ 80 × 75 × 28 mm): board on 4 nylon standoffs, divider, 2000 mAh LiPo underneath, USB-C and switch on the side, harness connector on top.
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

## 8. Next steps
1. Download the OpenBCI Cyton and Daisy schematics; copy the exact analog values into a **KiCad** schematic of this architecture.
2. Draw the power section and ESP32 section; run ERC.
3. Layout (4 layers), DRC, generate Gerbers + BOM + pick-and-place for an assembly service (JLCPCB / PCBWay / an Indian fab).
4. Order 2–3 prototypes; bring up power rails first, then one ADS1299, then both; then firmware; then validation.
5. Expect one revision (B) to fix noise or layout issues.

## References
- [OpenBCI V3 hardware design files (Cyton schematic and PCB), CC BY-SA 3.0](https://github.com/OpenBCI/V3_Hardware_Design_Files)
- [TI ADS1299 datasheet (daisy-chain, power, pin caps)](https://www.ti.com/lit/ds/symlink/ads1299.pdf)
- [cyton-hardware: an open custom Cyton clone](https://github.com/AbhijithSriram/cyton-hardware)
- [Cerelog ESP-EEG 16-channel (dual ADS1299 + ESP32, BrainFlow/OpenBCI GUI compatible)](https://www.cerelog.com/esp_eeg_16ch.html)
- [TI E2E: multiple ADS1299 in cascade mode](https://e2e.ti.com/support/data-converters-group/data-converters/f/data-converters-forum/501787/multiple-divice-ads1299-in-cascaded-mode/1819596)
