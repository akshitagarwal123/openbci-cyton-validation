# Synced face + EEG videos

Each video shows the camera (face blurred and eyes pixelated for privacy; electrodes kept sharp) next to the EEG recorded at the same moment, scrolling past a red "now" line. Built with `tools/video_eeg.py`; camera frames carry clock timestamps, so camera and EEG are aligned exactly (except the first blink video, see below).

On the EEG side: a µV scale per channel, seconds from the start of the test, the signal size (RMS µV) for every second above each trace, dashed lines at each cue, and a red banner on the face side while a cue or block is active.

| Video | Test | What to watch |
|---|---|---|
| `blinks_dry_gold_oct9_estimated_sync.mp4` | Blinks, dry (ch1) + gold (ch2) on the forehead | A large dip on both channels after each BLINK cue. **Sync estimated (±1 s)**: recorded before the clock-stamped camera tool existed |
| `jaw_dry_gold_oct10.mp4` | Jaw clench, 20–45 Hz | Muscle bursts on both channels after each CLENCH cue |
| `alpha_dry_gold_oct11.mp4` | Eyes open / closed, 8–13 Hz, dry O1 + gold Oz | Alpha waves grow in every EYES CLOSED block (per-second size ~4–6 → 8–11 µV) |
| `ssvep_dry_gold_oct11.mp4` | 12 Hz and 15 Hz flicker, 10–17 Hz | Bottom row: live size of the wave at exactly 12 Hz (green) and 15 Hz (purple) on the dry electrode. Green rises during the 12 Hz flicker, purple during 15 Hz; green also jumps in the first seconds after the 12 Hz flicker (alpha rebound at 11–12.5 Hz) |
