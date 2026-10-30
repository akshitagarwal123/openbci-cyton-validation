# Build progress: BrainTech-8

Live tracker (tick tasks, answer assignments): https://claude.ai/artifact/HxVcUf9j7qhkBvV2hgPwsa
This file is a snapshot of the tracker, updated by Claude after each review. Source of the page: `build_tracker.html`.

_Last synced: 2026-10-31: 14 of 15 week 1 tasks done

## Parts on hand (24 Oct)

ESP32 DevKit V1 (38-pin) · 830-point breadboard · jumper wires · DT830D multimeter · resistor kit (600 pc) · capacitor kit (300 pc) · 5× LM358 · 5× TL072 · AD8232 ECG module + 3-lead cable · 100 ECG electrode pads · Soldron 25 W iron · 63/37 solder 0.8 mm · wick + flux · 9 V battery + snap · 18650 2200 mAh cell · 2000 mAh LiPo · Li-ion connector

Still needed: TP4056 charger module **with protection** (never charge the 18650/LiPo without one), tweezers, through-hole practice kit. Later (week 6): a temperature-controlled iron for SMD bodge wires.

## Week 1: Electronics basics and KiCad setup (2026-10-24 → 2026-10-31)

Understand voltage, current, resistance, grounds and RC filters; get your tools installed and ordered.

