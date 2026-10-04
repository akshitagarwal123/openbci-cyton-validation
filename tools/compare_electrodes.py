"""
Compare ECG signal quality between two electrodes (e.g. dry vs gold cup).

Simultaneous mode (default, fairest): both electrodes side by side on the same
wrist, one per channel, sharing SRB/BIAS - they see the same heartbeats, so any
difference is the electrode.
Sequential mode: record electrode A, prompt to swap, record electrode B.

Usage:
    python live_inference/compare_electrodes.py                       # ch1 vs ch2, 60 s together
    python live_inference/compare_electrodes.py --labels Dry Gold --seconds 90
    python live_inference/compare_electrodes.py --sequential --channels 1 1
    python live_inference/compare_electrodes.py --analyze runs/compare_<stamp>.json
"""

import argparse
import json
import os
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, iirnotch, sosfiltfilt, welch

from breathing_hr import FS, OUT_DIR, RAIL_UV, clean_rr, detect_beats, load_recordings, say

COLORS = ["#2a78d6", "#eb6834"]
INK, INK2 = "#0b0b0b", "#52514e"


def record(seconds, prompt):
    say(prompt)
    print(f"\n▶ {prompt} ({seconds}s)")
    for s in range(5, 0, -1):
        print(f"\r   starting in {s}s ", end="", flush=True)
        time.sleep(1)
    say("Recording. Stay still.")
    start = time.time()
    while (left := seconds - (time.time() - start)) > 0:
        print(f"\r   recording… {left:4.0f}s left   ", end="", flush=True)
        time.sleep(0.5)
    print()
    return {"start": start, "end": time.time()}


def ecg(x):
    b, a = iirnotch(50, 30, FS)
    return filtfilt(b, a, sosfiltfilt(butter(2, [0.5, 40], "bandpass", fs=FS, output="sos"), x - np.median(x)))


def quality(x, t):
    """Signal-quality metrics for one ECG channel segment."""
    out = {"seconds": round(float(t[-1] - t[0]), 1), "railed_pct": round(float(np.mean(np.abs(x) > RAIL_UV) * 100), 1)}
    f, p = welch(x - x.mean(), FS, nperseg=1000)
    band = lambda lo, hi: float(np.sqrt(p[(f >= lo) & (f < hi)].sum() * (f[1] - f[0])))
    slow = sosfiltfilt(butter(2, 1, "lowpass", fs=FS, output="sos"), x)
    out.update(offset_uv=round(float(np.median(x))), drift_uv=round(float(np.ptp(slow))),
               mains_50hz_uv=round(band(48, 52), 1), below_1hz_uv=round(band(0.1, 1), 1))
    out["_spectrum"] = (f, np.sqrt(p * (f[1] - f[0])))
    if out["railed_pct"] > 5:
        return out

    peaks = detect_beats(x)
    t_rr, rr = clean_rr(t[peaks])
    y = ecg(x)
    pre, post = int(0.3 * FS), int(0.55 * FS)
    R = []
    for pk in peaks:
        lo = max(pk - 8, 0)
        r = lo + np.argmax(np.abs(y[lo:pk + 8]))
        if r - pre >= 0 and r + post <= len(y):
            R.append(r)
    ep = np.array([y[r - pre:r + post] for r in R])
    ep = ep - np.median(ep[:, :15], axis=1, keepdims=True)
    tmpl = np.median(ep, axis=0)
    corr = np.array([np.corrcoef(e, tmpl)[0, 1] for e in ep])
    r_amp = float(np.max(np.abs(tmpl[pre - 10:pre + 10])))
    # noise = beat-to-beat scatter around the template in the quiet part before P (-300..-200 ms)
    quiet = slice(0, int(0.1 * FS))
    noise = float(np.median(np.std(ep[:, quiet] - tmpl[quiet], axis=1)))
    out.update(beats=len(peaks), kept_pct=round(len(rr) / max(len(peaks) - 1, 1) * 100, 1),
               mean_bpm=round(float(np.mean(60 / rr)), 1) if len(rr) else None,
               r_peak_uv=round(r_amp), noise_uv=round(noise, 1), snr=round(r_amp / max(noise, 1e-6), 1),
               shape_match=round(float(np.median(corr)), 3), clean_beats_pct=round(float(np.mean(corr > 0.8) * 100), 1),
               filtered_rms_uv=round(float(np.std(y)), 1))
    out["_template"], out["_y"], out["_peaks"], out["_rr"] = tmpl, y, peaks, (t_rr, rr)
    return out


def verdict(a, b, la, lb):
    """Plain-language comparison of the two channels."""
    bad = [lab for r, lab in ((a, la), (b, lb)) if r["railed_pct"] > 5 or "snr" not in r]
    if bad:
        return "  " + ", ".join(bad) + " railed or no heartbeat found — check that electrode is on the skin; no comparison."
    lines = []
    def better(key, higher=True, fmt="{:.1f}", unit=""):
        va, vb = a.get(key), b.get(key)
        if va is None or vb is None:
            return
        win = la if (va > vb) == higher else lb
        ratio = (max(va, vb) / max(min(va, vb), 1e-6))
        lines.append(f"  {key:16s} {la}: {fmt.format(va)}{unit}   {lb}: {fmt.format(vb)}{unit}   → {win} better ({ratio:.1f}×)")
    better("snr")
    better("r_peak_uv", fmt="{:.0f}", unit=" µV")
    better("noise_uv", higher=False, unit=" µV")
    better("mains_50hz_uv", higher=False, unit=" µV")
    better("drift_uv", higher=False, fmt="{:.0f}", unit=" µV")
    better("shape_match", fmt="{:.3f}")
    better("kept_pct", unit="%")
    return "\n".join(lines)


