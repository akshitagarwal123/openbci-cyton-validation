"""
Validate that the Cyton board captures correct, good-quality, physiologically valid signals.

Works through the OpenBCI GUI: keep it open and streaming; each test speaks its
instructions, logs the phase times, then analyses that window from the GUI's
recording file and prints PASS/FAIL against fixed criteria. Channels 1 and 2.

Order (≈30 min):
    integrity   data timing / dropped packets (no action)
    hardware    electrodes OFF; switch GUI Input Type: Shorted -> Test Signal -> Normal
    extshort    electrode + SRB + BIAS clipped onto one piece of metal, hands off (analyses last 20 s)
    ecg         SRB left wrist, BIAS forearm, ch1 + ch2 on right wrist, pulse oximeter on a finger
    blinks      Fp1 (ch1) / Fp2 (ch2), ear clips; blink on cue
    jaw         same placement; clench on cue
    alpha       O1 (ch1) / O2 (ch2); eyes open / closed
    ssvep       same placement; watch a 12 Hz and 15 Hz full-screen flicker
    report      summary of the latest run of every test

Usage:
    python live_inference/validate_board.py hardware
    python live_inference/validate_board.py hardware --recent 20     # analyse the last 20 s only
    python live_inference/validate_board.py ecg
    python live_inference/validate_board.py ecg --analyze runs/validate_ecg_<stamp>.json --oximeter 82 84 83 85
    python live_inference/validate_board.py report
"""

import argparse
import glob
import json
import os
import random
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, iirnotch, medfilt, sosfiltfilt, welch

from breathing_hr import FS, OUT_DIR, RAIL_UV, load_recordings, say
from compare_electrodes import quality
from eeg_compare import alpha_envelope
from eeg_compare import metrics as eeg_metrics
from eeg_compare import run as run_steps

CHANNELS = [1, 2]
LABELS = {1: "Ch1 (dry)", 2: "Ch2 (gold)"}
COLORS = {1: "#2a78d6", 2: "#eb6834"}
INK, INK2, MUTED, GOOD, BAD = "#0b0b0b", "#52514e", "#898781", "#0ca30c", "#d03b3b"
TESTS = ["integrity", "hardware", "extshort", "ecg", "blinks", "jaw", "alpha", "ssvep"]
REPORT_TESTS = ["integrity", "hardware", "testsignal", "extshort", "ecg", "blinks", "jaw", "alpha", "ssvep"]  # testsignal: test_signal_check.py
TESTSIG_HALF_AMPS = {"1x": 1875.0, "2x": 3750.0}           # µV, = ±(4.5 V / 2400) × amp, input-referred
TESTSIG_PERIODS = {"slow": 2 ** 21 / 2.048e6, "fast": 2 ** 20 / 2.048e6}   # 1.024 s, 0.512 s


# ───────────────────────── shared helpers ─────────────────────────

def load(t0, t1, channels=CHANNELS):
    df = load_recordings(t0, t1)
    t = df["t"].to_numpy(float)
    xs = {ch: pd.Series(pd.to_numeric(df[f"EXG Channel {ch - 1}"], errors="coerce").to_numpy(float))
          .interpolate(limit_direction="both").to_numpy() for ch in channels}
    return t, xs, df


def bandpass(x, lo, hi, notch=True):
    y = sosfiltfilt(butter(4, [lo, hi], "bandpass", fs=FS, output="sos"), x - np.median(x))
    if notch:
        b, a = iirnotch(50, 30, FS)
        y = filtfilt(b, a, y)
    return y


def band_rms(x, lo, hi):
    f, p = welch(x - x.mean(), FS, nperseg=min(len(x), 2 * FS))
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(p[m].sum() * (f[1] - f[0])))


class Result:
    def __init__(self, test, window):
        self.test, self.window, self.checks, self.metrics = test, window, [], {}

    def check(self, name, value, ok, criterion, channel=None):
        self.checks.append({"check": name, "channel": channel, "value": value,
                            "criterion": criterion, "pass": bool(ok)})

    @property
    def passed(self):
        return bool(self.checks) and all(c["pass"] for c in self.checks)

    def save(self, prefix):
        out = {"test": self.test, "time": datetime.fromtimestamp(self.window[0]).isoformat(timespec="seconds"),
               "passed": self.passed, "checks": self.checks, "metrics": self.metrics}
        with open(prefix + "_result.json", "w") as fh:
            json.dump(out, fh, indent=2, default=float)
        print(f"\n{self.test.upper()} — {'PASS ✅' if self.passed else 'FAIL ❌'}")
        for c in self.checks:
            ch = LABELS.get(c["channel"], "") if c["channel"] else ""
            v = f"{c['value']:.3g}" if isinstance(c["value"], (int, float)) else str(c["value"])
            print(f"  {'✅' if c['pass'] else '❌'} {c['check']:28s} {ch:11s} {v:>10s}   (need {c['criterion']})")
        print(f"Saved {prefix}_result.json")


def new_prefix(test, tag=""):
    os.makedirs(OUT_DIR, exist_ok=True)
    return os.path.join(OUT_DIR, f"validate_{test}_{datetime.now():%Y%m%d_%H%M%S}" + (f"_{tag}" if tag else ""))


def save_meta(prefix, meta):
    with open(prefix + ".json", "w") as fh:
        json.dump(meta, fh, indent=2)
    print("Waiting 3 s for the GUI to flush its recording file...")
    time.sleep(3)


