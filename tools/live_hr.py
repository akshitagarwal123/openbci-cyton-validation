"""
Live heart-rate monitor (ECG on one channel) in a window.

Reads the OpenBCI GUI's own recording file as it grows (no LSL needed, and it
follows the GUI when a new session/file starts). Shows:
  - big instant heart rate (last beat) and 5-beat average
  - the last 8 s of ECG with detected beats
  - heart-rate trend over the last 2 minutes

Setup: SRB on one wrist, channel electrode on the OTHER wrist, BIAS on skin,
GUI streaming.

Usage:
    python live_inference/live_hr.py              # channel 1
    python live_inference/live_hr.py --channel 2
"""

import argparse
import glob
import os
import time
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, iirnotch, sosfiltfilt, filtfilt

from breathing_hr import FS, RAIL_UV, RECORDINGS, clean_rr, detect_beats

BUFFER_S = 20
STRIP_S = 8
TREND_S = 120
INK, INK2, BLUE, ORANGE, MUTED = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834", "#898781"


class RecordingTail:
    """Follows the newest GUI RAW file and returns new (epoch_time, value) samples."""

    def __init__(self, channel):
        self.col = channel  # column 0 is Sample Index, EXG Channel 0 is column 1
        self.path, self.fh, self.partial = None, None, ""
        self.utc_offset = datetime.now().astimezone().utcoffset().total_seconds()

    def _newest(self):
        files = glob.glob(os.path.join(RECORDINGS, "*", "OpenBCI-RAW-*.txt"))
        return max(files, key=os.path.getmtime) if files else None

    def read(self):
        newest = self._newest()
        if newest != self.path:
            if self.fh:
                self.fh.close()
            self.path = newest
            self.fh = open(newest, "r") if newest else None
            if self.fh:
                self.fh.seek(max(0, os.path.getsize(newest) - 300 * FS * BUFFER_S))  # start ~20 s back
                self.fh.readline()  # drop the partial first line
            self.partial = ""
        if not self.fh:
            return [], []
        chunk = self.partial + self.fh.read()
        lines = chunk.split("\n")
        self.partial = lines.pop()  # last line may be incomplete
        ts, vals = [], []
        for line in lines:
            if not line or line[0] in "%S":
                continue
            parts = line.split(",")
            try:
                v = float(parts[self.col])
                t = datetime.strptime(parts[-1].strip(), "%Y-%m-%d %H:%M:%S.%f").timestamp()
            except (ValueError, IndexError):
                continue
            ts.append(t)
            vals.append(v)
        return ts, vals


