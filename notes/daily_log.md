# BrainTech daily log

Short check-ins: what we did, what we learned, what's next. Newest first.

## 2026-10-04 (afternoon)
- Step 2 round 1, dry electrode ECG (13:21): FAIL. 75.8 % beats clean, SNR 5.2 (weak dry contact); ECG shape correct (QRS 80 ms, T 212 ms). Oximeter readings still to add.
- Upgraded live heart-rate dashboard (`live_hr.py`): 8-s average to compare with the oximeter, signal-quality label, per-second CSV log.
- Found the heart rate jumping 80↔160 bpm: the detector was counting the T wave as a second beat (half-length RR intervals). Added `merge_double_detections` to the beat detector → 80 bpm steady, 97 % clean on the same data.
- Dry electrode contact kept drifting toward the limit, then lost contact at 14:00:40.
- After re-seating the dry electrode (14:03), 10 min of clean ECG: 810 beats, 100 % clean, 80.6 bpm (66–105), SNR 46.9, QRS 68 ms, T at 236 ms; dashboard and raw-signal heart rate agree within ~1 bpm per minute.
![Heart-rate session 13:55–14:13](images/ecg_dry_session_oct4.png)
- Notes now carry charts, screenshots and photos. Apple Notes won't display images added by automation (tried inline HTML, attachments and import), so Notes links to each image on GitHub, where the same log renders them inline.
- Published all BrainTech work to the public GitHub repo (`braintech-eeg-classification`): README section on the Cyton hardware work, the validation tracker and daily log with images, all live_inference tools.
- **Next:** rerun the formal dry-electrode ECG test with oximeter readings; then gold electrode.

## 2026-10-04 (early hours)
- Got the internal test signal visible in the GUI: Expert Mode custom command `-`, bandpass off (All circle), notch None, scale Auto → clean ±1,875 µV square wave on all 8 channels.
- Validated it from the GUI recording too (±1,870 µV, 1.024 s, ch1–ch2 gain match 0.018 %).
- Board battery ran flat mid-session (packet loss → disconnect); swapped battery, link clean again (0 dropped).
- Set up screen capture + guarded clicking so Claude can drive the GUI (check front app before every click, verify via screenshot and board log).
- Notes now live in Apple Notes › BrainTech (synced from notes/*.md); tracker rewritten with plain-language explanations of every test.
- Same-spot fingertip test: hum ~1.5 µV, but 10–40 µV slow drift from the dry electrode's skin contact; metal-to-metal external short still to do.
- External short PASSED using a metal key as the shared metal: 0.13 µV noise, 0.14 µV hum, offset −26 µV (same as internal short) → wires/clips/pins add nothing. Confirmed hands-free 02:27:53–02:28:12 (0.12 µV noise, 0.10 µV hum, offset −25 µV). Lesson: dry comb pins need pressure for solid contact. **Step 1 complete.**
![External short on a metal key](images/extshort_key_setup.jpg)
![Test signal in the GUI](images/gui_square_wave.png)
- **Next:** Step 2 ECG + pulse oximeter.

## 2026-10-03
- Planned the formal validation (3 steps: board → independent device → cause/effect physiology); built `validate_board.py` and `test_signal_check.py`.
- Step 1 passed: integrity, shorted inputs (0.10 µV noise), internal test signal on all 8 channels.
- Learned the GUI quirks (Send + restart stream; "Test" mode doesn't drive the generator).
- Built `eeg_compare.py` + electrode placement diagram for dry vs gold EEG (forehead Fp1/Fp2 option since no paste).

## 2026-10-02
- ECG from wrists: clear heartbeat once electrode and SRB were on opposite wrists (80 bpm).
- Built `heart_monitor.py`, `live_hr.py` (live window), `breathing_hr.py` (guided breathing protocol), `compare_electrodes.py`.
- Breathing run: paced breathing swings heart rate ~28 bpm; breath-holds give a brief dip.
- Dry vs gold ECG: dry cleaner without paste (SNR 42.6 vs 18.8).

## 2026-10-01
- First look at live Cyton data: floating inputs, railing, 50 Hz pickup from long leads, notch/bandpass effects.
- Built `gui_monitor.py` / `noise_breakdown.py` (LSL) for live filter + noise analysis.