def countdown(seconds, label=""):
    end = time.time() + seconds
    while (left := end - time.time()) > 0:
        print(f"\r   {label}{left:4.0f}s left   ", end="", flush=True)
        time.sleep(0.2)
    print()


def styled(ax):
    ax.set_facecolor("#fcfcfb")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#ecebe8")
    ax.tick_params(colors=INK2)


def figure(n, title, width=14, height=4.2):
    fig, axs = plt.subplots(1, n, figsize=(width, height))
    fig.patch.set_facecolor("#fcfcfb")
    axs = np.atleast_1d(axs)
    for ax in axs:
        styled(ax)
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=12)
    return fig, axs


def finish(fig, prefix):
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(prefix + ".png", dpi=120)
    print(f"Saved {prefix}.png")


# ───────────────────────── 1. integrity ─────────────────────────

def test_integrity(args):
    t1 = time.time()
    t0 = t1 - args.seconds
    _, _, df = load(t0, t1)
    t = df["t"].to_numpy(float)
    idx = df["Sample Index"].to_numpy(float)
    r = Result("integrity", (t0, t1))
    rate = (len(t) - 1) / (t[-1] - t[0])
    dropped = int((np.diff(idx) % 256 != 1).sum())
    backwards = int((np.diff(t) < 0).sum())
    r.metrics.update(samples=len(t), seconds=round(t[-1] - t[0], 1), rate_hz=round(rate, 2),
                     dropped=dropped, backwards_timestamps=backwards)
    r.check("sample rate (Hz)", round(rate, 2), abs(rate - 250) <= 0.5, "250 ± 0.5")
    r.check("dropped packets (%)", round(100 * dropped / len(t), 3), dropped / len(t) < 0.001, "< 0.1 %")
    r.check("timestamps going backwards", backwards, backwards == 0, "0")
    r.save(new_prefix("integrity"))


# ───────────────────────── 2. hardware ─────────────────────────

def classify_seconds(x):
    """Label each 1 s window: 'square' (test signal), 'flat' (shorted), 'railed' or 'normal'."""
    labels = []
    for i in range(0, len(x) - FS + 1, FS):
        w = x[i:i + FS]
        if np.mean(np.abs(w) > RAIL_UV) > 0.05:
            labels.append("railed")
            continue
        lo, hi = np.percentile(w, [5, 95])
        amp = hi - lo
        near = np.mean((np.abs(w - lo) < 0.08 * amp) | (np.abs(w - hi) < 0.08 * amp)) if amp > 0 else 0
        if amp > 1000 and near > 0.85:
            labels.append("square")
        elif np.ptp(w) < 300 and np.std(bandpass(w, 1, 45)) < 5 and abs(np.median(w)) < 1000:
            labels.append("flat")      # shorted inputs read ~0 µV; floating inputs are quiet but far from 0
        else:
            labels.append("normal")
    return labels


def longest_run(labels, target):
    best, cur, start, best_start = 0, 0, 0, 0
    for i, lab in enumerate(labels + [None]):
        if lab == target:
            if cur == 0:
                start = i
            cur += 1
            if cur > best:
                best, best_start = cur, start
        else:
            cur = 0
    return best_start, best


def analyse_square(x):
    y = medfilt(x, 5)
    mid = (np.percentile(y, 5) + np.percentile(y, 95)) / 2
    hi, lo = np.median(y[y > mid]), np.median(y[y < mid])
    rising = np.where((y[:-1] < mid) & (y[1:] >= mid))[0]
    period = float(np.median(np.diff(rising)) / FS) if len(rising) > 2 else float("nan")
    return (hi - lo) / 2, period


