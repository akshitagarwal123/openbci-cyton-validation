"""
Compare the ECG heart rate (live_hr.py dashboard log) with pulse-oximeter readings
taken from a phone video, and plot both.

Readings are given as "seconds_from_start:bpm" pairs, read off the video frames.

Usage:
    python live_inference/ecg_vs_oximeter.py --start "2026-10-05 00:14:34" \
        --log runs/live_hr_20261005_001213.csv --label gold \
        --readings 0:78 2:80 4:80 8:80 12:84 16:85 20:85 24:88 28:89 30:88 32:85 34:85 36:87 38:87 50:85 52:85 54:85

Pass rule: mean absolute difference <= 3 bpm.
"""

import argparse
import json
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from breathing_hr import OUT_DIR


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", required=True, help="wall-clock time of video second 0, 'YYYY-MM-DD HH:MM:SS'")
    ap.add_argument("--log", required=True, help="live_hr CSV (time,bpm_8s_avg,...)")
    ap.add_argument("--readings", nargs="+", required=True, help="seconds:bpm pairs from the oximeter video")
    ap.add_argument("--label", default="ECG")
    args = ap.parse_args()

    t0 = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    oxi = {int(s): float(b) for s, b in (r.split(":") for r in args.readings)}
    log = pd.read_csv(args.log).drop_duplicates("time")
    day = t0.strftime("%Y-%m-%d")
    log["s"] = [(datetime.strptime(f"{day} {v}", "%Y-%m-%d %H:%M:%S") - t0).total_seconds() for v in log.time]
    ecg = dict(zip(log.s.round().astype(int), log.bpm_8s_avg))
    pairs = [(s, o, ecg[s]) for s, o in sorted(oxi.items()) if s in ecg]
    if not pairs:
        raise SystemExit("No overlapping seconds between the readings and the ECG log")
    diff = np.array([e - o for _, o, e in pairs])
    res = dict(start=args.start, electrode=args.label, readings_compared=len(pairs),
               oximeter_mean=round(float(np.mean([p[1] for p in pairs])), 1),
               ecg_8s_avg_mean=round(float(np.mean([p[2] for p in pairs])), 1),
               mean_abs_diff_bpm=round(float(np.mean(np.abs(diff))), 1),
               max_abs_diff_bpm=round(float(np.max(np.abs(diff))), 1),
               pass_rule="mean abs diff <= 3 bpm")
    res["result"] = "PASS" if res["mean_abs_diff_bpm"] <= 3 else "FAIL"
    print(json.dumps(res, indent=1))

    stamp = t0.strftime("%Y%m%d_%H%M%S")
    prefix = os.path.join(OUT_DIR, f"ecg_{args.label}_vs_oximeter_{stamp}")
    json.dump(res, open(prefix + "_result.json", "w"), indent=1)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot([p[0] for p in pairs], [p[1] for p in pairs], "s", color="#d4a017", label="pulse oximeter (phone video)")
    span = log[(log.s >= -2) & (log.s <= max(oxi) + 4)]
    ax.plot(span.s, span.bpm_8s_avg, "-", color="#2a78d6", label=f"Cyton ECG, {args.label} (8-s average)")
    lo, hi = min(min(oxi.values()), span.bpm_8s_avg.min()), max(max(oxi.values()), span.bpm_8s_avg.max())
    ax.set_ylim(lo - 8, hi + 8)
    ax.set_xlabel(f"seconds from {t0:%H:%M:%S}")
    ax.set_ylabel("bpm")
    ax.set_title(f"{args.label} vs pulse oximeter: mean difference {res['mean_abs_diff_bpm']} bpm ({res['result']})",
                 loc="left", fontsize=11)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(prefix + ".png", dpi=110)
    print("Saved", prefix + ".png")


if __name__ == "__main__":
    main()
