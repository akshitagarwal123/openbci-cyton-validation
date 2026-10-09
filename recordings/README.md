# Raw recordings

The exact OpenBCI GUI data behind each test, cut from the full GUI recordings to just the test window and gzip-compressed. Format is the GUI's own `OpenBCI-RAW` text file (header lines start with `%`). Values are in µV, 250 samples per second. `EXG Channel 0` is board channel 1.

| File | Date / time (IST) | Test | Electrode on ch1 | Result |
|---|---|---|---|---|
| `01_integrity_board_streaming` | 2026-10-03 21:21–21:22 | Data integrity (rate, dropped samples) | none | PASS |
| `02_hardware_shorted_inputs` | 2026-10-03 21:39–21:40 | Inputs shorted inside the chip (noise floor) | none | PASS, 0.10 µV |
| `03_hardware_test_signal_gui` | 2026-10-04 00:46–00:47 | Internal ±1,875 µV square-wave test signal | none | PASS |
| `04_external_short_metal_key` | 2026-10-04 02:22 | Electrode + SRB + BIAS on one metal key | dry | PASS |
| `05_external_short_hands_free` | 2026-10-04 02:27–02:28 | Same, hands off | dry | PASS, 0.12 µV |
| `06_ecg_dry_first_attempt_fail` | 2026-10-04 13:20–13:21 | ECG, poor contact | dry | FAIL (kept for reference) |
| `07_ecg_gold_10min` | 2026-10-04 14:03–14:13 | ECG, 10 min | gold | PASS, SNR 47 |
| `08_ecg_dry_repaired` | 2026-10-04 23:26–23:32 | ECG | dry | partial: good beats, contact drops |
| `09_ecg_dry_vs_oximeter_video` | 2026-10-05 00:03:30–00:05 | ECG vs filmed pulse oximeter (00:04:01–00:04:29) | dry | PASS, 1.6 bpm |
| `10_ecg_gold_vs_oximeter_video` | 2026-10-05 00:14–00:16 | ECG vs filmed pulse oximeter (00:14:34 +56 s) | gold | PASS, 1.5 bpm |
| `11_blinks_dry` | 2026-10-08 01:30–01:31 | 10 spoken blink cues | dry | PASS, 10/10 |
| `12_jaw_clench_dry` | 2026-10-08 21:23 | 3 spoken clench / relax cues | dry | PASS, 6.8× |
| `15_blinks_dry_and_gold` | 2026-10-09 23:56–23:57 | 10 blink cues, dry on ch1 + gold with Ag/AgCl gel on ch2 (forehead) | dry + gold | PASS, 10/10 and 9/10 |
| `14_ssvep_12_15hz_dry` | 2026-10-08 22:52–22:54 | Rest / 12 Hz flicker / rest / 15 Hz flicker, 20 s each, electrode at O1 | dry | PASS, SNR 19 and 15 |
| `13_alpha_eyes_closed_open_dry` | 2026-10-08 22:43–22:46 | Eyes open / closed, 30 s × 3, electrode at O1 (back of head) | dry | PASS, 4.3× |

ECG tests: SRB on one wrist, electrode on the other, BIAS on the forearm. Alpha test: electrode at O1 in the headset, SRB left earlobe, BIAS right earlobe. Blink test: electrode above the left eyebrow, SRB left earlobe, BIAS right earlobe. Unused channels are unconnected and read as noise or at the ±187,500 µV limit.

Read one in Python:
```python
import pandas as pd
df = pd.read_csv("recordings/07_ecg_gold_10min.txt.gz", comment="%", skipinitialspace=True)
ch1 = df["EXG Channel 0"]
```
