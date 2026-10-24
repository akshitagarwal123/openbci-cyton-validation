# Build plan: BrainTech-8 EEG board

Tracker (tick tasks, answer weekly assignments): https://claude.ai/artifact/HxVcUf9j7qhkBvV2hgPwsa

Goal: **I design and build** my own Cyton-class 8-channel EEG board (schematic, PCB, firmware), and validate it against the Cyton.
Claude's role: tutor and reviewer. Explains each topic, reviews every step against the datasheets, never hands over a finished design.

**Window: Sat 24 Oct → Thu 31 Dec 2026 (10 weeks).** Starting from a computer-science background, so weeks 1–2 are learning, and there is time for **one board order** (by Sat 28 Nov).

## How every week works

1. **Learn** only what that week's build needs (≈ 1–2 h/day).
2. **Do** the task myself in KiCad / on the bench / in code.
3. **Review** with Claude: explain my choices, Claude checks against datasheet and Cyton schematic.
4. **Deliverable** = proof the week is done. Not done → next week shifts, not skipped.

## Reference designs (learn from, do not copy blindly)

- OpenBCI Cyton schematic (open source, same ADS1299 chip)
- TI ADS1299 datasheet (`BrainTech/hardware_ref/ads1299.pdf`): pin table, Fig. 68 bias drive, layout section
- Our earlier rev A design (`hardware/kicad/`): to compare against after I draw mine

## Weekly plan

| Week | Dates | Learn | Do | Deliverable |
|---|---|---|---|---|
| 1 | 24–31 Oct | Book Ch 2: V, I, R, Ohm, dividers, grounds, capacitors, RC filters. Install KiCad + LTspice; one KiCad beginner tutorial (Phil's Lab). | Order tools + ESP32-S3 DevKit. Simulate an RC filter. Make the tutorial's practice PCB in KiCad (not ordered). | RC sim matches `week01_rc_filter.py`; tutorial board passes DRC |
| 2 | 1–7 Nov | Op-amps and instrumentation amps (Ch 8, Op Amps for Everyone). How an EEG front end works: protection → RC filter → PGA → ADC, reference (SRB), bias/DRL. | Read the Cyton schematic block by block and explain each to Claude. ESP32: blink, SPI basics, Wi-Fi; stream fake data into BrainFlow. | Annotated Cyton block diagram in my own words; BrainFlow receives fake data |
| 3 | 8–14 Nov | ADS1299 datasheet in depth: power pins, VCAP/VREF caps, inputs, SRB1, bias, SPI. Power basics: LDO, buck, charge pump, LiPo charging. | **Draw my schematic in KiCad**: power, ADS1299, 8 inputs, ESP32, connectors. Daily review with Claude. | Schematic passes ERC + Claude review |
| 4 | 15–21 Nov | PCB basics: 4-layer stack-up, ground plane, decoupling placement, analog/digital separation, footprints. | **Lay out the PCB**: place parts (caps next to pins), route, DRC. | Routed board, 0 DRC errors |
| 5 | 22–28 Nov | How JLCPCB fab + assembly works (Gerbers, BOM, pick-and-place). | Outside review (NeuroTechX / OpenBCI forum / r/PrintedCircuitBoard) + Claude review → fixes. Map BOM to LCSC parts, check stock. **Order Sat 28 Nov.** | Order placed (5 PCBs, 2 assembled) |
| 6 | 29 Nov–5 Dec | Soldering + multimeter use (Ch 7). Bring-up method. | Soldering practice kit. Firmware: real ADS1299 driver (registers, RDATAC, Cyton packet format). | Practice kit works; firmware compiles |
| 7 | 6–12 Dec | ADS1299 test modes, noise measurement. | Port the Cyton validation scripts to my board (one command → pass table). Write the bring-up checklist. | Validation suite runs on Cyton data |
| 8 | 13–19 Dec | Debugging hardware (rails, shorts, ripple). | **Bring-up** (boards arrive ~12–14 Dec): rails → SPI ID → test signal → shorted noise → Wi-Fi streaming. | Board streams 8 channels into BrainFlow |
| 9 | 20–26 Dec | — | **Validate vs Cyton**, same day: noise, alpha, ECG, SSVEP. | Pass table filled |
| 10 | 27–31 Dec | — | Fixes (bodge wires), live motor-imagery demo, write-up on GitHub. | Demo video + write-up |

## Definition of done: "comparable to Cyton"

| Test | Cyton (measured) | Pass for my board |
|---|---|---|
| Channels / resolution / rate | 8 ch, 24-bit, 250 Hz | same |
| Shorted-input noise | 0.10 µV | ≤ 0.15 µV |
| Eyes-closed alpha ratio | 2.4–5.7× | ≥ 3× |
| SSVEP | dry SNR 3.3 / 3.7 | detects 12 and 15 Hz |
| ECG | 100 % beats clean | ≥ 95 % clean |
| Packet loss over 10 min | 0 | < 0.1 % |
| Software | BrainFlow | works with `live_classify.py` |

## Board spec (target)

8 channels on 1 × ADS1299 · ESP32-S3 Wi-Fi · LiPo + USB-C charging · Cyton-compatible data (BrainFlow `CYTON_WIFI_BOARD`) · 4-layer PCB · battery-only while worn.

## Parts available at JLCPCB (checked 24 Oct)

| Part | Use | LCSC # | Stock | Price |
|---|---|---|---|---|
| ADS1299IPAGR | EEG ADC | C476817 | 636 | $61.93 |
| TPD4E1B06DCKR | input ESD protection (as Cyton) | C840093 | 5,382 | $0.43 |
| ESP32-S3-WROOM-1U-N8 | MCU + Wi-Fi | C2980297 | 2,609 | $4.62 |
| LP5907MFX-2.5 / LM2776 / ADP7182-2.5 | ±2.5 V analog supplies | C165132 / C69527 / C462196 | in stock | |
| TLV62569 + FNR4020S2R2MT | 3.3 V buck + inductor | C141836 / C167825 | in stock | |
| MCP73831 | LiPo charger | C424093 | 7,410 | $0.70 |

## Shopping list (this week)

- ESP32-S3 DevKitC-1 (Robu.in / Amazon.in)
- Multimeter, temperature-controlled soldering iron, solder, flux, tweezers
- A soldering practice kit
- Budget for the board order (week 5): ≈ ₹25–35k for 5 PCBs with 2 assembled, incl. shipping and duty

## Risks

| Risk | Mitigation |
|---|---|
| Learning takes longer than planned | Weeks 1–2 learning is only what the design needs; Claude explains on demand |
| Design mistake | Claude review at each step + outside review before ordering; bodge wires; rev C in January |
| Order slips past 28 Nov | Boards would arrive too late for December validation; protect weeks 3–5 |

## Progress

- [ ] Week 1: basics, KiCad tutorial, tools ordered
- [ ] Week 2: Cyton schematic understood, fake data in BrainFlow
- [ ] Week 3: my schematic, ERC clean
- [ ] Week 4: my PCB, DRC clean
- [ ] Week 5: reviewed and ordered (28 Nov)
- [ ] Week 6–7: firmware + validation suite ready
- [ ] Week 8: board brought up
- [ ] Week 9: validated vs Cyton
- [ ] Week 10: demo + write-up
