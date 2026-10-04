"""
Live heartbeat (ECG) monitor from the OpenBCI GUI's LSL TimeSeriesRaw stream.

Setup: SRB + BIAS clips on the skin, a channel electrode on the skin (ideally the
other arm/hand), and the GUI Networking widget streaming TimeSeriesRaw over LSL.

Usage:
    python live_inference/heart_monitor.py --channel 1 --every 3
"""

import argparse
import time

import numpy as np
from pylsl import StreamInlet, resolve_streams
from scipy.signal import butter, filtfilt, find_peaks, iirnotch, sosfiltfilt, welch

FS = 250
RAIL_UV = 187000


def raw_inlet(timeout=5):
    """Pick the stream with the large DC offset - that is TimeSeriesRaw."""
    inlets = [StreamInlet(s, max_buflen=60) for s in resolve_streams(wait_time=timeout) if s.channel_count() >= 8]
    if not inlets:
        raise SystemExit("No LSL streams found. Start the LSL stream in the GUI Networking widget.")
    probe = {}
    end = time.time() + 2
    while time.time() < end:
        for i, inlet in enumerate(inlets):
            chunk, _ = inlet.pull_chunk(timeout=0.0)
            if chunk:
                probe.setdefault(i, []).extend(chunk)
        time.sleep(0.05)
    offsets = {i: np.median(np.abs(np.mean(np.asarray(v)[:, :8], axis=0))) for i, v in probe.items()}
    return inlets[max(offsets, key=offsets.get)]


def analyse(x):
    """Return heart rate, beat-to-beat variability, R-peak size and signal quality."""
    out = {"railed": float(np.mean(np.abs(x) > RAIL_UV) * 100)}
    if out["railed"] > 5:
        return out
    x = x - x.mean()
    f, p = welch(x, FS, nperseg=min(500, len(x)))
    out["mains_uv"] = float(np.sqrt(p[(f >= 48) & (f < 52)].sum() * (f[1] - f[0])))

    b, a = iirnotch(50, 30, FS)
    qrs = filtfilt(b, a, sosfiltfilt(butter(3, [5, 25], "bandpass", fs=FS, output="sos"), x))
    env = np.abs(qrs)
    peaks, _ = find_peaks(env, distance=int(0.33 * FS), prominence=np.percentile(env, 99) * 0.4)
    if len(peaks) < 3:
        return out
    rr = np.diff(peaks) / FS
    rr = rr[(rr > 0.33) & (rr < 2.0)]           # 30-180 bpm
    if len(rr) < 2:
        return out
    beat = np.median(env[peaks])
    between = np.median(env[np.setdiff1d(np.arange(len(env)), np.concatenate([np.arange(p - 25, p + 25) for p in peaks]).clip(0, len(env) - 1))])
    out.update(bpm=60 / np.median(rr), rr_ms=np.median(rr) * 1000, rr_sd_ms=rr.std() * 1000,
               r_uv=float(beat), snr=float(beat / max(between, 1e-6)), beats=len(peaks))
    return out


def quality(o):
    if o["railed"] > 5:
        return "RAILED - electrode or clips not on skin"
    if "bpm" not in o:
        return "no clear heartbeat yet"
    if o["snr"] > 8 and o["rr_sd_ms"] < 150:
        return "GOOD"
    if o["snr"] > 4:
        return "ok"
    return "noisy"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", type=int, default=1)
    ap.add_argument("--every", type=float, default=3)
    ap.add_argument("--window", type=float, default=10)
    args = ap.parse_args()

    inlet = raw_inlet()
    buf = np.empty(0)
    keep = int(args.window * FS)
    nxt = time.time() + args.every
    print(f"Monitoring channel {args.channel} ({args.window:.0f}s window, report every {args.every:.0f}s)")
    print("time      quality   bpm   RR(ms)  RR-sd  R-peak(µV)  SNR   50Hz(µV)")
    while True:
        chunk, _ = inlet.pull_chunk(timeout=0.0)
        if chunk:
            buf = np.concatenate([buf, np.asarray(chunk)[:, args.channel - 1]])[-keep:]
        if time.time() >= nxt and len(buf) > 4 * FS:
            nxt += args.every
            o = analyse(buf)
            stamp = time.strftime("%H:%M:%S")
            if "bpm" in o:
                print(f"{stamp}  {quality(o):8s} {o['bpm']:5.0f}  {o['rr_ms']:6.0f}  {o['rr_sd_ms']:5.0f}  "
                      f"{o['r_uv']:9.0f}  {o['snr']:5.1f}  {o['mains_uv']:7.0f}", flush=True)
            else:
                print(f"{stamp}  {quality(o)}  (railed {o['railed']:.0f}%, 50Hz {o.get('mains_uv', 0):.0f} µV)", flush=True)
        time.sleep(0.05)


if __name__ == "__main__":
    main()
