# Hardware learning plan — build our own BCI from scratch

> **Paused 24 Oct 2026:** the build sprint (`build_plan.md`, deadline 31 Dec) takes priority. Reading continues just in time; the discrete front-end track resumes after 31 Dec.

Goal: learn enough analog electronics to design, build and debug our own EEG front end, then scale it into the wheelchair BCI. Every build is checked against the Cyton on the same test.

**Gate rule:** move to the next phase only when the current build works and has been compared with the Cyton.

**Safety rule:** anything touching the head runs on battery only, never on a laptop connected to its charger without isolation.

## Roadmap

| Phase | Learn | Build | Pass when |
|---|---|---|---|
| Weeks 1–3 | Electronics basics: Ohm, RC, op-amps | Breadboard filters | Measured cutoff/gain within 10 % of the calculation |
| Weeks 4–6 | Biosignals: ECG, EMG, sampling | AD8232 + ESP32, own firmware and viewer | Clean heartbeat in our own software |
| Weeks 7–10 | Bioamplifiers: INA, right-leg drive, noise | 1-channel EEG on breadboard | Noise < 1 µV RMS, eyes-closed alpha ≥ 3× |
| Weeks 11–14 | PCB design: KiCad, grounding | First 2-layer PCB, one channel | Same numbers as the breadboard version |
| Months 4–6 | Scaling: discrete vs AFE chip (ADS1299, Intan) | 4–8 channel board with lead-off and isolation | Matches Cyton on noise, alpha, SSVEP |
| Month 6+ | BCI decoding: motor imagery, EEGNet | Wheelchair BCI, simulation first | Safe stop, low false positives |

Decoder work runs in parallel on the Cyton the whole time.

## Phase 1 (weeks 1–3): Practical Electronics for Inventors

Read only: Ch 2 (theory, RC, filters), Ch 8 (op-amps), Ch 9 (filters), first half of Ch 7 (hands-on, safety). Loop for every circuit: **calculate in Python → simulate in LTspice → build → measure → compare**.

### Week 1 — voltage, current, RC
(Book page numbers, 4th edition.)
- Day 1: Ch 1 (p1–4); 2.1–2.3 current, voltage (p5–18); 2.5 resistance (p23–28); 2.7 heat and power (p31–34). Skip 2.4, 2.6, 2.8, 2.9. Install LTspice.
- Day 2: 2.10 grounds (p40–48, read carefully); 2.11–2.12 circuits, Ohm's law, series/parallel, dividers (p49–62); 2.13–2.17 sources, measuring, open/short, Kirchhoff (p62–74). Exercise: divider calc + LTspice sim.
- Day 3: 2.20–2.21 AC, frequency, phase, RMS (p80–92); 2.22 mains power (p92–94, the source of 50 Hz noise). Skip 2.18–2.19 for now.
- Day 4: 2.23 capacitors (p94–113): focus on 2.23.8 RC time constant, 2.23.12–2.23.14 reactance and capacitive divider. Then the RC filter sections later in Ch 2. Run `hw_learning/week01_rc_filter.py`.
- Day 5: Ch 7 (first half) — breadboards, multimeter, safety.
- Weekend: build the RC low-pass on a breadboard, measure, compare with the script.

### Week 2 — op-amps
- Ch 8: golden rules, non-inverting and inverting amps, gain.
- Build: non-inverting amp, gain 10 (TL072 or OPA2333) on a 9 V battery split supply.
- Ch 8: instrumentation amps. Why EEG needs CMRR.

### Week 3 — active filters
- Ch 9: active low-pass/high-pass (Sallen-Key), notch.
- Build: 0.5 Hz high-pass → gain 10 → 40 Hz low-pass chain (a mini EEG chain). Feed it the Cyton test signal or a phone tone generator.
- Week 3 pass: chain's measured response matches the simulation.

## Shopping list (≈ ₹15–25k)

- Multimeter
- Temperature-controlled soldering iron (Pinecil or similar), solder, flux, tweezers
- 2 breadboards, jumper wires, resistor kit, capacitor kit
- Op-amps: TL072, OPA2333; instrumentation amp: INA333 or AD620 breakout
- AD8232 ECG module (for weeks 4–6)
- Analog Discovery 3 (preferred) or a cheap USB oscilloscope
- 9 V / AA battery packs

## Books by phase

- Weeks 1–3: Practical Electronics for Inventors (Ch 2, 7, 8, 9)
- Weeks 4–10: Op Amps for Everyone (free TI PDF), Prutchi & Norris
- Weeks 11–14: Phil's Lab (YouTube)
- Month 6+: Wolpaw & Wolpaw, Mike X Cohen

## Progress

- [ ] Week 1 — RC basics
- [ ] Week 2 — op-amps
- [ ] Week 3 — active filter chain
