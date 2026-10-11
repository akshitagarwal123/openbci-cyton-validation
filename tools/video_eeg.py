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
    banners = []  # (word, wall start, wall end)
    if args.test:
        tm = json.load(open(args.test))
        test = os.path.basename(args.test).split("_")[1]
        title = test.upper() if test == "ssvep" else test.capitalize() + " test"
        if "phases" in tm:  # alpha / ssvep: labelled blocks instead of cues
            ph = tm["phases"]
            a, b = max(a, ph[0]["start"] - 3), min(b, ph[-1]["end"] + 3)
            cues = [p["start"] for p in ph]
            for p in ph:
                if p["phase"] == "Eyes closed":
                    banners.append(("EYES CLOSED", p["start"], p["end"]))
                elif p["phase"] == "Flicker":
                    banners.append((f"{p['target_hz']:g} Hz FLICKER", p["start"], p["end"]))
        else:
            cues = tm.get("cues", [])
            hold = tm.get("hold") or 1.0
            word = {"jaw": "CLENCH", "blinks": "BLINK"}.get(test, "CUE")
            banners = [(word, c, c + hold) for c in cues]
            a, b = max(a, tm["start"] - 3), min(b, tm["end"] + 3)
    d = load_recordings(a - 2, b + 2)
    t = d["t"].values
    traces = []
    for ch in args.channels:
        x = d[f"EXG Channel {ch - 1}"].values.astype(float)
        bb, aa = iirnotch(50, 30, FS)
        traces.append(filtfilt(bb, aa, sosfiltfilt(butter(4, args.band, "bandpass", fs=FS, output="sos"),
                                                   x - np.median(x))))

    track = None
    if args.track:
        ch0 = args.channels[0]
        x0 = d[f"EXG Channel {ch0 - 1}"].values.astype(float)
        bb, aa = iirnotch(50, 30, FS)
        y0 = filtfilt(bb, aa, sosfiltfilt(butter(4, [5, 45], "bandpass", fs=FS, output="sos"), x0 - np.median(x0)))
        win, step = 2 * FS, FS // 4
        times, amps = [], {fq: [] for fq in args.track}
        k = np.arange(win)
        hann = np.hanning(win)
        for i in range(0, len(y0) - win, step):
            seg = y0[i:i + win] * hann
            times.append(t[i + win // 2])
            for fq in args.track:  # amplitude of a sine at exactly fq (single-bin DFT)
                c = np.sum(seg * np.exp(-2j * np.pi * fq * k / FS))
                amps[fq].append(2 * abs(c) / hann.sum())
        track = (np.array(times), {fq: np.array(v) for fq, v in amps.items()}, ch0)

    # one long strip image, scrolled by ffmpeg: PX pixels per second, cursor in the middle
    PX, WIN, H = 120, 8, 720
    span_a, span_b = a - WIN / 2, b + WIN / 2
    width = int((span_b - span_a) * PX)
    fig = plt.figure(figsize=(width / 100, H / 100), dpi=100)
    fig.patch.set_facecolor("#fcfcfb")
    n = len(traces) + (1 if track is not None else 0)
    t_ref = cues[0] if cues else a  # time axis counts from the first cue / phase
    lims, rects = [], []
    for i, (ch, y) in enumerate(zip(args.channels, traces)):
        rect = [0, 1 - (i + 1) / n + 0.08 / n, 1, 0.74 / n]
        rects.append(rect)
        ax = fig.add_axes(rect)
        m = (t >= span_a) & (t <= span_b)
        lim = max(args.min_scale, np.percentile(np.abs(y[m]), 99.5) * 1.15)
        lims.append(lim)
        for v in (-lim, -lim / 2, lim / 2, lim):
            ax.axhline(v, color="#e3e2de", lw=0.8, zorder=0)
        ax.axhline(0, color="#c9c7c1", lw=0.9, zorder=0)
        ax.plot(t[m], y[m], color=COLORS[i % 4], lw=1.4)
        ax.set_ylim(-lim * 1.05, lim * 1.25)
        ax.set_xlim(span_a, span_b)
        for c in cues:
            ax.axvline(c, color="#898781", ls="--", lw=1.2)
        for sec in np.arange(np.ceil(span_a), span_b, 1):
            ax.axvline(sec, color="#ecebe8", lw=0.6, zorder=0)
            w = (t >= sec) & (t < sec + 1)
            if w.sum() > FS // 2:  # signal size in this second, printed above the trace
                ax.text(sec + 0.5, lim * 1.13, f"{np.std(y[w]):.1f}", ha="center", va="center", fontsize=10,
                        color=COLORS[i % 4], alpha=0.9)
            ax.text(sec + 0.04, -lim * 0.98, f"{sec - t_ref:+.0f} s", fontsize=9, color="#898781", va="bottom")
        ax.axis("off")
        ax.set_facecolor("#fcfcfb")
    if track is not None:
        tt, amps, ch0 = track
        rect = [0, 0.08 / n, 1, 0.74 / n]
        ax = fig.add_axes(rect)
        top = max(np.percentile(np.concatenate(list(amps.values())), 99.5) * 1.2, 1.0)
        for j, (fq, v) in enumerate(amps.items()):
            ax.plot(tt, v, color=["#2a9d5c", "#8a5cd6", "#c49a3c"][j % 3], lw=2.2)
        for c in cues:
            ax.axvline(c, color="#898781", ls="--", lw=1.2)
        for v in (top / 4, top / 2, 3 * top / 4):
            ax.axhline(v, color="#e3e2de", lw=0.8, zorder=0)
        ax.set_ylim(0, top)
        ax.set_xlim(span_a, span_b)
        ax.axis("off")
        rects.append(rect)
        lims.append(None)
        track_top = top
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
    for i, (rect, lim) in enumerate(zip(rects, lims)):
        y0, hh = rect[1], rect[3]
        if lim is None:  # tracked-frequency row: 0..top µV
            for v in (0, track_top / 2, track_top):
                axo.plot([0, 0.012], [y0 + v / track_top * hh] * 2, color="#52514e", lw=1)
                axo.text(0.015, y0 + v / track_top * hh, f"{v:.1f} µV" if v else "0", fontsize=10, va="center",
                         color="#52514e", bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
            labels = "   ".join(f"{fq:g} Hz" for fq in args.track)
            axo.text(0.12, y0 + hh + 0.035, f"Ch{track[2]} size of the wave at exactly:", fontsize=12, color="#52514e",
                     va="center", fontweight="bold")
            for j, fq in enumerate(args.track):
                axo.text(0.6 + j * 0.16, y0 + hh + 0.035, f"— {fq:g} Hz", fontsize=13, va="center", fontweight="bold",
                         color=["#2a9d5c", "#8a5cd6", "#c49a3c"][j % 3])
            continue
        to_y = lambda v: y0 + (v + lim * 1.05) / (lim * 2.3) * hh
        for v in (-lim, -lim / 2, 0, lim / 2, lim):
            axo.plot([0, 0.012], [to_y(v)] * 2, color="#52514e", lw=1)
            axo.text(0.015, to_y(v), f"{v:+.0f} µV" if v else "0", fontsize=10, va="center", color="#52514e",
                     bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
        axo.text(0.985, to_y(lim * 1.13), "RMS µV / s", fontsize=9, ha="right", va="center", color="#898781",
                 bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
    for i, ch in enumerate(args.channels):
        lab = args.labels[i] if args.labels and i < len(args.labels) else f"ch{ch}"
        axo.text(0.12, 1 - i / n - 0.03, f"Ch{ch} ({lab}), {args.band[0]:g}–{args.band[1]:g} Hz", fontsize=13, va="top", color=COLORS[i % 4],
                 fontweight="bold")
    sync = meta.get("note") or "camera and EEG synced by clock"
    axo.text(0.01, 0.01, f"{title} · {WIN} s window · {sync}", fontsize=11, color="#52514e")
    overlay = args.session + "_overlay.png"
    ov.savefig(overlay, transparent=True)
    plt.close(ov)

    banner_files = []
    for i, w in enumerate(dict.fromkeys(bw for bw, _, _ in banners)):
        bn = plt.figure(figsize=(max(4.2, 0.36 * len(w) + 0.8), 1.1), dpi=100)
        bn.patch.set_alpha(0)
        axb = bn.add_axes([0, 0, 1, 1])
        axb.axis("off")
        axb.add_patch(plt.Rectangle((0, 0), 1, 1, color="#d03b3b", alpha=0.85, transform=axb.transAxes))
        axb.text(0.5, 0.5, w, color="white", fontsize=36, fontweight="bold", ha="center", va="center")
        path = f"{args.session}_banner{i}.png"
        bn.savefig(path, transparent=True)
        plt.close(bn)
        wins = [(x0 - a, x1 - a) for bw, x0, x1 in banners if bw == w and x1 >= a and x0 <= b]
        enable = "+".join(f"between(t,{x0:.2f},{x1:.2f})" for x0, x1 in wins) or "0"
        banner_files.append((path, enable))

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
        regions = args.pixelate or []
        if regions:
            face += f"[f2]split={len(regions)}" + "".join(f"[p{i}]" for i in range(len(regions))) + ";"
            for i, (x, y, w, h, n) in enumerate(regions):
                dst = "face" if i == len(regions) - 1 else f"o{i}"
                face += (f"[p{i}]crop={w}:{h}:{x}:{y},scale={max(1, w // n)}:{max(1, h // n)},"
                         f"scale={w}:{h}:flags=neighbor[q{i}];[{last}][q{i}]overlay={x}:{y}[{dst}];")
                last = dst
        else:
            face += f"[f2]nullsink;[{last}]null[face];"
    else:
        face += "[face];"
    filt = (face +
            f"[1:v]loop=loop=-1:size=1,setpts=N/30/TB,crop={WIN * PX}:{H}:x='{x_expr}':y=0,trim=duration={b - a:.3f}[eeg];" +
            "".join(f"[{'face' if i == 0 else f'fb{i - 1}'}][{3 + i}:v]overlay=30:30:enable='{en}'[fb{i}];"
                    for i, (_, en) in enumerate(banner_files)) +
            f"[eeg][2:v]overlay[eegl];[{f'fb{len(banner_files) - 1}' if banner_files else 'face'}][eegl]hstack=2,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-i", meta["video"], "-loop", "1", "-framerate", "30", "-i", strip,
                    "-i", overlay, *[x for path, _ in banner_files for x in ("-i", path)], "-filter_complex", filt, "-map", "[v]", "-map", "0:a?",
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
    b.add_argument("--track", type=float, nargs="+", help="extra row: live amplitude at these frequencies (SSVEP), first channel")
    b.add_argument("--min-scale", type=float, default=150, help="smallest y-range in µV")
    b.add_argument("--keep", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                   help="privacy: region kept sharp (camera pixels), everything else blurred")
    b.add_argument("--pixelate", type=int, nargs=5, action="append", metavar=("X", "Y", "W", "H", "BLOCK"),
                   help="privacy: region pixelated with BLOCK-pixel squares (repeatable: eyes, jaw)")
    args = ap.parse_args()
    record(args) if args.cmd == "record" else build(args)


if __name__ == "__main__":
    main()
