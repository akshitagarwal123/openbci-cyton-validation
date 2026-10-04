"""
Live monitor for the OpenBCI GUI's LSL streams.

The GUI does not expose its filter settings, but its Networking widget can
stream both the filtered signal (exactly what is drawn on screen) and the raw
signal. Comparing the two gives the effective filter the GUI is applying.

GUI setup (Networking widget):
    Protocol: LSL
    Stream 1: Data Type = TimeSeriesFilt
    Stream 2: Data Type = TimeSeriesRaw
    Click "Start LSL Stream"

Usage:
    python live_inference/gui_monitor.py              # report every 5 s
    python live_inference/gui_monitor.py --every 10 --window 10
"""

import argparse
import time

import numpy as np
from pylsl import StreamInlet, resolve_streams
from scipy.signal import welch

FS = 250
RAIL_UV = 187000


def find_streams(timeout):
    streams = resolve_streams(wait_time=timeout)
    if not streams:
        raise SystemExit("No LSL streams found. Start the LSL stream in the GUI Networking widget.")
    for s in streams:
        print(f"  found: name={s.name()!r} type={s.type()!r} ch={s.channel_count()} fs={s.nominal_srate()}")
    return [StreamInlet(s, max_buflen=60) for s in streams if s.channel_count() >= 8]


def classify(buffers):
    """Raw data carries a large DC offset; filtered data is centred on zero."""
    offsets = {k: np.median(np.abs(np.mean(v, axis=0))) for k, v in buffers.items() if len(v) > FS}
    if len(offsets) < 2:
        return None, None
    raw = max(offsets, key=offsets.get)
    filt = min(offsets, key=offsets.get)
    return (raw, filt) if raw != filt else (None, None)


def band_amp(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(p[m].sum() * (f[1] - f[0])))


def estimate_filter(raw, filt):
    """Effective GUI filter gain |H(f)| = sqrt(P_filt / P_raw), median over channels."""
    n = min(len(raw), len(filt))
    raw, filt = raw[-n:], filt[-n:]
    gains = []
    for ch in range(raw.shape[1]):
        r = raw[:, ch] - raw[:, ch].mean()
        if np.abs(raw[:, ch]).max() > RAIL_UV or r.std() == 0:
            continue
        f, pr = welch(r, FS, nperseg=min(512, n))
        _, pf = welch(filt[:, ch] - filt[:, ch].mean(), FS, nperseg=min(512, n))
        gains.append(np.sqrt(pf / np.maximum(pr, 1e-12)))
    if not gains:
        return None
    g = np.median(gains, axis=0)

    passband = f[g >= 0.5]
    lo, hi = (float(passband.min()), float(passband.max())) if len(passband) else (None, None)
    at = lambda hz: float(np.interp(hz, f, g))
    # A notch is only observable if the bandpass lets the neighbouring frequencies through
    notch50 = None if max(at(46), at(54)) < 0.3 else at(50) < 0.1
    notch60 = None if max(at(56), at(64)) < 0.3 else at(60) < 0.1
    return {"low": lo, "high": hi, "notch50": notch50, "notch60": notch60,
            "gain@": {hz: round(at(hz), 2) for hz in (1, 5, 8, 30, 45, 50, 60)}}


def report(raw, filt):
    stamp = time.strftime("%H:%M:%S")
    print(f"\n=== {stamp}  ({len(filt) / FS:.0f}s window) ===")
    est = estimate_filter(raw, filt)
    if est:
        bp = f"{est['low']:.1f}-{est['high']:.1f} Hz" if est["low"] is not None else "nothing passes"
        if est["notch50"] is None and est["notch60"] is None:
            notch = "can't tell (bandpass already removes 50/60 Hz)"
        else:
            notch = "50 Hz" if est["notch50"] else "60 Hz" if est["notch60"] else "OFF"
        print(f"GUI filter (estimated): passband {bp} | notch {notch} | gain {est['gain@']}")
    print(" ch | on-screen rms  ptp/s | raw: offset   railed  50Hz    1-5Hz  8-13Hz 13-30Hz")
    for ch in range(filt.shape[1]):
        y = filt[:, ch]
        ptp = np.median([np.ptp(y[s:s + FS]) for s in range(0, len(y) - FS + 1, FS)])
        r = raw[-len(filt):, ch]
        f, p = welch(r - r.mean(), FS, nperseg=min(512, len(r)))
        railed = np.mean(np.abs(r) > RAIL_UV) * 100
        print(f" {ch + 1:2d} | {y.std():8.1f} {ptp:8.1f}   | {r.mean():9.0f} {railed:5.0f}% "
              f"{band_amp(f, p, 48, 52):7.1f} {band_amp(f, p, 1, 5):7.1f} "
              f"{band_amp(f, p, 8, 13):7.1f} {band_amp(f, p, 13, 30):7.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=float, default=5, help="seconds between reports")
    ap.add_argument("--window", type=float, default=10, help="seconds of data per report")
    ap.add_argument("--channels", type=int, default=8)
    args = ap.parse_args()

    print("Looking for OpenBCI GUI LSL streams...")
    inlets = find_streams(timeout=5)
    keep = int(args.window * FS)
    buffers = {i: np.empty((0, args.channels)) for i in range(len(inlets))}
    next_report = time.time() + args.every

    while True:
        for i, inlet in enumerate(inlets):
            chunk, _ = inlet.pull_chunk(timeout=0.0)
            if chunk:
                buffers[i] = np.vstack([buffers[i], np.asarray(chunk)[:, :args.channels]])[-keep:]
        if time.time() >= next_report:
            next_report += args.every
            raw_i, filt_i = classify(buffers)
            if raw_i is None:
                print("Need both TimeSeriesRaw and TimeSeriesFilt streams with data; waiting...")
                continue
            report(buffers[raw_i], buffers[filt_i])
        time.sleep(0.05)


if __name__ == "__main__":
    main()