def test_hardware(args):
    if args.recent:
        meta = {"start": time.time() - args.recent, "end": time.time(), "only": args.only}
        prefix = new_prefix("hardware")
        with open(prefix + ".json", "w") as fh:
            json.dump(meta, fh, indent=2)
    elif args.analyze:
        meta = json.load(open(args.analyze))
        prefix = args.analyze[:-5]
    else:
        say("Hardware test. Remove the electrodes from your body.")
        print("\nRemove electrodes from the body. Keep the GUI streaming.")
        steps = [("Shorted", "In the GUI hardware settings, set channels one and two input type to shorted."),
                 ("Test signal", "Now set channels one and two input type to test signal."),
                 ("Normal", "Now set channels one and two back to normal.")]
        start = time.time()
        for name, text in steps:
            print(f"\n▶ {text}")
            say(text)
            countdown(15 if name == "Normal" else 35, f"{name}: ")
        prefix = new_prefix("hardware")
        meta = {"start": start, "end": time.time()}
        save_meta(prefix, meta)

    t, xs, _ = load(meta["start"], meta["end"])
    r = Result("hardware", (meta["start"], meta["end"]))
    fig, axs = figure(3, f"Hardware validation — {datetime.fromtimestamp(meta['start']):%Y-%m-%d %H:%M}")
    squares = {}
    for ch in CHANNELS:
        x = xs[ch]
        labels = classify_seconds(x)
        r.metrics[f"ch{ch}_seconds"] = {k: labels.count(k) for k in set(labels)}

        only = args.only or meta.get("only")
        s, n = longest_run(labels, "flat")
        if only == "testsignal":
            pass
        elif n >= 10:
            seg = x[(s + 1) * FS:(s + n - 1) * FS]
            noise = float(np.std(bandpass(seg, 1, 45, notch=False)))
            mains = band_rms(seg, 48, 52)
            r.check("shorted: noise 1–45 Hz (µV)", round(noise, 2), noise <= 1.5, "≤ 1.5 µV", ch)
            r.check("shorted: 50 Hz (µV)", round(mains, 2), mains <= 1.0, "≤ 1.0 µV", ch)
            r.metrics[f"ch{ch}_shorted_offset_uv"] = round(float(np.median(seg)), 1)
            f, p = welch(seg - seg.mean(), FS, nperseg=2 * FS)
            axs[0].semilogy(f, np.sqrt(p), color=COLORS[ch], lw=1.4, label=LABELS[ch])
        else:
            r.check("shorted segment found", f"{n} s", False, "≥ 10 s of flat signal", ch)

        s, n = longest_run(labels, "square")
        if only == "shorted":
            pass
        elif n >= 10:
            seg = x[(s + 1) * FS:(s + n - 1) * FS]
            half, period = analyse_square(seg)
            squares[ch] = (s, n, seg, half)
            amp_name = min(TESTSIG_HALF_AMPS, key=lambda k: abs(TESTSIG_HALF_AMPS[k] - half))
            per_name = min(TESTSIG_PERIODS, key=lambda k: abs(TESTSIG_PERIODS[k] - period))
            amp_err = 100 * (half - TESTSIG_HALF_AMPS[amp_name]) / TESTSIG_HALF_AMPS[amp_name]
            per_err = 100 * (period - TESTSIG_PERIODS[per_name]) / TESTSIG_PERIODS[per_name]
            r.check(f"test signal amplitude ({amp_name})", round(half, 1), abs(amp_err) <= 2,
                    f"±{TESTSIG_HALF_AMPS[amp_name]:.0f} µV ± 2 %", ch)
            r.check(f"test signal period ({per_name})", round(period, 4), abs(per_err) <= 2,
                    f"{TESTSIG_PERIODS[per_name]:.3f} s ± 2 %", ch)
            tt = np.arange(min(len(seg), 3 * FS)) / FS
            axs[1].plot(tt, seg[:len(tt)] - np.median(seg), color=COLORS[ch], lw=1.4, label=LABELS[ch])
        else:
            r.check("test-signal segment found", f"{n} s", False, "≥ 10 s of square wave", ch)

    if len(squares) == 2:
        (s1, n1, a1, h1), (s2, n2, a2, h2) = squares[1], squares[2]
        lo, hi = max(s1, s2) + 1, min(s1 + n1, s2 + n2) - 1
        if hi - lo >= 5:
            c = float(np.corrcoef(xs[1][lo * FS:hi * FS], xs[2][lo * FS:hi * FS])[0, 1])
            r.check("ch1 vs ch2 waveform correlation", round(c, 5), c > 0.999, "> 0.999")
        mismatch = 100 * abs(h1 - h2) / ((h1 + h2) / 2)
        r.check("ch1 vs ch2 gain match (%)", round(mismatch, 3), mismatch <= 0.5, "≤ 0.5 %")
        axs[2].bar([LABELS[1], LABELS[2]], [h1, h2], color=[COLORS[1], COLORS[2]])
        for ref in TESTSIG_HALF_AMPS.values():
            axs[2].axhline(ref, color=MUTED, ls="--", lw=1)
        axs[2].set_ylim(0, max(h1, h2) * 1.25)
    axs[0].set(title="Shorted inputs: noise spectrum", xlabel="Hz", ylabel="µV/√Hz", xlim=(0, 70))
    axs[1].set(title="Internal test signal (3 s)", xlabel="s", ylabel="µV")
    axs[2].set(title="Test-signal half amplitude vs spec (dashed)", ylabel="µV")
    for ax in axs[:2]:
        ax.legend(frameon=False)
    finish(fig, prefix)
    r.save(prefix)


# ───────────────────────── 2b. external short ─────────────────────────

def test_extshort(args):
    """Electrode + SRB + BIAS clipped onto one piece of metal: channel should read ~0 with tiny noise."""
    if args.analyze:
        meta, prefix = json.load(open(args.analyze)), args.analyze[:-5]
    else:
        seconds = args.recent or 20
        meta = {"start": time.time() - seconds, "end": time.time()}
        prefix = new_prefix("extshort")
        with open(prefix + ".json", "w") as fh:
            json.dump(meta, fh, indent=2)
    chans = args.ext_channels
    t, xs, _ = load(meta["start"], meta["end"], chans)
    r = Result("extshort", (meta["start"], meta["end"]))
    fig, axs = figure(2, f"External short — {datetime.fromtimestamp(meta['start']):%Y-%m-%d %H:%M}", width=13)
    for ch in chans:
        x = xs[ch]
        railed = float(np.mean(np.abs(x) > RAIL_UV) * 100)
        if railed > 5:
            r.check("not railed", f"{railed:.0f}% railed", False, "clips + electrode on the same metal", ch)
            continue
        noise = float(np.std(bandpass(x, 1, 45, notch=False)))
        mains = band_rms(x, 48, 52)
        slow = sosfiltfilt(butter(2, 0.5, "lowpass", fs=FS, output="sos"), x)
        drift = float(np.ptp(slow[FS:-FS]))
        r.metrics[f"ch{ch}_offset_uv"] = round(float(np.median(x)), 1)
        r.check("noise 1–45 Hz (µV)", round(noise, 2), noise <= 1.0, "≤ 1.0 µV", ch)
        r.check("50 Hz hum (µV)", round(mains, 2), mains <= 1.0, "≤ 1.0 µV", ch)
        r.check("offset drift (µV)", round(drift, 1), drift <= 50, "≤ 50 µV over window", ch)
        f, p = welch(x - x.mean(), FS, nperseg=2 * FS)
        axs[0].semilogy(f, np.sqrt(p), color=COLORS.get(ch, MUTED), lw=1.4, label=LABELS.get(ch, f"Ch{ch}"))
        axs[1].plot(t - t[0], x - np.median(x), color=COLORS.get(ch, MUTED), lw=1, label=LABELS.get(ch, f"Ch{ch}"))
    axs[0].set(title="Noise spectrum", xlabel="Hz", ylabel="µV/√Hz", xlim=(0, 70))
    axs[1].set(title="Signal (offset removed)", xlabel="s", ylabel="µV")
    for ax in axs:
        ax.legend(frameon=False)
    finish(fig, prefix)
    r.save(prefix)


