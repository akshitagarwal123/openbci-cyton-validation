# Build plan: BrainTech-8 EEG board

Goal: our own Cyton-class 8-channel EEG board, designed by us (schematic, PCB, firmware, software), validated against the Cyton.

**Window: Sat 24 Oct 2026 (Day 1) → Thu 31 Dec 2026 (Day 69).** Two board spins fit: rev B (first real board) and rev C (fixes).

## Key dates

| Date | Day | Milestone |
|---|---|---|
| Sun 1 Nov | 9 | Rev B design complete: schematic, placement, routing, self-review |
| **Mon 9 Nov** | 17 | **Rev B ordered** (after outside review) |
| Sun 22 Nov | 30 | Firmware + validation suite proven on an ESP32-S3 dev kit |
| ~Mon 23 Nov | 31 | Rev B boards arrive (fab + assembly + DHL ≈ 2 weeks) |
| Wed 2 Dec | 40 | Rev B brought up: power, SPI, test signal, noise, Wi-Fi |
| **Tue 8 Dec** | 46 | **Rev C ordered** (only if rev B needs fixes) |
| Sun 20 Dec | 58 | Physiology comparison vs Cyton done on rev B |
| ~Mon 21 Dec | 59 | Rev C arrives (Christmas shipping may add days) |
| Thu 31 Dec | 69 | Final validation, write-up, demo, GitHub |

## What we are building (rev B scope, decided 24 Oct)

"From scratch" for this sprint = our own design around the **ADS1299**, the same chip as the Cyton. The discrete front end (own amplifier chain) is a learning project for after 31 Dec (`hardware_learning_plan.md`).

- **8 channels, 1 × ADS1299** (rev A had 16 on 2 chips): half the parts and risk, same as the Cyton, covers our 8 model channels (FC3, FCz, FC4, C3, Cz, C4, CP3, CP4).
- ESP32-S3 (Wi-Fi), built-in LiPo with USB-C charging, LIS3DH accelerometer, 4-layer PCB.
- Speaks the Cyton + Wi-Fi Shield protocol, so BrainFlow (`CYTON_WIFI_BOARD`), the OpenBCI GUI and our scripts work unchanged.
- Electrode header: 2 × 6 pins at 2.54 mm, so the existing OpenBCI electrode leads plug in directly.
- Adopted from the rev A review list (DESIGN_LOG "Proposed rev-A changes"):
  - Low-leakage TVS **TPD4E1B06** (what the Cyton uses; SC-70-6 package, in stock).
  - **47 pF C0G ±2 %** input caps instead of 1 nF (better mains rejection with dry or high-impedance contacts).
  - **2 × 100 kΩ in series with BIAS** (limits current into the body if a part fails).
  - **USB-plugged detection:** firmware stops streaming and turns off BIAS while USB is connected.
- Deferred to later revisions: active-electrode power, shield driver, guard pour, 2 × 13 connector.

## Definition of done: "comparable to Cyton"

Measured with our validation suite, same day, same person, Cyton as reference.

| Test | Cyton (our measurements) | Pass for our board |
|---|---|---|
| Channels / resolution / rate | 8 ch, 24-bit, 250 Hz | same |
| Shorted-input noise | 0.10 µV | ≤ 0.15 µV |
| Internal test signal, gain match | 0.018 % | ≤ 0.1 % |
| Eyes-closed alpha ratio | 2.4–5.7× | ≥ 3× on O1/Oz |
| SSVEP | dry SNR 3.3 / 3.7 | detects 12 and 15 Hz |
| ECG | 100 % beats clean | ≥ 95 % clean |
| Packet loss over 10 min | 0 | < 0.1 % |
| Software | OpenBCI GUI + BrainFlow | BrainFlow + `live_classify.py` unchanged |
| Battery | yes | ≥ 4 h on LiPo |

Stretch: lead-off (electrode impedance) check; live motor-imagery demo on our board.

## Phases

Tracks: **H** hardware (critical path) · **F** firmware/software · **V** validation · **L** learning (just in time).

