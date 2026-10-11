"""
Compare ECG quality of two recordings (e.g. dry vs gold electrode on the channel-1 lead):
share of usable 30-s windows, time at the rail, and beat quality (SNR, beat shape) in a chosen window.

Usage:
    python live_inference/ecg_dry_vs_gold.py \
        --run gold "2026-10-04 14:03:15" "2026-10-04 14:13:15" "2026-10-04 14:03:15" "2026-10-04 14:13:15" \
        --run dry  "2026-10-04 23:26:37" "2026-10-04 23:32:15" "2026-10-04 23:30:37" "2026-10-04 23:31:07" \
        --out ecg_dry_vs_gold_oct4

Each --run is: label, whole-run start, whole-run end, best-window start, best-window end.
"""

import argparse
import json
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from breathing_hr import FS, OUT_DIR, RAIL_UV, load_recordings
from compare_electrodes import quality

COLORS = ["#d4a017", "#2a78d6", "#2a9d5c", "#8a5cd6"]


def ts(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()


def segment(a, b, channel):
    d = load_recordings(ts(a), ts(b))
    return d["t"].values, d[f"EXG Channel {channel - 1}"].values.astype(float)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", nargs=5, action="append", required=True,
                    metavar=("LABEL", "START", "END", "BEST_START", "BEST_END"))
    ap.add_argument("--channel", type=int, default=1)
    ap.add_argument("--out", default="ecg_compare")
    args = ap.parse_args()

    res = {}
    for label, a, b, ba, bb in args.run:
        t, x = segment(a, b, args.channel)
        windows = [quality(x[(t >= s) & (t < s + 30)], t[(t >= s) & (t < s + 30)]) for s in np.arange(t[0], t[-1] - 30, 30)]
        usable = [w for w in windows if w["railed_pct"] < 5 and w.get("kept_pct", 0) >= 90]
        tb, xb = segment(ba, bb, args.channel)
        q = quality(xb, tb)
        res[label] = dict(total_s=round(t[-1] - t[0]), usable_pct=round(100 * len(usable) / max(len(windows), 1)),
                          railed_pct=round(float(np.mean(np.abs(x) > RAIL_UV) * 100), 1), best_window=f"{ba} - {bb}",
                          **{k: q.get(k) for k in ("beats", "kept_pct", "mean_bpm", "r_peak_uv", "noise_uv", "snr",
                                                   "shape_match", "mains_50hz_uv", "drift_uv")},
                          _tmpl=q.get("_template"), _y=(tb, q.get("_y")))
        print(label, {k: v for k, v in res[label].items() if not k.startswith("_")})

    fig, ax = plt.subplots(1, len(res) + 1, figsize=(5 * len(res) + 4, 4),
                           gridspec_kw={"width_ratios": [2] * len(res) + [1.3]})
    for i, (label, r) in enumerate(res.items()):
        tb, y = r["_y"]
        if y is None:
            continue
        t0 = tb[0] + min(120, max(0, tb[-1] - tb[0] - 8)) if r["total_s"] > 60 else tb[0]
        m = (tb >= t0) & (tb < t0 + 8)
        ax[i].plot(tb[m] - t0, y[m], color=COLORS[i % 4], lw=1)
        ax[i].set_title(f"{label} electrode ECG (8 s)\n{r['mean_bpm']} bpm, SNR {r['snr']}, usable {r['usable_pct']}% of run",
                        loc="left", fontsize=10)
        ax[i].set(xlabel="s", ylabel="µV")
        tt = (np.arange(len(r["_tmpl"])) - int(0.3 * FS)) / FS * 1000
        ax[-1].plot(tt, r["_tmpl"], color=COLORS[i % 4], label=label)
    ax[-1].set_title("Average heartbeat shape", loc="left", fontsize=10)
    ax[-1].set_xlabel("ms from R")
    ax[-1].legend()
    for a_ in ax:
        a_.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    prefix = os.path.join(OUT_DIR, args.out)
    plt.savefig(prefix + ".png", dpi=110)
    json.dump({k: {a: b for a, b in v.items() if not a.startswith("_")} for k, v in res.items()},
              open(prefix + "_result.json", "w"), indent=1, default=float)
    print("Saved", prefix + ".png")


if __name__ == "__main__":
    main()