# ───────────────────────── 3. ecg ─────────────────────────

def ecg_intervals(tmpl):
    """QRS width (ms) from the template's slope, and T-wave latency (ms after R)."""
    pre = int(0.3 * FS)
    d = np.abs(np.gradient(tmpl))
    win = slice(pre - int(0.1 * FS), pre + int(0.1 * FS))
    dd = d[win]
    above = np.where(dd > 0.1 * dd.max())[0]
    qrs_ms = (above[-1] - above[0]) / FS * 1000 if len(above) else float("nan")
    qrs_end = win.start + (above[-1] if len(above) else int(0.1 * FS))
    tw = slice(max(qrs_end + int(0.05 * FS), pre + int(0.12 * FS)), pre + int(0.45 * FS))
    ti = tw.start + int(np.argmax(np.abs(tmpl[tw])))
    return float(qrs_ms), float((ti - pre) / FS * 1000), float(tmpl[ti])


def test_ecg(args):
    if args.analyze:
        meta = json.load(open(args.analyze))
        prefix = args.analyze[:-5]
    else:
        say("E C G test. Sit still with your hands resting. Keep the pulse oximeter on.")
        print("\nSRB left wrist, BIAS forearm, ch1 + ch2 on right wrist, oximeter on a finger.")
        countdown(5, "starting: ")
        start = time.time()
        cues = []
        for k in range(4):
            countdown(15, f"recording ({k + 1}/4): ")
            cues.append(time.time())
            say("Read the oximeter now.")
            print(f"   >>> note the oximeter reading #{k + 1}")
        say("Done.")
        prefix = new_prefix("ecg", args.tag)
        meta = {"start": start, "end": time.time(), "cues": cues, "channels": args.channels, "tag": args.tag}
        save_meta(prefix, meta)
        print("\nRe-run analysis with your readings, e.g.:\n"
              f"  python live_inference/validate_board.py ecg --analyze {prefix}.json --oximeter 82 84 83 85")

    chans = meta.get("channels") or args.channels
    t, xs, _ = load(meta["start"] + 3, meta["end"], chans)
    r = Result("ecg", (meta["start"], meta["end"]))
    tag = meta.get("tag") or ""
    fig, axs = figure(3, f"ECG validation {('(' + tag + ') ') if tag else ''}— {datetime.fromtimestamp(meta['start']):%Y-%m-%d %H:%M}")
    beat_times = {}
    for ch in chans:
        q = quality(xs[ch], t)
        if "snr" not in q:
            r.check("heartbeat found", f"railed {q['railed_pct']}%", False, "electrode on skin", ch)
            continue
        qrs, t_ms, t_amp = ecg_intervals(q["_template"])
        r.metrics[f"ch{ch}"] = {k: v for k, v in q.items() if not k.startswith("_")} | \
            {"qrs_ms": round(qrs), "t_wave_ms": round(t_ms), "t_wave_uv": round(t_amp)}
        r.check("beats kept (%)", q["kept_pct"], q["kept_pct"] >= 95, "≥ 95 %", ch)
        r.check("SNR (R peak / noise)", q["snr"], q["snr"] >= 10, "≥ 10", ch)
        r.check("QRS width (ms)", round(qrs), 60 <= qrs <= 120, "60–120 ms", ch)
        r.check("T wave after R (ms)", round(t_ms), 150 <= t_ms <= 350, "150–350 ms", ch)
        beat_times[ch] = t[q["_peaks"]]
        tt = (np.arange(len(q["_template"])) - int(0.3 * FS)) / FS * 1000
        axs[0].plot(tt, q["_template"], color=COLORS[ch], lw=2, label=f"{LABELS[ch]} SNR {q['snr']}")
        t_rr, rr = q["_rr"]
        axs[1].plot(t_rr - meta["start"], 60 / rr, color=COLORS[ch], lw=1.2, marker="o", ms=2, label=LABELS[ch])

    if len(beat_times) == 2:
        b1, b2 = (beat_times[c] for c in sorted(beat_times))
        diffs = np.array([np.min(np.abs(b2 - b)) for b in b1])
        matched = diffs < 0.1
        r.check("beats seen on both channels (%)", round(100 * matched.mean(), 1), matched.mean() >= 0.9, "≥ 90 %")
        r.check("ch1 vs ch2 beat timing (ms)", round(float(np.median(diffs[matched]) * 1000), 1),
                np.median(diffs[matched]) <= 0.02, "≤ 20 ms")

    if args.oximeter:
        ox = args.oximeter[:len(meta["cues"])]
        ch = chans[0] if chans[0] in beat_times else next(iter(beat_times), None)
        if ch:
            bt = beat_times[ch]
            ecg_hr = []
            for c in meta["cues"][:len(ox)]:
                b = bt[(bt >= c - 8) & (bt <= c)]
                rr = np.diff(b)
                rr = rr[(rr > 0.33) & (rr < 2)]
                ecg_hr.append(60 / np.median(rr) if len(rr) else np.nan)
            err = np.abs(np.array(ecg_hr) - np.array(ox))
            r.metrics["oximeter"] = {"oximeter_bpm": ox, "ecg_bpm": [round(v, 1) for v in ecg_hr]}
            r.check("ECG vs oximeter (mean |Δ| bpm)", round(float(np.nanmean(err)), 1), np.nanmean(err) <= 3, "≤ 3 bpm")
            axs[1].scatter(np.array(meta["cues"][:len(ox)]) - meta["start"], ox, color=INK, marker="s", s=40,
                           zorder=5, label="oximeter")
    else:
        print("\n(no --oximeter readings given: skipping the independent heart-rate check)")
    axs[0].set(title="Average beat", xlabel="ms from R", ylabel="µV")
    axs[1].set(title="Heart rate", xlabel="s from start", ylabel="bpm")
    axs[0].legend(frameon=False)
    axs[1].legend(frameon=False)
    axs[2].axis("off")
    axs[2].text(0, 0.9, "\n".join(f"{'PASS' if c['pass'] else 'FAIL'}  {c['check']}: {c['value']}"
                                  + (f" ({LABELS[c['channel']]})" if c["channel"] else "") for c in r.checks),
                va="top", fontsize=9, color=INK2, family="monospace")
    finish(fig, prefix)
    r.save(prefix)


