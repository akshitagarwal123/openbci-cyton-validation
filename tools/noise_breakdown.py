"""
Which frequencies make up the noise currently drawn in the OpenBCI GUI?

Captures the GUI's LSL streams (TimeSeriesFilt + TimeSeriesRaw, see
gui_monitor.py for setup), applies the given bandpass/notch to the RAW stream
(the GUI's own filtered stream adds broadband artifacts that are not in the
signal), then plots:
  1. amplitude spectrum of the raw and filtered signal per channel
  2. how much each frequency band contributes to the filtered noise

Usage:
    python live_inference/noise_breakdown.py --seconds 20 --channels 1 2 --band 1 50 --notch off
"""

import argparse
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pylsl import StreamInlet, resolve_streams
from scipy.signal import butter, sosfilt, welch

from gui_monitor import FS, classify

BANDS = [("1–4\ndrift/motion", 1, 4), ("4–8\ntheta", 4, 8), ("8–13\nmu/alpha", 8, 13),
         ("13–30\nbeta", 13, 30), ("30–45\ngamma/EMG", 30, 45), ("45–55\nmains", 45, 55)]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # fixed categorical order
FLOOR = "#898781"
INK, INK2 = "#0b0b0b", "#52514e"


def capture(seconds):
    inlets = [StreamInlet(s, max_buflen=60) for s in resolve_streams(wait_time=5) if s.channel_count() >= 8]
    if len(inlets) < 2:
        raise SystemExit("Need both TimeSeriesFilt and TimeSeriesRaw LSL streams from the GUI.")
    buf = {i: [] for i in range(len(inlets))}
    end = time.time() + seconds
    while time.time() < end:
        for i, inlet in enumerate(inlets):
            chunk, _ = inlet.pull_chunk(timeout=0.0)
            if chunk:
                buf[i].extend(chunk)
        time.sleep(0.05)
    buf = {i: np.asarray(v)[:, :8] for i, v in buf.items() if len(v)}
    raw_i, filt_i = classify(buf)
    n = min(len(buf[raw_i]), len(buf[filt_i]))
    return buf[raw_i][-n:], buf[filt_i][-n:]


def spectrum(x):
    f, p = welch(x - x.mean(), FS, nperseg=min(500, len(x)))
    return f, p


def band_rms(f, p, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(p[m].sum() * (f[1] - f[0])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20)
    ap.add_argument("--channels", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--band", type=float, nargs=2, default=[1, 50], help="bandpass to match the GUI")
    ap.add_argument("--notch", choices=["on", "off"], default="off")
    ap.add_argument("--out", default="noise_breakdown.png")
    args = ap.parse_args()

    print(f"Capturing {args.seconds:.0f}s from the GUI...")
    raw, _ = capture(args.seconds)
    stamp = time.strftime("%H:%M:%S")
    sos = butter(4, args.band, "bandpass", fs=FS, output="sos")
    if args.notch == "on":
        sos = np.vstack([sos, butter(4, [48, 52], "bandstop", fs=FS, output="sos")])
    filt = np.array([sosfilt(sos, raw[:, c] - raw[:, c].mean()) for c in range(8)]).T[FS:]
    raw = raw[FS:]
    filt_desc = f"filter {args.band[0]:g}–{args.band[1]:g} Hz, notch 50 Hz {args.notch.upper()}"

    chans = [c - 1 for c in args.channels]
    others = [c for c in range(8) if c not in chans]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9), gridspec_kw={"height_ratios": [1.1, 1]})
    fig.patch.set_facecolor("#fcfcfb")
    for ax in (ax1, ax2):
        ax.set_facecolor("#fcfcfb")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color("#c9c8c3")
        ax.tick_params(colors=INK2, labelsize=10)

    # 1. Spectrum of what is on screen
    floor_p = np.median([spectrum(filt[:, c])[1] for c in others], axis=0)
    f, _ = spectrum(filt[:, 0])
    df = f[1] - f[0]
    m = f <= 70
    for k, c in enumerate(chans):
        _, pr = spectrum(raw[:, c])
        ax1.plot(f[m], np.sqrt(pr[m] * df), color=SERIES[k], lw=1, alpha=0.45, label=f"Ch {c + 1} raw")
        _, p = spectrum(filt[:, c])
        ax1.plot(f[m], np.sqrt(p[m] * df), color=SERIES[k], lw=2, label=f"Ch {c + 1} after filter")
    ax1.plot(f[m], np.sqrt(floor_p[m] * df), color=FLOOR, lw=2, ls="--", label="Ch 3–8 median (board floor)")
    ax1.set_yscale("log")
    ax1.set_xlim(0, 70)
    ax1.set_xlabel("Frequency (Hz)", color=INK2)
    ax1.set_ylabel("Amplitude per 0.5 Hz bin (µV)", color=INK2)
    ax1.set_title("Amplitude by frequency — raw (thin) vs after filter (thick)", loc="left", color=INK, fontsize=13)
    ax1.grid(axis="y", color="#ecebe8", lw=0.8)
    ax1.legend(frameon=False, labelcolor=INK2, loc="upper right")

    # 2. Band contribution to on-screen noise
    x = np.arange(len(BANDS))
    width = 0.8 / (len(chans) + 1)
    rows = []
    for k, c in enumerate(chans + ["floor"]):
        p = floor_p if c == "floor" else spectrum(filt[:, c])[1]
        vals = [band_rms(f, p, lo, hi) for _, lo, hi in BANDS]
        total = np.sqrt(sum(v ** 2 for v in vals))
        name = "Ch 3–8 floor" if c == "floor" else f"Ch {c + 1}"
        rows.append((name, vals, total))
        color = FLOOR if c == "floor" else SERIES[k]
        bars = ax2.bar(x + (k - len(chans) / 2) * width, vals, width * 0.92, color=color, label=name)
        if c != "floor":
            for b, v in zip(bars, vals):
                share = 100 * v ** 2 / total ** 2 if total else 0
                if share >= 10:
                    ax2.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{share:.0f}%", ha="center",
                             fontsize=9, color=INK2)
    ax2.set_yscale("log")
    ax2.set_xticks(x, [b[0] for b in BANDS])
    ax2.set_ylabel("RMS contribution (µV)", color=INK2)
    ax2.set_title("Which band the filtered noise comes from  (% = share of channel's noise power)",
                  loc="left", color=INK, fontsize=13)
    ax2.grid(axis="y", color="#ecebe8", lw=0.8)
    ax2.legend(frameon=False, labelcolor=INK2, loc="upper left")

    fig.suptitle(f"OpenBCI live noise breakdown — {stamp}, {len(filt) / FS:.0f}s — {filt_desc}",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(args.out, dpi=130)

    print(f"\n{stamp}  {filt_desc}")
    print("channel        " + "".join(f"{b[0].split(chr(10))[0]:>9}" for b in BANDS) + "    total")
    for name, vals, total in rows:
        print(f"{name:14s} " + "".join(f"{v:9.1f}" for v in vals) + f" {total:8.1f} µV")
    for name, vals, total in rows[:-1]:
        top = max(range(len(vals)), key=lambda i: vals[i])
        print(f"{name}: biggest contributor {BANDS[top][0].replace(chr(10), ' ')} "
              f"({100 * vals[top] ** 2 / total ** 2:.0f}% of noise power)")
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
