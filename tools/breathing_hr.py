"""
Guided breathing protocol + beat-by-beat heart rate analysis (ECG on one channel).

Setup: SRB clip on one wrist, channel electrode on the OTHER wrist, BIAS on the
skin; OpenBCI GUI streaming (it records automatically). The script speaks each
phase, logs its wall-clock times, then reads the GUI's own recording file and
analyses heart rate per phase. No LSL needed.

Usage:
    python live_inference/breathing_hr.py                 # run protocol + analyse
    python live_inference/breathing_hr.py --quick         # short test run
    python live_inference/breathing_hr.py --analyze runs/breath_<stamp>.json
"""

import argparse
import glob
import json
import os
import subprocess
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, find_peaks, iirnotch, sosfiltfilt

FS = 250
RAIL_UV = 187000
RECORDINGS = os.path.expanduser("~/Documents/OpenBCI_GUI/Recordings")
OUT_DIR = os.path.join(os.path.dirname(__file__), "runs")

# (name, seconds, spoken instruction, paced-breathing period in s or None)
PROTOCOL = [
    ("Baseline", 60, "Breathe normally and stay still.", None),
    ("Paced 5-5", 60, "Paced breathing. Follow the prompts.", 10),
    ("Inhale hold", 20, "Breathe in fully, then hold gently. Do not push.", None),
    ("Recovery 1", 30, "Breathe normally.", None),
    ("Exhale hold", 15, "Breathe out fully, then hold.", None),
    ("Recovery 2", 30, "Breathe normally.", None),
]
QUICK = [("Baseline", 20, "Breathe normally.", None), ("Paced 5-5", 20, "Paced breathing.", 10),
         ("Inhale hold", 10, "Breathe in and hold.", None), ("Recovery 1", 10, "Breathe normally.", None),
         ("Exhale hold", 10, "Breathe out and hold.", None), ("Recovery 2", 10, "Breathe normally.", None)]

PHASE_COLORS = {"Baseline": "#f0efec", "Paced 5-5": "#cde2fb", "Inhale hold": "#fde2cf",
                "Recovery 1": "#f0efec", "Exhale hold": "#f9d3d3", "Recovery 2": "#f0efec"}
INK, INK2, BLUE, ORANGE = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834"