# ───────────────────────── 4. blinks / 5. jaw ─────────────────────────

def cued_run(test, intro, cue_word, n, gap, hold=None, release_word=None):
    say(intro)
    print(f"\n{intro}")
    countdown(5, "starting: ")
    start = time.time()
    cues = []
    countdown(4, "baseline: ")
    for k in range(n):
        say(cue_word)
        cues.append(time.time())
        print(f"   cue {k + 1}/{n}: {cue_word}")
        if hold:
            countdown(hold, "hold: ")
            say(release_word)
        countdown(gap() if callable(gap) else gap, "")
    say("Done.")
    prefix = new_prefix(test)
    meta = {"start": start, "end": time.time(), "cues": cues, "hold": hold}
    save_meta(prefix, meta)
    return prefix, meta


def test_blinks(args):
    if args.analyze:
        meta, prefix = json.load(open(args.analyze)), args.analyze[:-5]
    else:
        prefix, meta = cued_run("blinks", "Blink test. Look straight ahead. Blink once each time you hear blink. "
                                "Try not to blink otherwise.", "blink", 10, lambda: random.uniform(3, 6))
    t, xs, _ = load(meta["start"], meta["end"])
    r = Result("blinks", (meta["start"], meta["end"]))
    fig, axs = figure(len(CHANNELS), f"Blink validation — {datetime.fromtimestamp(meta['start']):%Y-%m-%d %H:%M}", width=12)
    avgs = {}
    for ch in CHANNELS:
        y = bandpass(xs[ch], 0.5, 15)
        # spoken cue + reaction time puts the blink ~1-1.5 s after the cue timestamp
        ep_t = np.arange(-int(0.5 * FS), int(2.5 * FS))
        hits, epochs = 0, []
        for c in meta["cues"]:
            i = int(np.searchsorted(t, c))
            if i + ep_t[0] < 0 or i + ep_t[-1] >= len(y):
                continue
            e = y[i + ep_t] - np.median(y[i + ep_t[ep_t < 0]])
            epochs.append(e)
            hits += np.max(np.abs(e[(ep_t >= int(0.3 * FS)) & (ep_t < int(2.2 * FS))])) > 50
        # false positives: blink-sized deflections > 2 s away from any cue
        far = np.ones(len(t), bool)
        for c in meta["cues"]:
            far &= (t < c - 1.0) | (t > c + 3.0)
        far &= t > meta["start"] + 1
        false = 0
        for i in range(0, len(y) - FS, FS):
            if far[i:i + FS].all() and np.ptp(y[i:i + FS]) > 100:
                false += 1
        avg = np.mean(epochs, axis=0) if epochs else np.zeros(len(ep_t))
        avgs[ch] = avg
        r.metrics[f"ch{ch}_blink_peak_uv"] = round(float(np.max(np.abs(avg))), 1)
        r.check("cued blinks detected", f"{hits}/{len(meta['cues'])}", hits >= 9, "≥ 9/10 (> 50 µV)", ch)
        r.check("uncued blink-sized events", false, false <= 2, "≤ 2", ch)
        ax = axs[CHANNELS.index(ch)]
        for e in epochs:
            ax.plot(ep_t / FS, e, color=COLORS[ch], alpha=0.25, lw=0.8)
        ax.plot(ep_t / FS, avg, color=COLORS[ch], lw=2.4)
        ax.set(title=f"{LABELS[ch]}: epochs around each cue", xlabel="s from cue", ylabel="µV")
    if len(avgs) == 2:
        c = float(np.corrcoef(avgs[1], avgs[2])[0, 1])
        r.check("ch1 vs ch2 blink shape correlation", round(c, 3), c > 0.8, "> 0.8")
    finish(fig, prefix)
    r.save(prefix)