- [x] Read Ch 1, Introduction (p1–4)
- [x] Read 2.1–2.3 current and voltage (p5–18)
- [x] Read 2.5 resistance and 2.7 heat and power (p23–34)
- [x] Read 2.10 grounds (p40–48)
- [x] Read 2.11–2.17 Ohm's law, dividers, Kirchhoff (p49–74)
- [x] Read 2.20–2.22 AC, frequency, RMS, mains power (p80–94)
- [x] Read 2.23 capacitors, RC time constant, reactance (p94–113)
- [x] Install KiCad and LTspice
- [x] Run week01_rc_filter.py with three different R and C pairs
- [x] Simulate an RC low-pass in LTspice and compare its cutoff with the script
- [ ] Finish one KiCad beginner tutorial (Phil's Lab) to a practice board with 0 DRC errors
- [x] Get an ESP32 dev board (have: ESP32 DevKit V1)
- [x] Get multimeter, soldering iron, solder, wick and flux (have)
- [x] Buy what is still missing: TP4056 charger module with protection (for the 18650/LiPo), tweezers, a through-hole soldering practice kit
- [x] Breadboard an RC low-pass from your kits (10 kΩ + 0.47 µF ≈ 34 Hz) and check R and C values with the multimeter

**Assignment** (answers in the tracker; review: _not yet_)

1. EEG is measured as a voltage between two points. Why not at one point, and what job does the reference (SRB) do?
2. Skin–electrode resistance is 50 kΩ and 1 nA flows through it. What voltage appears, and how does it compare with a 10 µV alpha wave?
3. When the SRB ear clip came off, all your channels looked identical. Explain why.
4. Design an RC low-pass with a cutoff near 40 Hz using a 10 kΩ resistor. Which capacitor? How much of the 50 Hz mains signal still passes?
5. What does 'floating' mean, and why is a battery-powered, floating EEG board safer?
6. Your LTspice result: what cutoff did you measure, and how far was it from the calculated value?

## Week 2: Op-amps, the Cyton, and ESP32 basics (2026-11-01 → 2026-11-07)

Understand how an EEG front end works by reading the Cyton schematic, and get the ESP32 sending data to BrainFlow.

- [ ] Book Ch 8: op-amp golden rules, inverting and non-inverting amplifiers
- [ ] Book Ch 8: instrumentation amplifiers and CMRR
- [ ] Op Amps for Everyone: skim the basics and noise chapters
- [ ] Simulate a non-inverting amplifier with gain 10 in LTspice
- [ ] Read the ADS1299 datasheet overview and block diagram
- [ ] Mark the Cyton schematic's blocks: protection, ADS1299, power, MCU, radio
- [ ] Explain every Cyton block to Claude in a review session
- [ ] ESP32: set up Arduino or PlatformIO and blink an LED
- [ ] ESP32: join Wi-Fi and send fake 8-channel data
- [ ] See your fake data arrive in BrainFlow
- [ ] Breadboard a TL072 non-inverting amplifier, gain 10, on the 9 V battery; measure input and output DC with the multimeter
- [ ] AD8232 + ESP32: read your ECG with the ESP32 ADC and plot it in Python (laptop on battery, not charging)

**Assignment** (answers in the tracker; review: _not yet_)

1. State the op-amp golden rules. What is the gain of a non-inverting amplifier with Rf = 90 kΩ and Rg = 10 kΩ?
2. What is the difference between common-mode and differential signals? Why does EEG need a high CMRR? Use 50 Hz mains as your example.
3. What does a PGA do, and why does the Cyton run the ADS1299 at gain 24?
4. Why is there a resistor and a small capacitor between each electrode and the ADS1299 input?
5. What does the bias (driven right leg) electrode do?
6. Explain SPI in four lines (SCLK, MOSI, MISO, CS), and say what the ADS1299's DRDY pin tells the MCU.

## Week 3: Draw your schematic (2026-11-08 → 2026-11-14)

Your own complete schematic in KiCad, checked pin by pin against the ADS1299 datasheet.

- [ ] ADS1299 datasheet: pin table, power supplies, required capacitors
- [ ] ADS1299 datasheet: bias drive (Fig. 68), SRB1, input multiplexer
- [ ] Learn power basics: LDO vs buck vs charge pump, LiPo charging
- [ ] Create the KiCad project and set up symbol and footprint libraries
- [ ] Draw power: USB-C, charger, battery, switch, 3.3 V buck, ±2.5 V analog
- [ ] Draw the ADS1299 with every VCAP, VREF and decoupling capacitor
- [ ] Draw 8 input channels plus SRB and BIAS with protection (TVS, 2.2 kΩ, 47 pF)
- [ ] Draw the ESP32-S3: SPI, DRDY, START, RESET, PWDN, boot and reset buttons, LEDs
- [ ] Add battery sense, USB-plugged detection and test points
- [ ] Run ERC and fix every error
- [ ] Review session with Claude: every pin against the datasheet
- [ ] Compare with the Cyton and rev A; write down each difference and why

**Assignment** (answers in the tracker; review: _not yet_)

1. List every ADS1299 power pin and the capacitor on it, with the datasheet section that says so.
2. Why do AVDD and AVSS (±2.5 V) come from LDOs instead of straight from the buck converter?
3. Why put 2 × 100 kΩ in series with the BIAS electrode?
4. What happens if the CLKSEL pin is left floating?
5. Trace the signal path from an electrode to Wi-Fi in one line, naming every part it passes through.

## Week 4: Lay out your PCB (2026-11-15 → 2026-11-21)

A routed 4-layer board with 0 DRC errors, decoupling caps at their pins and short analog inputs.

- [ ] Learn: 4-layer stack-up, ground planes, return currents (Phil's Lab)
- [ ] Assign footprints and check each against its part datasheet
- [ ] Set the board outline, layer stack and JLCPCB design rules
- [ ] Place the ADS1299 and its decoupling caps within 1–2 mm of their pins
- [ ] Place the input protection in a straight row next to the input pins
- [ ] Place the buck and charge pump far from the electrode inputs
- [ ] Place the ESP32 at the board edge with its antenna keep-out
- [ ] Route the analog inputs first: short and similar in length
- [ ] Route SPI and power; keep the inner ground plane solid
- [ ] Reach 0 DRC errors and check the 3D view
- [ ] Review session with Claude

**Assignment** (answers in the tracker; review: _not yet_)

1. Why use a solid ground plane, and what happens when a trace cuts through it?
2. Why must decoupling capacitors sit right next to their pins?
3. Why keep the buck converter away from the electrode inputs?
4. What is a via, and when can one cause problems?
5. Describe each layer of your 4-layer stack-up and what it carries.

## Week 5: Review, fix and order (2026-11-22 → 2026-11-28) — **Order by Sat 28 Nov**

Outside review, fixes, manufacturing files, and the order placed with JLCPCB.

- [ ] Post the design for outside review (NeuroTechX, OpenBCI forum, r/PrintedCircuitBoard)
- [ ] Fix the review findings
- [ ] Generate Gerbers, drill files, BOM and pick-and-place (CPL)
- [ ] Map every BOM line to an LCSC part number and check stock
- [ ] Upload to JLCPCB and check the assembly preview (rotation, pin 1)
- [ ] Get the quote: 5 PCBs, 2 assembled
- [ ] Place the order (by Sat 28 Nov)
- [ ] Order electrodes, gel and a protected 1S LiPo

**Assignment** (answers in the tracker; review: _not yet_)

1. What are Gerber, BOM and CPL files, and who uses each?
2. Why check component rotation in JLCPCB's assembly preview?
3. What is the difference between a Basic and an Extended part at JLCPCB, and why does it matter?
4. Name the three riskiest things on your board and how you would detect each one at bring-up.

## Week 6: Soldering practice and ADS1299 firmware (2026-11-29 → 2026-12-05)

Hands ready for bodge wires; firmware ready to talk to the real ADS1299.

- [ ] Book Ch 7: soldering and multimeter use
- [ ] Build the soldering practice kit
- [ ] Practise soldering an 0603 part and a bodge wire on scrap board
- [ ] Firmware: ADS1299 register map and power-up sequence
- [ ] Firmware: SPI read of the ID register
- [ ] Firmware: RDATAC loop and 24-bit to µV conversion
- [ ] Firmware: Cyton packet format over Wi-Fi into BrainFlow

**Assignment** (answers in the tracker; review: _not yet_)

1. Write the formula to convert a raw 24-bit ADS1299 value to µV at gain 24 with Vref = 4.5 V.
2. What is a cold solder joint, and how do you spot one?
3. Describe the ADS1299 power-up and reset sequence.
4. Describe the Cyton 33-byte packet: what is in each part?

## Week 7: Validation suite and bring-up prep (2026-12-06 → 2026-12-12)

One command that tests your board and prints the pass table; a bench ready for the boards.

- [ ] Port the Cyton validation scripts to your board
- [ ] Run the suite on recorded Cyton data
- [ ] Write the bring-up checklist: rails, SPI, test signal, noise, Wi-Fi
- [ ] Prepare the bench: battery or current-limited supply, multimeter, cables
- [ ] Track the shipment

**Assignment** (answers in the tracker; review: _not yet_)

1. What is shorted-input noise, how do you measure it, and what number passes?
2. What does the internal test signal prove?
3. Why check the power rails before running any firmware?
4. Why measure packet loss over 10 minutes instead of 10 seconds?

## Week 8: Bring up the board (2026-12-13 → 2026-12-19)

Your board streams 8 channels into BrainFlow with noise in spec.

- [ ] Inspect the board under a magnifier
- [ ] Measure resistance from every rail to GND (no shorts)
- [ ] Power on from battery or a current-limited supply; measure 3.3 V, +2.5 V, −2.5 V
- [ ] Flash the firmware over USB
- [ ] Read the ADS1299 ID register (expect 0x3E)
- [ ] Internal test signal on all 8 channels
- [ ] Shorted-input noise ≤ 0.15 µV
- [ ] Wi-Fi streaming into BrainFlow; 10-minute packet-loss test
- [ ] Log every problem and its fix

**Assignment** (answers in the tracker; review: _not yet_)

1. A rail reads 0 V. Give three possible causes and how you would check each.
2. The ID register reads 0x00 or 0xFF. What do you check?
3. Noise is 2 µV with a big 50 Hz peak. What are your next steps?

## Week 9: Validate against the Cyton (2026-12-20 → 2026-12-26)

The 'comparable to Cyton' pass table filled in with real measurements.

- [ ] Eyes-closed alpha: Cyton, then your board, same positions
- [ ] ECG test
- [ ] SSVEP at 12 and 15 Hz
- [ ] Battery runtime ≥ 4 h
- [ ] Fill in the pass table

**Assignment** (answers in the tracker; review: _not yet_)

1. Your alpha ratio is 2× on your board but 4× on the Cyton. What could explain the difference?
2. Go through your pass table: what passed, what failed, and why?

## Week 10: Demo and write-up (2026-12-27 → 2026-12-31)

A live demo and a public write-up of your board.

- [ ] Fix remaining issues with bodge wires
- [ ] Motor-imagery calibration and live_classify.py on your board
- [ ] Record the demo video
- [ ] Write the design story and the Cyton comparison table on GitHub
- [ ] List the rev C changes for January

**Assignment** (answers in the tracker; review: _not yet_)

1. What would you change in rev C, and why?
2. Write how you would explain your board to an interviewer in two minutes.