### Phase 1, Days 1–9 (24 Oct – 1 Nov): design rev B
- H: `hardware/rev_b/circuit.py` (8 ch + adopted changes) → schematic → ERC → BOM with LCSC part numbers. **Done when ERC is clean.**
- H: Parts check against JLCPCB stock (script, re-run before ordering). First check done 24 Oct (below).
- H: Placement with every decoupling cap next to its ADS1299 pin; input network in a straight row at the input pins; analog/digital separation; route; DRC clean.
- H: Self-review checklist (TI layout guide items, rev A step 10 list) + review request posted.
- F: Firmware for 8 channels (Cyton Wi-Fi format) + a "fake ADC" mode that runs on a bare ESP32-S3 dev kit.
- L: ADS1299 datasheet: analog input, reference (SRB), bias drive, power-up, SPI. Book 2.10 (grounds). One KiCad 4-layer video (Phil's Lab).
- **Gate:** design passes ERC + DRC + self-review; reviewer agreed.

### Phase 2, Days 10–17 (2 – 9 Nov): review and order rev B
- H: Outside review → fixes → footprint check against each real part's datasheet → final stock check.
- H: **Order Mon 9 Nov:** 5 PCBs, 2 assembled (JLCPCB), DHL. Header and battery connector hand-soldered if cheaper.
- Buy: matched wet electrodes (see `hardware/ELECTRODES_AND_WIRING.md`), 1S LiPo with protection, bring-up tools.
- L: How PCB fabrication and assembly work (Gerbers, BOM, pick-and-place files).
- **Gate:** order placed.

### Phase 3, Days 18–30 (10 – 22 Nov): while rev B ships
- F: Firmware end to end on the dev kit: Wi-Fi → BrainFlow → `live_classify.py` with fake data; reconnects; battery reading; USB-plugged safety.
- V: Port the Cyton validation scripts; one command runs every test and prints the pass table above.
- V: Motor imagery on the Cyton (C3/C4 placement fix, calibration trials), so the decoder is ready.
- H: Bring-up checklist and a rev C issues list.
- L: Soldering practice on a cheap kit (bodge wires will be needed). Book Ch 7 (hands-on), 2.20–2.23 (AC, capacitors).
- **Gate:** firmware + validation suite proven on the dev kit.

### Phase 4, Days 31–40 (23 Nov – 2 Dec): bring-up rev B
One step at a time, battery or current-limited supply only:
1. Visual check; resistance from every rail to ground (no shorts).
2. Power on; measure 3.3 V, +2.5 V, −2.5 V and the charge-pump ripple.
3. Flash firmware; read the ADS1299 ID register over SPI.
4. Internal test signal on all 8 channels.
5. Shorted-input noise.
6. Wi-Fi into BrainFlow; 10-minute packet-loss test; battery runtime.
- Log every problem and fix (bodge wires allowed).
- **Gate:** noise ≤ 0.15 µV, stable streaming.

### Phase 5, Days 41–46 (3 – 8 Dec): rev C
- If rev B passes everything: rev C is optional polish (or skip it).
- Otherwise: fix every issue in `circuit.py`/layout, review, **order Tue 8 Dec**.

### Phase 6, Days 47–58 (9 – 20 Dec): physiology vs Cyton (on rev B)
- Same session, same electrode positions, Cyton then our board: eyes-closed alpha, ECG, SSVEP.
- Motor imagery: `calibrate.py` and `live_classify.py` on our board.
- **Gate:** pass table filled in.

### Phase 7, Days 59–66 (21 – 28 Dec): rev C bring-up and final validation
- Same bring-up order; full validation suite on rev C.

### Phase 8, Days 67–69 (29 – 31 Dec): write-up and demo
- Design story, bring-up log, comparison table vs Cyton, photos, demo video of live classification. Publish to GitHub.

## Parts check, 24 Oct (JLCPCB stock)

| Part | Use | LCSC # | Stock | Unit price |
|---|---|---|---|---|
| ADS1299IPAGR | 8-ch EEG ADC | C476817 | 636 | $61.93 |
| TPD4E1B06DCKR (TI, SC-70-6) | input TVS | C840093 | 5,382 | $0.43 |
| ESP32-S3-WROOM-1U-N8 | MCU + Wi-Fi | C2980297 | 2,609 | $4.62 |
| LP5907MFX-2.5 | +2.5 V analog LDO | C165132 | 28,283 | $0.30 |
| LM2776DBVR | charge pump (−3.3 V) | C69527 | 12,437 | $0.68 |
| ADP7182AUJZ-2.5-R7 | −2.5 V analog LDO | C462196 | 310 | $5.54 |
| TLV62569DBVR | 3.3 V buck | C141836 | 435,080 | $0.07 |
| MCP73831T-2ACI/OT | LiPo charger | C424093 | 7,410 | $0.70 |
| LIS3DHTR | accelerometer | C15134 | 1,196 | $1.92 |
| 47 pF C0G ±2 % 0603 | input caps | C5375808 | 7,667 | $0.007 |

- The TI TPD4E1B06 in the tiny SOT-5X3 package (rev A's choice) is out of stock: switched to the SC-70-6 version (same chip).
- Still to choose: a 2.2 µH buck inductor rated ≥ 1.5 A (no 1210 part in stock), then map every passive to a JLCPCB part.

## Rough budget (estimate; real quote on ~5 Nov)

| Item | Per spin |
|---|---|
| 5 PCBs (4-layer) + assembly of 2 + parts (2 × ADS1299 ≈ $124) | ≈ $230–300 |
| DHL to India + import duty | ≈ $50–100 |
| **Per spin** | **≈ $280–400 (≈ ₹24–34k)** |

Plus electrodes and tools, once. Two spins ≈ ₹50–70k.

## Top risks

| Risk | Mitigation |
|---|---|
| Layout mistake nobody catches | Outside review before ordering; second spin (rev C) in the plan |
| Part out of stock at order time | Re-run the stock script on order day; alternates listed in the BOM |
| Shipping/customs delays (Christmas) | Order dates fixed (9 Nov, 8 Dec); DHL |
| Noise above target | Bring-up order isolates the cause; Cyton comparison on the same day |
| Firmware not ready when boards arrive | Developed on a dev kit with fake data from Day 2 |

## Progress

- [ ] Phase 1: rev B design complete, reviewer agreed
- [ ] Phase 2: rev B ordered (9 Nov)
- [ ] Phase 3: firmware + validation suite proven on dev kit
- [ ] Phase 4: rev B brought up, noise in spec
- [ ] Phase 5: rev C decided / ordered (8 Dec)
- [ ] Phase 6: physiology comparison done
- [ ] Phase 7: rev C validated
- [ ] Phase 8: written up and demoed
