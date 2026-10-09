"""
Record the webcam while the OpenBCI GUI records EEG, then build a side-by-side
video: face on the left, scrolling EEG traces on the right, exactly in sync.

Sync: ffmpeg stamps every camera frame with the wall clock
(-use_wallclock_as_timestamps), and the first frame's clock time is logged, so
the video lines up with the GUI's timestamps without guessing camera delays.

Usage:
    python live_inference/video_eeg.py record --seconds 90          # start this, then run a test
    python live_inference/video_eeg.py build runs/video_<stamp>      # make the side-by-side mp4
        [--channels 1 2] [--labels dry gold] [--test runs/validate_blinks_<stamp>.json]
"""

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch, sosfiltfilt

from breathing_hr import FS, OUT_DIR, load_recordings

COLORS = ["#2a78d6", "#eb6834", "#2a9d5c", "#8a5cd6"]


def record(args):
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, f"video_{datetime.now():%Y%m%d_%H%M%S}")
    log = open(base + "_ffmpeg.log", "w")
    print(f"Recording {args.seconds:.0f} s of webcam to {base}.mov — start your test now")
    subprocess.run(["ffmpeg", "-hide_banner", "-use_wallclock_as_timestamps", "1", "-f", "avfoundation",
                    "-framerate", "30", "-pixel_format", "nv12", "-video_size", "1280x720", "-i", "0:0",
                    "-copyts", "-vf", "showinfo,setpts=PTS-STARTPTS", "-af", "asetpts=PTS-STARTPTS",
                    "-frames:v", str(int(args.seconds * 30)), "-shortest", "-c:v", "h264_videotoolbox", "-b:v", "4M",
                    "-c:a", "aac", "-y", base + ".mov"], stderr=log)
    log.close()
    first = None
    for line in open(base + "_ffmpeg.log"):
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            first = float(m.group(1))
            break
    if not first or first < 1e9:
        raise SystemExit("Could not read the camera's clock time from the ffmpeg log")
    json.dump({"video": base + ".mov", "first_frame_wall": first}, open(base + ".json", "w"), indent=1)
    print(f"Saved {base}.mov (first frame at {datetime.fromtimestamp(first):%H:%M:%S.%f})")