def ecg_view(x):
    b, a = iirnotch(50, 30, FS)
    return filtfilt(b, a, sosfiltfilt(butter(3, [0.7, 40], "bandpass", fs=FS, output="sos"), x - np.median(x)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", type=int, default=1)
    args = ap.parse_args()

    tail = RecordingTail(args.channel)
    t_buf, x_buf = deque(maxlen=FS * BUFFER_S), deque(maxlen=FS * BUFFER_S)
    beats = {}  # rounded beat time -> beat time (accumulates for the trend)

    plt.ion()
    fig = plt.figure(figsize=(11, 7))
    fig.patch.set_facecolor("#fcfcfb")
    gs = fig.add_gridspec(3, 1, height_ratios=[0.9, 1.3, 1.1], hspace=0.45)
    ax_txt, ax_ecg, ax_hr = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
    for ax in (ax_ecg, ax_hr):
        ax.set_facecolor("#fcfcfb")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=INK2)
        ax.grid(axis="y", color="#ecebe8")
    ax_txt.axis("off")
    big = ax_txt.text(0.0, 0.55, "-- bpm", fontsize=54, color=INK, va="center", fontweight="bold")
    sub = ax_txt.text(0.0, 0.0, "waiting for data…", fontsize=13, color=INK2, va="center")
    status = ax_txt.text(1.0, 0.55, "", fontsize=12, color=INK2, va="center", ha="right")
    ecg_line, = ax_ecg.plot([], [], color=BLUE, lw=1.1)
    beat_dots, = ax_ecg.plot([], [], "o", ms=7, mfc="none", mec=ORANGE, mew=1.8)
    ax_ecg.set_title(f"Channel {args.channel} ECG — last {STRIP_S} s", loc="left", color=INK, fontsize=11)
    ax_ecg.set_xlim(-STRIP_S, 0)
    ax_ecg.set_xlabel("seconds ago", color=INK2)
    hr_line, = ax_hr.plot([], [], color=BLUE, lw=1.6, marker="o", ms=2.5)
    ax_hr.set_title("Heart rate — last 2 min", loc="left", color=INK, fontsize=11)
    ax_hr.set_xlim(-TREND_S, 0)
    ax_hr.set_xlabel("seconds ago", color=INK2)
    ax_hr.set_ylabel("bpm", color=INK2)
    fig.canvas.manager.set_window_title("Live heart rate")

    print("Live heart rate — close the window or Ctrl+C to stop")
    last_print = 0
    os.makedirs(os.path.join(os.path.dirname(__file__), "runs"), exist_ok=True)
    log_path = os.path.join(os.path.dirname(__file__), "runs", f"live_hr_{datetime.now():%Y%m%d_%H%M%S}.csv")
    log = open(log_path, "w")
    log.write("time,bpm_8s_avg,bpm_instant,beats_kept_pct\n")
    print(f"Logging to {log_path}")
    while plt.fignum_exists(fig.number):
        ts, vals = tail.read()
        t_buf.extend(ts)
        x_buf.extend(vals)
        if len(x_buf) < 4 * FS:
            plt.pause(0.3)
            continue

        t = np.asarray(t_buf)
        x = np.asarray(x_buf)
        now = t[-1]
        railed = np.mean(np.abs(x[-2 * FS:]) > RAIL_UV) > 0.05

        if railed:
            big.set_text("-- bpm")
            sub.set_text("Channel railed — electrode or clips not on skin")
            status.set_text(f"{datetime.fromtimestamp(now):%H:%M:%S}")
            ecg_line.set_data([], [])
            beat_dots.set_data([], [])
        else:
            peaks = detect_beats(x)
            settled = peaks[t[peaks] < now - 0.4]  # ignore beats at the unstable buffer edge
            for bt in t[settled]:
                beats.setdefault(round(bt / 0.05), bt)
            bt_all = np.array(sorted(v for v in beats.values() if v > now - TREND_S - 5))
            beats = {round(v / 0.05): v for v in bt_all}

            y = ecg_view(x)
            strip = t > now - STRIP_S
            ecg_line.set_data(t[strip] - now, y[strip])
            lo, hi = np.percentile(y[strip], [0.5, 99.5])
            ax_ecg.set_ylim(lo * 1.3 - 10, hi * 1.3 + 10)
            vis = settled[t[settled] > now - STRIP_S]
            beat_dots.set_data(t[vis] - now, y[vis])

            if len(bt_all) >= 3:
                t_rr, rr = clean_rr(bt_all)
                if len(rr):
                    hr = 60 / rr
                    inst = hr[-1]
                    recent = t_rr > now - 8                 # oximeters average over roughly 4-8 s
                    avg8 = np.mean(hr[recent]) if recent.any() else np.mean(hr[-5:])
                    raw_recent = np.sum(bt_all > now - 15) - 1
                    kept = 100 * np.sum(t_rr > now - 15) / max(raw_recent, 1)
                    quality = "GOOD" if kept >= 90 else "fair" if kept >= 70 else "POOR - press electrode / keep still"
                    fresh = now - t_rr[-1] < 3
                    big.set_text(f"{avg8:.0f} bpm" if fresh else "-- bpm")
                    big.set_color(INK if kept >= 70 else ORANGE)
                    sub.set_text(f"8-s average (compare with oximeter)   ·   instant {inst:.0f} bpm   ·   "
                                 f"signal {quality} ({min(kept, 100):.0f}% clean beats)")
                    if time.time() - last_print > 1:
                        log.write(f"{datetime.fromtimestamp(now):%H:%M:%S},{avg8:.1f},{inst:.1f},{min(kept, 100):.0f}\n")
                        log.flush()
                        print(f"{datetime.fromtimestamp(now):%H:%M:%S}  {avg8:5.0f} bpm (8-s avg)  instant {inst:5.0f}  "
                              f"clean {min(kept, 100):3.0f}%", flush=True)
                        last_print = time.time()
                    hr_line.set_data(t_rr - now, hr)
                    ax_hr.set_ylim(max(30, hr.min() - 8), min(200, hr.max() + 8))
            else:
                sub.set_text("looking for heartbeats…")
            status.set_text(f"{datetime.fromtimestamp(now):%H:%M:%S}\n{os.path.basename(tail.path)}")
        fig.canvas.draw_idle()
        plt.pause(0.25)


if __name__ == "__main__":
    main()