def plot(res, labels, out_png, title):
    fig = plt.figure(figsize=(14, 8.5))
    fig.patch.set_facecolor("#fcfcfb")
    gs = fig.add_gridspec(3, 2, width_ratios=[1, 1.5], hspace=0.55, wspace=0.18)
    axes = [fig.add_subplot(gs[0:2, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[2, :])]
    for ax in axes:
        ax.set_facecolor("#fcfcfb")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="y", color="#ecebe8")
        ax.tick_params(colors=INK2)

    tt = (np.arange(int(0.85 * FS)) - int(0.3 * FS)) / FS * 1000
    for r, lab, c in zip(res, labels, COLORS):
        if "_template" in r:
            axes[0].plot(tt, r["_template"], color=c, lw=2.2, label=f"{lab}  (SNR {r['snr']})")
    axes[0].set_title("Average heartbeat", loc="left", color=INK)
    axes[0].set_xlabel("ms from R peak", color=INK2)
    axes[0].set_ylabel("µV", color=INK2)
    axes[0].legend(frameon=False)

    for ax, r, lab, c in zip(axes[1:3], res, labels, COLORS):
        if "_y" not in r:
            ax.set_title(f"{lab}: railed / no beats", loc="left", color=INK)
            continue
        y, pk = r["_y"], r["_peaks"]
        n = min(len(y), 8 * FS)
        s0 = len(y) // 2 - n // 2
        seg = y[s0:s0 + n]
        ax.plot(np.arange(n) / FS, seg, color=c, lw=1)
        vis = pk[(pk >= s0) & (pk < s0 + n)]
        ax.plot((vis - s0) / FS, y[vis], "o", ms=6, mfc="none", mec=INK2, mew=1.2)
        lo, hi = np.percentile(seg, [0.5, 99.5])
        ax.set_ylim(lo * 1.3, hi * 1.3)
        ax.set_title(f"{lab}: 8 s of ECG (0.5–40 Hz, notch 50)", loc="left", color=INK, fontsize=11)
    axes[2].set_xlabel("s", color=INK2)

    for r, lab, c in zip(res, labels, COLORS):
        f, a = r["_spectrum"]
        m = f <= 70
        axes[3].plot(f[m], a[m], color=c, lw=1.6, label=lab)
    axes[3].set_yscale("log")
    axes[3].set_xlim(0, 70)
    axes[3].set_title("Raw spectrum (before filtering)", loc="left", color=INK)
    axes[3].set_xlabel("Hz", color=INK2)
    axes[3].set_ylabel("µV per bin", color=INK2)
    axes[3].legend(frameon=False)
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=13)
    fig.savefig(out_png, dpi=120, bbox_inches="tight")


def analyse(meta, prefix):
    labels, chans, wins = meta["labels"], meta["channels"], meta["windows"]
    res = []
    for ch, w in zip(chans, wins):
        df = load_recordings(w["start"] + 3, w["end"])          # skip the first 3 s settling
        x = pd.to_numeric(df[f"EXG Channel {ch - 1}"], errors="coerce").to_numpy(float)
        t = df["t"].to_numpy(float)
        ok = ~np.isnan(x)
        res.append(quality(x[ok], t[ok]))

    keys = ["seconds", "railed_pct", "offset_uv", "drift_uv", "mains_50hz_uv", "beats", "kept_pct", "mean_bpm",
            "r_peak_uv", "noise_uv", "snr", "shape_match", "clean_beats_pct", "filtered_rms_uv"]
    print(f"\n{'metric':18s}" + "".join(f"{lab:>14s}" for lab in labels))
    for k in keys:
        print(f"{k:18s}" + "".join(f"{str(r.get(k, '-')):>14s}" for r in res))
    print("\nComparison:\n" + verdict(res[0], res[1], *labels))

    when = datetime.fromtimestamp(wins[0]["start"])
    mode = "same time" if meta["mode"] == "simultaneous" else "one after the other"
    plot(res, labels, prefix + ".png", f"ECG electrode comparison — {labels[0]} vs {labels[1]}, {when:%Y-%m-%d %H:%M}, recorded {mode}")
    with open(prefix + "_summary.json", "w") as fh:
        json.dump({lab: {k: v for k, v in r.items() if not k.startswith("_")} for lab, r in zip(labels, res)}, fh, indent=2)
    print(f"\nSaved {prefix}.png and _summary.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", type=int, nargs=2, default=[1, 2])
    ap.add_argument("--labels", nargs=2, default=["Dry", "Gold"])
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--sequential", action="store_true", help="record A, then swap to B")
    ap.add_argument("--analyze", help="re-analyse a saved run (.json)")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.analyze:
        with open(args.analyze) as fh:
            meta = json.load(fh)
        prefix = args.analyze.replace(".json", "")
    else:
        la, lb = args.labels
        if args.sequential:
            w1 = record(args.seconds, f"Place the {la} electrode and keep still.")
            w2 = record(args.seconds, f"Now swap to the {lb} electrode.")
            wins, mode = [w1, w2], "sequential"
        else:
            w = record(args.seconds, f"Both electrodes on. {la} and {lb} side by side.")
            wins, mode = [w, w], "simultaneous"
        say("Done.")
        meta = {"labels": [la, lb], "channels": args.channels, "windows": wins, "mode": mode}
        prefix = os.path.join(OUT_DIR, f"compare_{datetime.now():%Y%m%d_%H%M%S}")
        with open(prefix + ".json", "w") as fh:
            json.dump(meta, fh, indent=2)
        print("Waiting 3 s for the GUI to flush its recording file...")
        time.sleep(3)
    analyse(meta, prefix)


if __name__ == "__main__":
    main()