def build(args):
    meta = json.load(open(args.session + ".json"))
    t0_video = meta["first_frame_wall"]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "csv=p=0", meta["video"]]).strip())
    cues, title = [], "EEG"
    a, b = t0_video, t0_video + dur
    if args.test:
        tm = json.load(open(args.test))
        cues = tm.get("cues", [])
        a, b = max(a, tm["start"] - 3), min(b, tm["end"] + 3)
        title = os.path.basename(args.test).split("_")[1].capitalize() + " test"
    d = load_recordings(a - 2, b + 2)
    t = d["t"].values
    traces = []
    for ch in args.channels:
        x = d[f"EXG Channel {ch - 1}"].values.astype(float)
        bb, aa = iirnotch(50, 30, FS)
        traces.append(filtfilt(bb, aa, sosfiltfilt(butter(4, args.band, "bandpass", fs=FS, output="sos"),
                                                   x - np.median(x))))

    # one long strip image, scrolled by ffmpeg: PX pixels per second, cursor in the middle
    PX, WIN, H = 120, 8, 720
    span_a, span_b = a - WIN / 2, b + WIN / 2
    width = int((span_b - span_a) * PX)
    fig = plt.figure(figsize=(width / 100, H / 100), dpi=100)
    fig.patch.set_facecolor("#fcfcfb")
    n = len(traces)
    for i, (ch, y) in enumerate(zip(args.channels, traces)):
        ax = fig.add_axes([0, 1 - (i + 1) / n + 0.06 / n, 1, 0.82 / n])
        m = (t >= span_a) & (t <= span_b)
        ax.plot(t[m], y[m], color=COLORS[i % 4], lw=1.4)
        lim = max(args.min_scale, np.percentile(np.abs(y[m]), 99.5) * 1.15)
        ax.set_ylim(-lim, lim)
        ax.set_xlim(span_a, span_b)
        for c in cues:
            ax.axvline(c, color="#898781", ls="--", lw=1.2)
            ax.text(c + 0.05, lim * 0.82, "cue", color="#52514e", fontsize=11)
        for s in np.arange(np.ceil(span_a), span_b, 1):
            ax.axvline(s, color="#ecebe8", lw=0.6, zorder=0)
        ax.axis("off")
        ax.set_facecolor("#fcfcfb")
    strip = args.session + "_strip.png"
    fig.savefig(strip, facecolor=fig.get_facecolor())
    plt.close(fig)

    # static overlay: labels, scale bar and the "now" cursor for a WIN-second window
    ov = plt.figure(figsize=(WIN * PX / 100, H / 100), dpi=100)
    ov.patch.set_alpha(0)
    axo = ov.add_axes([0, 0, 1, 1])
    axo.set_xlim(0, 1)
    axo.set_ylim(0, 1)
    axo.axis("off")
    axo.axvline(0.5, color="#d03b3b", lw=2)
    axo.text(0.51, 0.975, "now", color="#d03b3b", fontsize=13, va="top")
    for i, ch in enumerate(args.channels):
        lab = args.labels[i] if args.labels and i < len(args.labels) else f"ch{ch}"
        axo.text(0.01, 1 - i / n - 0.03, f"Ch{ch} ({lab}), {args.band[0]:g}–{args.band[1]:g} Hz", fontsize=13, va="top", color=COLORS[i % 4],
                 fontweight="bold")
    sync = meta.get("note") or "camera and EEG synced by clock"
    axo.text(0.01, 0.01, f"{title} · {WIN} s window · {sync}", fontsize=11, color="#52514e")
    overlay = args.session + "_overlay.png"
    ov.savefig(overlay, transparent=True)
    plt.close(ov)

    out = args.session + "_side_by_side.mp4"
    start_in_video = a - t0_video
    x_expr = f"(t+{a - span_a - WIN / 2:.3f})*{PX}"
    face = f"[0:v]trim=start={start_in_video:.3f}:duration={b - a:.3f},setpts=PTS-STARTPTS,scale=-2:{H}"
    if args.keep or args.pixelate:
        # privacy: blur everything, keep the electrode area sharp, pixelate the eyes (blinks stay visible)
        face += ",split=3[f0][f1][f2];[f0]boxblur=28:6[bg];"
        last = "bg"
        if args.keep:
            x, y, w, h = args.keep
            face += f"[f1]crop={w}:{h}:{x}:{y}[keep];[{last}][keep]overlay={x}:{y}[k1];"
            last = "k1"
        else:
            face += "[f1]nullsink;"
        if args.pixelate:
            x, y, w, h, n = args.pixelate
            face += (f"[f2]crop={w}:{h}:{x}:{y},scale={max(1, w // n)}:{max(1, h // n)},"
                     f"scale={w}:{h}:flags=neighbor[pix];[{last}][pix]overlay={x}:{y}[face];")
        else:
            face += f"[f2]nullsink;[{last}]null[face];"
    else:
        face += "[face];"
    filt = (face +
            f"[1:v]loop=loop=-1:size=1,setpts=N/30/TB,crop={WIN * PX}:{H}:x='{x_expr}':y=0,trim=duration={b - a:.3f}[eeg];"
            f"[eeg][2:v]overlay[eegl];[face][eegl]hstack=2,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-i", meta["video"], "-loop", "1", "-framerate", "30", "-i", strip,
                    "-i", overlay, "-filter_complex", filt, "-map", "[v]", "-map", "0:a?",
                    "-af", f"atrim=start={start_in_video:.3f}:duration={b - a:.3f},asetpts=PTS-STARTPTS",
                    "-r", "30", "-c:v", "h264_videotoolbox", "-b:v", "6M", "-c:a", "aac", "-y", out], check=True)
    print(f"Saved {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--seconds", type=float, default=90)
    b = sub.add_parser("build")
    b.add_argument("session", help="runs/video_<stamp> (without extension)")
    b.add_argument("--channels", type=int, nargs="+", default=[1, 2])
    b.add_argument("--labels", nargs="+", default=["dry", "gold"])
    b.add_argument("--test", help="validate_*.json of the test run, for cue markers and trimming")
    b.add_argument("--band", type=float, nargs=2, default=[0.5, 15], help="EEG filter band (jaw: 20 45)")
    b.add_argument("--min-scale", type=float, default=150, help="smallest y-range in µV")
    b.add_argument("--keep", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                   help="privacy: region kept sharp (camera pixels), everything else blurred")
    b.add_argument("--pixelate", type=int, nargs=5, metavar=("X", "Y", "W", "H", "BLOCK"),
                   help="privacy: region pixelated with BLOCK-pixel squares (e.g. the eyes)")
    args = ap.parse_args()
    record(args) if args.cmd == "record" else build(args)


if __name__ == "__main__":
    main()