def test_jaw(args):
    if args.analyze:
        meta, prefix = json.load(open(args.analyze)), args.analyze[:-5]
    else:
        prefix, meta = cued_run("jaw", "Jaw test. When you hear clench, clench your jaw firmly. Relax on relax.",
                                "clench", 3, 5, hold=3, release_word="relax")
    t, xs, _ = load(meta["start"], meta["end"])
    r = Result("jaw", (meta["start"], meta["end"]))
    fig, axs = figure(1, f"Jaw-clench (muscle) validation — {datetime.fromtimestamp(meta['start']):%Y-%m-%d %H:%M}",
                      width=11)
    hold = meta["hold"] or 3
    for ch in CHANNELS:
        emg = bandpass(xs[ch], 20, 45)
        on = np.zeros(len(t), bool)
        for c in meta["cues"]:
            on |= (t >= c + 0.5) & (t < c + hold)
        rest = ~on
        for c in meta["cues"]:
            rest &= ~((t >= c) & (t < c + hold + 1.0))
        ratio = float(np.mean(emg[on] ** 2) / max(np.mean(emg[rest] ** 2), 1e-9))
        r.metrics[f"ch{ch}_emg_clench_uv"] = round(float(np.std(emg[on])), 1)
        r.metrics[f"ch{ch}_emg_rest_uv"] = round(float(np.std(emg[rest])), 1)
        r.check("20–45 Hz power clench / rest", round(ratio, 1), ratio >= 5, "≥ 5×", ch)
        env = np.sqrt(np.convolve(emg ** 2, np.ones(FS // 4) / (FS // 4), "same"))
        axs[0].plot(t - meta["start"], env, color=COLORS[ch], lw=1.2, label=LABELS[ch])
    for c in meta["cues"]:
        axs[0].axvspan(c - meta["start"], c - meta["start"] + hold, color="#f9d3d3", lw=0)
    axs[0].set(title="Muscle activity (20–45 Hz envelope); shaded = clench", xlabel="s from start", ylabel="µV")
    axs[0].legend(frameon=False)
    finish(fig, prefix)
    r.save(prefix)


# ───────────────────────── 6. alpha ─────────────────────────

def test_alpha(args):
    if args.analyze:
        meta, prefix = json.load(open(args.analyze)), args.analyze[:-5]
    else:
        steps = []
        for _ in range(args.rounds):
            steps += [("Eyes open", 30, "Eyes open. Look at one point and relax."),
                      ("Eyes closed", 30, "Close your eyes and relax.")]
        log = run_steps(steps)
        prefix = new_prefix("alpha")
        meta = {"phases": log, "site": args.site}
        save_meta(prefix, meta)
    log = meta["phases"]
    t, xs, _ = load(log[0]["start"] - 2, log[-1]["end"] + 1)
    r = Result("alpha", (log[0]["start"], log[-1]["end"]))
    need = 1.5 if meta.get("site") == "forehead" else 2.0
    fig, axs = figure(len(CHANNELS) + 1, f"Alpha validation ({meta.get('site', 'occipital')}) — "
                         f"{datetime.fromtimestamp(log[0]['start']):%Y-%m-%d %H:%M}")
    envs = []
    for ch in CHANNELS:
        m, y, spec = eeg_metrics(xs[ch], t, log)
        r.metrics[f"ch{ch}"] = m
        if spec is None:
            r.check("enough clean EEG", f"{m.get('clean_epochs_pct', 0)}%", False, "clean epochs", ch)
            continue
        r.check("alpha eyes-closed / open", m["alpha_reactivity"], m["alpha_reactivity"] >= need, f"≥ {need}×", ch)
        r.check("alpha peak (Hz)", m["alpha_peak_hz"], 8 <= m["alpha_peak_hz"] <= 13, "8–13 Hz", ch)
        r.check("clean epochs (%)", m["clean_epochs_pct"], m["clean_epochs_pct"] >= 70, "≥ 70 %", ch)
        f, p_eo, p_ec = spec
        k = (f >= 1) & (f <= 40)
        ax = axs[CHANNELS.index(ch)]
        ax.semilogy(f[k], np.sqrt(p_eo[k]), color=MUTED, lw=1.6, label="eyes open")
        ax.semilogy(f[k], np.sqrt(p_ec[k]), color=COLORS[ch], lw=2, label="eyes closed")
        ax.axvspan(8, 13, color="#ecebe8", lw=0)
        ax.set(title=f"{LABELS[ch]}: ×{m['alpha_reactivity']}", xlabel="Hz", ylabel="µV/√Hz")
        ax.legend(frameon=False)
        envs.append(alpha_envelope(y))
        axs[-1].plot(t - log[0]["start"], envs[-1], color=COLORS[ch], lw=1.2, label=LABELS[ch])
    if len(envs) == 2:
        c = float(np.corrcoef(envs[0], envs[1])[0, 1])
        r.check("ch1 vs ch2 alpha envelope corr", round(c, 2), c > 0.5, "> 0.5")
    for ph in log:
        if ph["phase"] == "Eyes closed":
            axs[-1].axvspan(ph["start"] - log[0]["start"], ph["end"] - log[0]["start"], color="#cde2fb", lw=0)
    axs[-1].set(title="Alpha over time (blue = eyes closed)", xlabel="s", ylabel="µV")
    axs[-1].legend(frameon=False)
    finish(fig, prefix)
    r.save(prefix)


# ───────────────────────── 7. ssvep ─────────────────────────

def run_flicker(targets, stim_s, rest_s):
    import pygame
    pygame.init()
    size = pygame.display.get_desktop_sizes()[0]
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.SCALED, vsync=1)
    pygame.mouse.set_visible(False)
    w, h = screen.get_size()
    font = pygame.font.SysFont(None, 60)

    def frame(color, text=None):
        screen.fill(color)
        if text:
            img = font.render(text, True, (200, 200, 200))
            screen.blit(img, img.get_rect(center=(w // 2, h // 2)))
        else:
            pygame.draw.line(screen, (255, 0, 0), (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), 4)
            pygame.draw.line(screen, (255, 0, 0), (w // 2, h // 2 - 20), (w // 2, h // 2 + 20), 4)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                raise KeyboardInterrupt

    # measure the real refresh rate
    stamps = []
    for _ in range(120):
        frame((40, 40, 40), "Measuring display…")
        stamps.append(time.perf_counter())
    refresh = 1 / float(np.median(np.diff(stamps)))
    print(f"Display refresh ≈ {refresh:.1f} Hz")
    if abs(refresh - round(refresh)) > 1:
        print("WARNING: refresh rate unstable; flicker frequencies may be inaccurate")

    log = []
    say("S S V E P test. Look at the red cross in the middle. Try not to blink.")
    end = time.time() + 6
    while time.time() < end:
        frame((40, 40, 40), "Look at the centre. Starting soon…")
    for target in targets:
        for kind, dur in (("Rest", rest_s), ("Flicker", stim_s)):
            n = max(2, round(refresh / target))
            delivered = refresh / n
            start, k, flips = time.time(), 0, []
            while time.time() - start < dur:
                if kind == "Rest":
                    frame((40, 40, 40))
                else:
                    frame((255, 255, 255) if (k % n) < (n + 1) // 2 else (0, 0, 0))
                flips.append(time.perf_counter())
                k += 1
            real = 1 / np.median(np.diff(flips)) / n if kind == "Flicker" else None
            log.append({"phase": kind, "target_hz": target, "delivered_hz": round(delivered, 3),
                        "measured_hz": round(float(real), 3) if real else None,
                        "start": start, "end": time.time()})
            print(f"   {kind} {target} Hz done" + (f" (delivered {delivered:.2f} Hz)" if kind == "Flicker" else ""))
    pygame.quit()
    say("Done.")
    return log, refresh


def ssvep_snr(f, p, freq):
    k = np.argmin(np.abs(f - freq))
    neigh = (np.abs(f - freq) >= 0.5) & (np.abs(f - freq) <= 1.5)
    return float(p[k] / np.mean(p[neigh]))


def test_ssvep(args):
    from ssvep_test import _cca_corr, _make_reference
    if args.analyze:
        meta, prefix = json.load(open(args.analyze)), args.analyze[:-5]
    else:
        log, refresh = run_flicker(args.freqs, args.stim, args.rest)
        prefix = new_prefix("ssvep")
        meta = {"phases": log, "refresh_hz": refresh}
        save_meta(prefix, meta)
    log = meta["phases"]
    t, xs, _ = load(log[0]["start"], log[-1]["end"])
    ys = {ch: bandpass(xs[ch], 3, 45) for ch in CHANNELS}
    r = Result("ssvep", (log[0]["start"], log[-1]["end"]))
    stim = [ph for ph in log if ph["phase"] == "Flicker"]
    freqs = [ph["delivered_hz"] for ph in stim]
    fig, axs = figure(len(stim), f"SSVEP validation — {datetime.fromtimestamp(log[0]['start']):%Y-%m-%d %H:%M} "
                                 f"(display {meta['refresh_hz']:.0f} Hz)")
    correct = total = 0
    for ax, ph in zip(axs, stim):
        fq = ph["delivered_hz"]
        rest = next(p for p in log if p["phase"] == "Rest" and p["target_hz"] == ph["target_hz"])
        for ch in CHANNELS:
            seg = ys[ch][(t >= ph["start"] + 2) & (t < ph["end"])]
            rseg = ys[ch][(t >= rest["start"] + 2) & (t < rest["end"])]
            f, p = welch(seg, FS, nperseg=4 * FS)
            _, pr = welch(rseg, FS, nperseg=4 * FS)
            snr = max(ssvep_snr(f, p, fq), ssvep_snr(f, p, 2 * fq))
            snr_rest = max(ssvep_snr(f, pr, fq), ssvep_snr(f, pr, 2 * fq))
            r.check(f"SNR at {fq:.2f} Hz (or 2×) flicker", round(snr, 2), snr >= 2, "≥ 2", ch)
            r.check(f"SNR at {fq:.2f} Hz during rest", round(snr_rest, 2), snr_rest < 2, "< 2 (control)", ch)
            k = (f >= 3) & (f <= 40)
            ax.semilogy(f[k], np.sqrt(p[k]), color=COLORS[ch], lw=1.6, label=f"{LABELS[ch]} flicker")
            ax.semilogy(f[k], np.sqrt(pr[k]), color=COLORS[ch], lw=1, ls=":", alpha=0.8, label=f"{LABELS[ch]} rest")
        for v in (fq, 2 * fq):
            ax.axvline(v, color=MUTED, ls="--", lw=1)
        ax.set(title=f"Flicker {fq:.2f} Hz", xlabel="Hz", ylabel="µV/√Hz")
        ax.legend(frameon=False, fontsize=8)
        # CCA classification on 2 s windows using both channels
        m = (t >= ph["start"] + 2) & (t < ph["end"])
        X = np.vstack([ys[ch][m] for ch in CHANNELS])
        for i in range(0, X.shape[1] - 2 * FS + 1, FS):
            w = X[:, i:i + 2 * FS]
            scores = [_cca_corr(w, _make_reference(c, w.shape[1], FS, 2)) for c in freqs]
            correct += int(np.argmax(scores) == freqs.index(fq))
            total += 1
    acc = 100 * correct / max(total, 1)
    r.metrics["cca_windows"] = total
    r.check("CCA picks the right frequency (%)", round(acc, 1), acc >= 80, "≥ 80 %")
    finish(fig, prefix)
    r.save(prefix)


# ───────────────────────── report ─────────────────────────

def test_report(args):
    rows = []
    for test in REPORT_TESTS:
        files = sorted(glob.glob(os.path.join(OUT_DIR, f"validate_{test}_*_result.json")))
        if not files:
            rows.append((test, "not run", "", []))
            continue
        res = json.load(open(files[-1]))
        checks = res.get("checks") or [{"check": k, "channel": None, "value": v, "pass": v["pass"]}
                                       for k, v in res.get("results", {}).items()]
        rows.append((test, "PASS" if res["passed"] else "FAIL", res["time"], checks))
    print(f"\n{'test':10s} {'result':8s} {'when':20s} failing checks")
    for test, status, when, checks in rows:
        fails = [f"{c['check']} {LABELS.get(c['channel'], '')}".strip() for c in checks if not c["pass"]]
        print(f"{test:10s} {status:8s} {when:20s} {'; '.join(fails)}")

    fig, ax = plt.subplots(figsize=(12, 0.6 + 0.55 * len(rows)))
    fig.patch.set_facecolor("#fcfcfb")
    ax.axis("off")
    for i, (test, status, when, checks) in enumerate(rows):
        y = len(rows) - i
        color = GOOD if status == "PASS" else BAD if status == "FAIL" else MUTED
        n_ok = sum(c["pass"] for c in checks)
        ax.text(0.0, y, test, fontsize=13, color=INK, va="center")
        ax.text(0.18, y, status, fontsize=13, color=color, fontweight="bold", va="center")
        ax.text(0.30, y, f"{n_ok}/{len(checks)} checks" if checks else "", fontsize=11, color=INK2, va="center")
        ax.text(0.45, y, when.replace("T", " "), fontsize=11, color=INK2, va="center")
        fails = [c["check"] for c in checks if not c["pass"]]
        ax.text(0.65, y, ("fails: " + ", ".join(sorted(set(fails)))[:60]) if fails else "", fontsize=9,
                color=BAD, va="center")
    ax.set_ylim(0.3, len(rows) + 0.7)
    ax.set_xlim(0, 1)
    passed = sum(r[1] == "PASS" for r in rows)
    ax.set_title(f"Cyton validation report — {passed}/{len(rows)} tests passed", loc="left", color=INK, fontsize=14)
    out = os.path.join(OUT_DIR, "validate_report")
    fig.savefig(out + ".png", dpi=120, bbox_inches="tight")
    with open(out + ".json", "w") as fh:
        json.dump([{"test": r[0], "result": r[1], "time": r[2], "checks": r[3]} for r in rows], fh, indent=2)
    print(f"\nSaved {out}.png and .json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("test", choices=TESTS + ["report"])
    ap.add_argument("--analyze", help="re-analyse a saved run (.json)")
    ap.add_argument("--oximeter", type=float, nargs="+", help="ecg: oximeter readings at the 4 cues (bpm)")
    ap.add_argument("--channels", type=int, nargs="+", default=[1, 2], help="channels to analyse (e.g. 1 for one electrode only)")
    ap.add_argument("--tag", default="", help="label added to result file names, e.g. dry / gold")
    ap.add_argument("--seconds", type=float, default=60, help="integrity: how many recent seconds to check")
    ap.add_argument("--recent", type=float, help="hardware: just analyse the last N seconds (set the GUI mode yourself)")
    ap.add_argument("--ext-channels", type=int, nargs="+", default=[1], help="extshort: channels clipped to the metal")
    ap.add_argument("--only", choices=["shorted", "testsignal"], help="hardware: check only one mode")
    ap.add_argument("--rounds", type=int, default=3, help="alpha: eyes open/closed rounds")
    ap.add_argument("--site", choices=["occipital", "forehead"], default="occipital", help="alpha: electrode site")
    ap.add_argument("--freqs", type=float, nargs="+", default=[12, 15], help="ssvep: target flicker frequencies")
    ap.add_argument("--stim", type=float, default=20, help="ssvep: seconds of flicker per frequency")
    ap.add_argument("--rest", type=float, default=20, help="ssvep: seconds of rest before each flicker")
    args = ap.parse_args()
    CHANNELS[:] = args.channels
    globals()[f"test_{args.test}"](args)


if __name__ == "__main__":
    main()