def say(text):
    """Speak without blocking (macOS `say`); fall back to print only."""
    try:
        subprocess.Popen(["say", "-r", "190", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def run_protocol(protocol):
    say("Get ready. Sit still with your hands resting.")
    for s in range(5, 0, -1):
        print(f"\rStarting in {s}s ", end="", flush=True)
        time.sleep(1)
    print()
    log = []
    for name, dur, instruction, period in protocol:
        print(f"\n▶ {name} ({dur}s): {instruction}")
        say(instruction)
        start = time.time()
        last_cue = None
        while (left := dur - (time.time() - start)) > 0:
            if period:
                cue = "in" if ((time.time() - start) % period) < period / 2 else "out"
                if cue != last_cue:
                    say(f"breathe {cue}")
                    last_cue = cue
            print(f"\r   {left:4.0f}s left  {('breathe ' + last_cue) if period else ''}   ", end="", flush=True)
            time.sleep(0.2)
        log.append({"phase": name, "start": start, "end": time.time()})
        print()
    say("Done. Thank you.")
    return log


def load_recordings(t0, t1):
    """Concatenate every GUI RAW file that overlaps [t0, t1]."""
    frames = []
    for path in sorted(glob.glob(os.path.join(RECORDINGS, "*", "OpenBCI-RAW-*.txt"))):
        if os.path.getmtime(path) < t0:
            continue
        df = pd.read_csv(path, comment="%", skipinitialspace=True, on_bad_lines="skip", low_memory=False)
        df = df.dropna(subset=["Timestamp (Formatted)"])
        # GUI timestamps are local wall-clock time; convert to epoch seconds like time.time()
        local = pd.to_datetime(df["Timestamp (Formatted)"], errors="coerce")
        utc_offset = datetime.now().astimezone().utcoffset().total_seconds()
        df["t"] = (local - pd.Timestamp("1970-01-01")).dt.total_seconds() - utc_offset
        frames.append(df[(df["t"] >= t0) & (df["t"] <= t1)])
    if not frames:
        raise SystemExit("No GUI recording covers the protocol time. Was the GUI streaming?")
    return pd.concat(frames).sort_values("t")


def detect_beats(x):
    """R-peak times (sample indices) from one ECG channel, robust to drift and hum."""
    b, a = iirnotch(50, 30, FS)
    q = filtfilt(b, a, sosfiltfilt(butter(3, [8, 30], "bandpass", fs=FS, output="sos"), x - np.median(x)))
    e = np.convolve(q ** 2, np.ones(10) / 10, "same")
    # adaptive threshold: 30% of the local 90th percentile (4 s blocks)
    block = 4 * FS
    levels = [np.percentile(e[i:i + block], 90) for i in range(0, len(e), block)]
    thr = 0.3 * np.interp(np.arange(len(e)), np.arange(len(levels)) * block + block / 2, levels)
    peaks, _ = find_peaks(e, distance=int(0.33 * FS), height=thr)
    return merge_double_detections(peaks, e)


def merge_double_detections(peaks, e):
    """Drop the weaker of two detections that are too close to both be heartbeats.

    A large T wave (or a second QRS lobe) can be detected ~0.3-0.45 s after the R peak,
    which makes intervals come out at half the true RR and doubles the heart rate.
    """
    peaks = list(peaks)
    while len(peaks) > 3:
        rr = np.diff(peaks)
        typical = np.percentile(rr, 75)              # robust to a mix of true and half intervals
        short = np.where(rr < 0.6 * typical)[0]
        if not len(short):
            break
        i = short[np.argmin(rr[short])]              # closest pair first
        drop = i if e[peaks[i]] < e[peaks[i + 1]] else i + 1
        peaks.pop(drop)
    # every beat doubled evenly: alternating strong/weak peaks -> keep the strong parity
    if len(peaks) >= 8:
        h = e[np.array(peaks)]
        odd, even = np.median(h[1::2]), np.median(h[0::2])
        if max(odd, even) > 2.5 * min(odd, even):
            peaks = peaks[1::2] if odd > even else peaks[0::2]
    return np.array(peaks, dtype=int)


def clean_rr(t_beats):
    """RR intervals with physiologically implausible / outlier beats removed."""
    rr = np.diff(t_beats)
    t_rr = t_beats[1:]
    ok = (rr > 0.33) & (rr < 2.0)
    med = pd.Series(rr).rolling(7, center=True, min_periods=3).median().to_numpy()
    ok &= np.abs(rr - med) < 0.25 * med
    return t_rr[ok], rr[ok]


def rmssd(rr):
    d = np.diff(rr)
    return float(np.sqrt(np.mean(d ** 2)) * 1000) if len(d) > 1 else float("nan")


def analyse(log, channel, out_prefix):
    t0, t1 = log[0]["start"] - 5, log[-1]["end"] + 2
    df = load_recordings(t0, t1)
    x = pd.to_numeric(df[f"EXG Channel {channel - 1}"], errors="coerce").to_numpy(float)
    t = df["t"].to_numpy(float)
    good = ~np.isnan(x)
    x, t = x[good], t[good]
    railed = np.mean(np.abs(x) > RAIL_UV) * 100

    peaks = detect_beats(x)
    t_rr, rr = clean_rr(t[peaks])
    hr = 60 / rr

    rows = []
    for ph in log:
        m = (t_rr >= ph["start"]) & (t_rr < ph["end"])
        r = rr[m]
        rows.append({"phase": ph["phase"], "seconds": round(ph["end"] - ph["start"]), "beats": int(m.sum()),
                     "mean_bpm": round(float(np.mean(60 / r)), 1) if len(r) else None,
                     "min_bpm": round(float(np.min(60 / r)), 1) if len(r) else None,
                     "max_bpm": round(float(np.max(60 / r)), 1) if len(r) else None,
                     "rmssd_ms": round(rmssd(r), 1) if len(r) > 2 else None})
    base = rows[0]["mean_bpm"]
    for row in rows:
        row["vs_baseline"] = round(row["mean_bpm"] - base, 1) if row["mean_bpm"] and base else None

    # paced breathing: heart-rate swing per 10 s breath cycle
    paced = next((ph for ph in log if ph["phase"].startswith("Paced")), None)
    rsa = None
    if paced:
        swings = []
        for c in np.arange(paced["start"], paced["end"] - 9.9, 10):
            m = (t_rr >= c) & (t_rr < c + 10)
            if m.sum() >= 4:
                swings.append(hr[m].max() - hr[m].min())
        rsa = round(float(np.median(swings)), 1) if swings else None

    print(f"\nChannel {channel}: {len(peaks)} beats detected, {len(rr)} kept after cleaning, railed {railed:.0f}%")
    print(f"{'phase':12s} {'sec':>4s} {'beats':>5s} {'mean':>6s} {'min':>6s} {'max':>6s} {'Δbase':>6s} {'RMSSD':>6s}")
    for r in rows:
        fmt = lambda v, w=6: f"{v:{w}.1f}" if isinstance(v, (int, float)) and v is not None else f"{'-':>{w}s}"
        print(f"{r['phase']:12s} {r['seconds']:4d} {r['beats']:5d} {fmt(r['mean_bpm'])} {fmt(r['min_bpm'])} "
              f"{fmt(r['max_bpm'])} {fmt(r['vs_baseline'])} {fmt(r['rmssd_ms'])}")
    if rsa is not None:
        print(f"Paced breathing heart-rate swing (in vs out): {rsa} bpm per breath")

    # plot
    fig, ax = plt.subplots(figsize=(12, 4.6))
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    origin = log[0]["start"]
    for ph in log:
        ax.axvspan(ph["start"] - origin, ph["end"] - origin, color=PHASE_COLORS.get(ph["phase"], "#f0efec"), lw=0)
        ax.text((ph["start"] + ph["end"]) / 2 - origin, 0.98, ph["phase"], transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=9, color=INK2)
    ax.plot(t_rr - origin, hr, color=BLUE, lw=1.6, marker="o", ms=3, label="beat-by-beat heart rate")
    for r, ph in zip(rows, log):
        if r["mean_bpm"]:
            ax.hlines(r["mean_bpm"], ph["start"] - origin, ph["end"] - origin, color=ORANGE, lw=2)
    ax.plot([], [], color=ORANGE, lw=2, label="phase mean")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("Time from start (s)", color=INK2)
    ax.set_ylabel("Heart rate (bpm)", color=INK2)
    ax.set_title(f"Heart rate through the breathing protocol — {datetime.fromtimestamp(origin):%Y-%m-%d %H:%M}",
                 loc="left", color=INK)
    ax.grid(axis="y", color="#ecebe8")
    ax.legend(frameon=False, loc="lower right")
    lo, hi = np.percentile(hr, [1, 99]) if len(hr) else (50, 100)
    ax.set_ylim(lo - 8, hi + 12)
    fig.tight_layout()
    fig.savefig(out_prefix + ".png", dpi=130)

    pd.DataFrame({"time": t_rr, "t_from_start": t_rr - origin, "rr_s": rr, "bpm": hr}).to_csv(
        out_prefix + "_beats.csv", index=False)
    with open(out_prefix + "_summary.json", "w") as fh:
        json.dump({"phases": rows, "paced_rsa_bpm": rsa, "channel": channel, "railed_pct": railed}, fh, indent=2)
    print(f"\nSaved {out_prefix}.png, _beats.csv, _summary.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", type=int, default=1)
    ap.add_argument("--quick", action="store_true", help="short protocol for testing")
    ap.add_argument("--analyze", help="re-analyse a saved phase log (.json)")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.analyze:
        with open(args.analyze) as fh:
            log = json.load(fh)["phases"]
        prefix = args.analyze.replace(".json", "")
    else:
        log = run_protocol(QUICK if args.quick else PROTOCOL)
        prefix = os.path.join(OUT_DIR, f"breath_{datetime.now():%Y%m%d_%H%M%S}")
        with open(prefix + ".json", "w") as fh:
            json.dump({"phases": log, "channel": args.channel}, fh, indent=2)
        print("\nWaiting 3 s for the GUI to flush its recording file...")
        time.sleep(3)
    analyse(log, args.channel, prefix)


if __name__ == "__main__":
    main()
