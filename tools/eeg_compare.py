"""
Compare EEG quality of two electrodes (e.g. dry comb vs gold cup) recorded together.

Standard test: alpha rhythm (8-13 Hz) over the occipital cortex grows when the eyes
close and shrinks when they open. A good electrode shows this clearly.

Setup: dry on O1 -> channel 1, gold cup + paste on O2 -> channel 2,
SRB on left earlobe, BIAS on right earlobe, GUI streaming, 50 Hz notch on.

Usage:
    python live_inference/eeg_compare.py                     # full protocol (~4 min) + analysis
    python live_inference/eeg_compare.py --rounds 2 --block 20
    python live_inference/eeg_compare.py --analyze runs/eeg_<stamp>.json
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

from breathing_hr import FS, OUT_DIR, RAIL_UV, load_recordings, say

COLORS = ["#2a78d6", "#eb6834"]
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
SHADE = {"Eyes open": "#f0efec", "Eyes closed": "#cde2fb", "Blinks": "#fde2cf", "Jaw clench": "#f9d3d3"}
SETTLE_S = 3          # ignore the first seconds of each block (eyes moving, settling)
ARTIFACT_UV = 100     # 2 s epoch rejected if its 1-40 Hz peak-to-peak exceeds this


def protocol(rounds, block):
    steps = []
    for _ in range(rounds):
        steps += [("Eyes open", block, "Eyes open. Look at one point and relax."),
                  ("Eyes closed", block, "Close your eyes and relax.")]
    steps += [("Blinks", 10, "Eyes open. Blink normally every two seconds."),
              ("Jaw clench", 5, "Gently clench your jaw."),
              ("Eyes open", 5, "Relax your jaw.")]
    return steps


def run(steps):
    say("Get ready. Sit still and relax your face and shoulders.")
    for s in range(5, 0, -1):
        print(f"\rStarting in {s}s ", end="", flush=True)
        time.sleep(1)
    print()
    log = []
    for name, dur, text in steps:
        print(f"\n▶ {name} ({dur}s)")
        say(text)
        start = time.time()
        while (left := dur - (time.time() - start)) > 0:
            print(f"\r   {left:4.0f}s left   ", end="", flush=True)
            time.sleep(0.2)
        log.append({"phase": name, "start": start, "end": time.time()})
    print()
    say("Done. You can open your eyes.")
    return log


def filt(x):
    b, a = iirnotch(50, 30, FS)
    return filtfilt(b, a, sosfiltfilt(butter(4, [1, 40], "bandpass", fs=FS, output="sos"), x - np.median(x)))


def psd(segments):
    """Average Welch PSD over clean 2 s epochs from a list of filtered segments."""
    eps = []
    for y in segments:
        for i in range(0, len(y) - 2 * FS + 1, FS):           # 2 s epochs, 1 s step
            e = y[i:i + 2 * FS]
            if np.ptp(e) < ARTIFACT_UV:
                eps.append(e)
    if not eps:
        return None, None, 0
    f, p = welch(np.array(eps), FS, nperseg=2 * FS, axis=-1)
    return f, p.mean(axis=0), len(eps)


def band(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(p[m].sum() * (f[1] - f[0]))


def metrics(x, t, log):
    y = filt(x)
    out = {"railed_pct": round(float(np.mean(np.abs(x) > RAIL_UV) * 100), 1),
           "offset_uv": round(float(np.median(x))),
           "drift_uv": round(float(np.ptp(sosfiltfilt(butter(2, 0.5, "lowpass", fs=FS, output="sos"), x))))}
    fr, pr = welch(x - x.mean(), FS, nperseg=2 * FS)
    out["mains_50hz_uv"] = round(np.sqrt(band(fr, pr, 48, 52)), 1)

    seg = lambda name: [y[(t >= ph["start"] + SETTLE_S) & (t < ph["end"])] for ph in log if ph["phase"] == name]
    eo, ec = seg("Eyes open"), seg("Eyes closed")

    # clean-data share over eyes-open/closed blocks
    total = clean = 0
    for s in eo + ec:
        for i in range(0, len(s) - 2 * FS + 1, 2 * FS):
            total += 1
            clean += np.ptp(s[i:i + 2 * FS]) < ARTIFACT_UV
    out["clean_epochs_pct"] = round(100 * clean / max(total, 1), 1)

    f, p_eo, n_eo = psd(eo)
    _, p_ec, n_ec = psd(ec)
    out["epochs_eo"], out["epochs_ec"] = n_eo, n_ec
    if p_eo is None or p_ec is None:
        return out, y, None
    a_eo, a_ec = band(f, p_eo, 8, 13), band(f, p_ec, 8, 13)
    m = (f >= 7) & (f <= 14)
    peak = float(f[m][np.argmax(p_ec[m])])
    flank = np.mean([p_ec[(f >= 4) & (f < 7)].mean(), p_ec[(f > 14) & (f <= 20)].mean()])
    out.update(alpha_eo_uv=round(np.sqrt(a_eo), 2), alpha_ec_uv=round(np.sqrt(a_ec), 2),
               alpha_reactivity=round(a_ec / a_eo, 2), alpha_peak_hz=round(peak, 1),
               alpha_peak_snr=round(float(p_ec[f == peak][0] / flank), 1),
               noise_35_45_uv=round(np.sqrt(band(f, p_eo, 35, 45)), 2),
               broadband_eo_uv=round(np.sqrt(band(f, p_eo, 1, 40)), 1))
    for name, key, lo in (("Blinks", "blink_ptp_uv", 0), ("Jaw clench", "jaw_emg_uv", 20)):
        s = seg(name)
        if s and len(s[0]) > FS:
            out[key] = round(float(np.ptp(s[0]) if lo == 0 else
                                   np.std(sosfiltfilt(butter(4, [20, 40], "bandpass", fs=FS, output="sos"), s[0]))), 1)
    return out, y, (f, p_eo, p_ec)


def alpha_envelope(y):
    a = sosfiltfilt(butter(4, [8, 13], "bandpass", fs=FS, output="sos"), y)
    k = FS  # 1 s RMS
    return np.sqrt(np.convolve(a ** 2, np.ones(k) / k, "same"))


def plot(res, labels, log, t, ys, out_png, when):
    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor("#fcfcfb")
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.4, wspace=0.18)
    axs = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
    for ax in axs:
        ax.set_facecolor("#fcfcfb")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="y", color="#ecebe8")
        ax.tick_params(colors=INK2)

    for ax, (r, spec), lab, c in zip(axs[:2], res, labels, COLORS):
        if spec is None:
            ax.set_title(f"{lab}: not enough clean data", loc="left", color=INK)
            continue
        f, p_eo, p_ec = spec
        m = (f >= 1) & (f <= 40)
        ax.plot(f[m], np.sqrt(p_eo[m]), color=MUTED, lw=1.8, label="eyes open")
        ax.plot(f[m], np.sqrt(p_ec[m]), color=c, lw=2.2, label="eyes closed")
        ax.axvspan(8, 13, color="#ecebe8", lw=0)
        ax.set_yscale("log")
        ax.set_xlabel("Hz", color=INK2)
        ax.set_ylabel("µV/√Hz", color=INK2)
        ax.set_title(f"{lab}: alpha ×{r['alpha_reactivity']} with eyes closed, peak {r['alpha_peak_hz']} Hz",
                     loc="left", color=INK, fontsize=11)
        ax.legend(frameon=False)

    ax = axs[2]
    origin = log[0]["start"]
    for ph in log:
        ax.axvspan(ph["start"] - origin, ph["end"] - origin, color=SHADE.get(ph["phase"], "#f0efec"), lw=0)
        ax.text((ph["start"] + ph["end"]) / 2 - origin, 0.98, ph["phase"].replace(" ", "\n"),
                transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=8, color=INK2)
    for y, lab, c in zip(ys, labels, COLORS):
        env = alpha_envelope(y)
        ax.plot(t - origin, env, color=c, lw=1.4, label=lab)
    ax.set_ylim(0, np.percentile(np.concatenate([alpha_envelope(y) for y in ys]), 99) * 1.4)
    ax.set_xlabel("Time from start (s)", color=INK2)
    ax.set_ylabel("alpha amplitude, 8–13 Hz (µV)", color=INK2)
    ax.set_title("Alpha over time — should rise in every eyes-closed block", loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.88))
    fig.suptitle(f"EEG electrode comparison — {labels[0]} vs {labels[1]}, {when:%Y-%m-%d %H:%M}",
                 x=0.01, ha="left", color=INK, fontsize=13)
    fig.savefig(out_png, dpi=120, bbox_inches="tight")


def analyse(meta, prefix):
    log, labels, chans = meta["phases"], meta["labels"], meta["channels"]
    df = load_recordings(log[0]["start"] - 2, log[-1]["end"] + 1)
    t = df["t"].to_numpy(float)
    res, ys = [], []
    for ch in chans:
        x = pd.to_numeric(df[f"EXG Channel {ch - 1}"], errors="coerce").to_numpy(float)
        x = pd.Series(x).interpolate(limit_direction="both").to_numpy()
        m, y, spec = metrics(x, t, log)
        res.append((m, spec))
        ys.append(y)

    keys = ["railed_pct", "offset_uv", "drift_uv", "mains_50hz_uv", "clean_epochs_pct", "epochs_eo", "epochs_ec",
            "alpha_eo_uv", "alpha_ec_uv", "alpha_reactivity", "alpha_peak_hz", "alpha_peak_snr",
            "noise_35_45_uv", "broadband_eo_uv", "blink_ptp_uv", "jaw_emg_uv"]
    print(f"\n{'metric':18s}" + "".join(f"{lab:>14s}" for lab in labels))
    for k in keys:
        print(f"{k:18s}" + "".join(f"{str(m.get(k, '-')):>14s}" for m, _ in res))

    (a, _), (b, _) = res
    if "alpha_ec_uv" in a and "alpha_ec_uv" in b:
        ea, eb = alpha_envelope(ys[0]), alpha_envelope(ys[1])
        r = float(np.corrcoef(ea, eb)[0, 1])
        print(f"\nAlpha agreement between channels (envelope correlation): {r:.2f}")
        for k, higher in (("alpha_reactivity", True), ("alpha_peak_snr", True), ("noise_35_45_uv", False),
                          ("clean_epochs_pct", True), ("drift_uv", False), ("mains_50hz_uv", False)):
            va, vb = a[k], b[k]
            if abs(va - vb) <= 0.05 * max(abs(va), abs(vb), 1e-9):
                verdict = "about equal"
            else:
                verdict = (labels[0] if (va > vb) == higher else labels[1]) + " better"
            print(f"  {k:18s} {labels[0]} {va}  vs  {labels[1]} {vb}  → {verdict}")
    plot(res, labels, log, t, ys, prefix + ".png", datetime.fromtimestamp(log[0]["start"]))
    with open(prefix + "_summary.json", "w") as fh:
        json.dump({lab: m for (m, _), lab in zip(res, labels)}, fh, indent=2)
    print(f"\nSaved {prefix}.png and _summary.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", type=int, nargs=2, default=[1, 2])
    ap.add_argument("--labels", nargs=2, default=["Dry (O1)", "Gold (O2)"])
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--block", type=int, default=30, help="seconds per eyes-open / eyes-closed block")
    ap.add_argument("--analyze", help="re-analyse a saved run (.json)")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    if args.analyze:
        with open(args.analyze) as fh:
            meta = json.load(fh)
        prefix = args.analyze.replace(".json", "")
    else:
        log = run(protocol(args.rounds, args.block))
        meta = {"phases": log, "labels": args.labels, "channels": args.channels}
        prefix = os.path.join(OUT_DIR, f"eeg_{datetime.now():%Y%m%d_%H%M%S}")
        with open(prefix + ".json", "w") as fh:
            json.dump(meta, fh, indent=2)
        print("Waiting 3 s for the GUI to flush its recording file...")
        time.sleep(3)
    analyse(meta, prefix)


if __name__ == "__main__":
    main()
