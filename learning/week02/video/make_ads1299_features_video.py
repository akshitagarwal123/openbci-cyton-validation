"""Narrated explainer video: the ADS1299's feature list (datasheet page 1), one animated scene per feature.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_ads1299_features_video.py  ->  ads1299_features.mp4
Preview frames: python make_ads1299_features_video.py --stills DIR"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ads1299_features.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM = "#0f1418", "#e8edf0", "#93a1aa", "#3a454d"
GREEN, RED, BLUE, AMBER, PURPLE, TEAL, YELLOW = "#6cc48a", "#ef6b5e", "#5b9be0", "#f0a04b", "#9a92ec", "#4fd1c5", "#ffd166"
RNG = np.random.default_rng(1)
NOISE = RNG.normal(0, 1, 20000)          # fixed noise so frames don't flicker


# ---------- helpers ----------
def new_fig(): return plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
def sentence_at(text, p):
    parts = [x for x in re.split(r"(?<=[.?!])\s+", text) if x]
    total = sum(len(x) for x in parts); acc = 0
    for x in parts:
        acc += len(x)
        if p <= acc / total: return x
    return parts[-1]
def caption(fig, text, p):
    fig.text(0.5, 0.035, "\n".join(textwrap.wrap(sentence_at(text, p), 95)), ha="center", va="bottom", color=FG, fontsize=17,
             bbox=dict(boxstyle="round,pad=0.5", fc="#1b2329", ec="none"))
def title(fig, n, t): fig.text(0.04, 0.93, f"{n}. {t}" if n else t, color=FG, fontsize=24, weight="bold", ha="left")
def side(fig, lines, p=1.0, step=0.0, x=0.685, y0=0.82, dy=0.066):
    for i, (s, c, f) in enumerate(lines):
        if p >= i * step: fig.text(x, y0 - i * dy, s, color=c, fontsize=min(f, 15.5), va="top")
def axL(fig, rect=(0.06, 0.2, 0.58, 0.66), xlabel=None, ylabel=None):
    ax = fig.add_axes(rect); ax.set_facecolor(BG)
    for s in ax.spines.values(): s.set_color(DIM)
    ax.tick_params(colors=MU, labelsize=10)
    if xlabel: ax.set_xlabel(xlabel, color=MU, fontsize=11)
    if ylabel: ax.set_ylabel(ylabel, color=MU, fontsize=11)
    return ax
def blank(fig, rect=(0.04, 0.17, 0.62, 0.7)):
    ax = fig.add_axes(rect); ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis("off"); return ax
def box(ax, x, y, w, h, s, c, fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=BG, ec=c, lw=1.8))
    ax.text(x + w / 2, y + h / 2, s, color=c, fontsize=fs, ha="center", va="center")
def arrow(ax, a, b, c=MU): ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color=c, lw=1.6))


# ---------- scenes ----------
FEATURES = ["8 PGAs + 8 simultaneous ADCs", "Noise: 1 µVpp", "Bias current: 300 pA", "Data rate: 250 SPS–16 kSPS",
            "CMRR: −110 dB", "Gain: 1 to 24", "Uni/bipolar supplies", "Bias drive amplifier", "Lead-off detection",
            "Test signals", "Built-in oscillator", "Internal reference", "Power-down / standby", "Pin-compatible ADS129x",
            "SPI interface", "−40 °C to +85 °C"]

def s_title(fig, p, t):
    fig.text(0.5, 0.88, "The ADS1299, feature by feature", color=FG, fontsize=36, ha="center", weight="bold")
    fig.text(0.5, 0.82, "what each line on page 1 of the datasheet means", color=MU, fontsize=18, ha="center")
    for i, f in enumerate(FEATURES):
        if p > i / 20:
            x = 0.12 if i < 8 else 0.55; y = 0.72 - (i % 8) * 0.06
            fig.text(x, y, f"{i + 1:2d}.  {f}", color=FG if i % 2 == 0 else MU, fontsize=17)

def s_channels(fig, p, t):
    title(fig, 1, "Eight amplifiers, eight ADCs, all at once")
    for k, (rect, lab, col, stagger) in enumerate((((0.06, 0.55, 0.58, 0.3), "ADS1299: 8 ADCs sample at the same instant", GREEN, 0),
                                                   ((0.06, 0.17, 0.58, 0.3), "ESP32: 1 ADC takes turns between pins", RED, 1))):
        ax = axL(fig, rect); ax.set_xlim(0, 1); ax.set_ylim(-0.7, 7.7); ax.set_yticks([]); ax.set_xticks([])
        ax.set_title(lab, color=col, fontsize=12, loc="left")
        x = np.linspace(0, 1, 400)
        for ch in range(8):
            ax.plot(x, ch + 0.3 * np.sin(2 * np.pi * (3 + ch) * x), color=DIM, lw=1)
        cur = min(1, p * 1.15)
        for j in range(10):
            xs = j * 0.1 + 0.02
            for ch in range(8):
                xx = xs + stagger * ch * 0.011
                if xx <= cur: ax.plot(xx, ch + 0.3 * np.sin(2 * np.pi * (3 + ch) * xx), "o", ms=4, color=col)
    side(fig, [("Each channel has its own", FG, 17), ("amplifier (PGA) and ADC.", GREEN, 17), ("", FG, 8),
               ("Top: dots line up vertically:", FG, 17), ("same moment on all 8.", GREEN, 17),
               ("Bottom: dots slant: each", FG, 17), ("pin read a bit later.", RED, 17), ("", FG, 8),
               ("Brain methods compare", MU, 16), ("channels at the same instant.", MU, 16)], p=p, step=0.06)

def s_noise(fig, p, t):
    title(fig, 2, "Noise: 1 µV peak-to-peak")
    ax = axL(fig, xlabel="seconds", ylabel="µV"); ax.set_xlim(0, 0.5); ax.set_ylim(-60, 60)
    x = np.linspace(0, 0.5, 500); eeg = 20 * np.sin(2 * np.pi * 10 * x)
    n = int(500 * min(1, p * 2))
    ax.plot(x[:n], (eeg + 0.17 * NOISE[:500])[:n], color=GREEN, lw=1.6, label="ADS1299: alpha wave, 1 µV noise")
    if p > 0.5:
        m = int(500 * min(1, (p - 0.5) * 2))
        q = np.round((1600 + eeg) / 800) * 800 - 1600       # ESP32 steps of 800 µV
        ax.plot(x[:m], q[:m], color=RED, lw=2.2, label="ESP32 ADC: steps of 800 µV")
    ax.legend(loc="upper right", facecolor=BG, edgecolor=DIM, labelcolor=FG, fontsize=10)
    side(fig, [("Noise = the chip's own hiss.", FG, 17), ("ADS1299: ~1 µV", GREEN, 17), ("Alpha waves: ~20 µV", FG, 17), ("", FG, 8),
               ("ESP32 ADC: one step", RED, 17), ("= ~800 µV, taller than", RED, 17), ("this whole chart.", RED, 17),
               ("The wave disappears.", RED, 17), ("", FG, 8), ("Fine for ECG (~1 mV),", MU, 16), ("hopeless for EEG.", MU, 16)], p=p, step=0.06)

def s_bias_current(fig, p, t):
    title(fig, 3, "Input bias current: 300 pA")
    ax = axL(fig, (0.24, 0.2, 0.4, 0.62), xlabel="false voltage it creates (µV, log scale)")
    rows = [("ADS1299, gel 10 kΩ", 3, GREEN), ("ADS1299, dry 1 MΩ", 300, AMBER), ("LM358, gel 10 kΩ", 200, AMBER), ("LM358, dry 1 MΩ", 20000, RED)]
    ax.set_xscale("log"); ax.set_xlim(1, 100000); ax.set_ylim(-0.6, 3.6); ax.set_yticks(range(4))
    ax.set_yticklabels([r[0] for r in rows][::-1], color=FG, fontsize=12); ax.invert_yaxis(); ax.set_yticks(range(4)); ax.set_yticklabels([r[0] for r in rows], color=FG, fontsize=12)
    for i, (lab, v, c) in enumerate(rows):
        g = min(1, max(0, p * 1.6 - i * 0.15)); w = 10 ** (math.log10(v) * g) if g > 0 else 1
        ax.barh(i, w - 1, left=1, color=c, height=0.55)
        if g >= 1: ax.text(w * 1.2, i, f"{v:,} µV", color=c, fontsize=12, va="center")
    ax.axvline(20, color=MU, ls="--", lw=1); ax.text(22, 3.5, "alpha wave ≈ 20 µV", color=MU, fontsize=10)
    side(fig, [("A tiny current leaks into", FG, 17), ("every input pin.", FG, 17), ("", FG, 8), ("It flows through the", FG, 17),
               ("electrode's resistance:", FG, 17), ("V = I × R", YELLOW, 17), ("", FG, 8), ("ADS1299: 300 pA", GREEN, 17),
               ("LM358: ~20,000 pA", RED, 17)], p=p, step=0.06)

def s_rate(fig, p, t):
    title(fig, 4, "Data rate: 250 to 16,000 samples per second")
    rates = [250, 1000, 16000]
    for i, r in enumerate(rates):
        ax = axL(fig, (0.06, 0.64 - i * 0.22, 0.58, 0.18)); ax.set_xlim(0, 0.1); ax.set_ylim(-1.6, 1.6); ax.set_yticks([])
        if i < 2: ax.set_xticks([])
        else: ax.set_xlabel("seconds (one 10 Hz wave)", color=MU, fontsize=11)
        xs = np.arange(0, 0.1, 1 / r); noise = 0.04 * (1 + i * 2.5) * NOISE[:len(xs)]
        n = int(len(xs) * min(1, p * 1.3))
        ax.plot(xs[:n], (np.sin(2 * np.pi * 10 * xs) + noise)[:n], "o" if r < 5000 else "-", ms=4, lw=0.8, color=[GREEN, AMBER, RED][i])
        ax.text(0.001, 1.25, f"{r:,} SPS: {len(xs)} samples", color=FG, fontsize=11)
    side(fig, [("More samples per second", FG, 17), ("catches faster signals...", FG, 17), ("...but lets in more noise.", RED, 17), ("", FG, 8),
               ("EEG lives below ~100 Hz,", FG, 17), ("so 250 or 500 SPS is plenty.", GREEN, 17), ("", FG, 8),
               ("The Cyton uses 250 SPS,", MU, 16), ("like your ECG sketch.", MU, 16)], p=p, step=0.07)

def s_cmrr(fig, p, t):
    title(fig, 5, "CMRR: −110 dB")
    x = np.linspace(0, 0.2, 800); hum = 300 * np.sin(2 * np.pi * 50 * x); eeg = 0.02 * np.sin(2 * np.pi * 10 * x)
    n = int(800 * min(1, p * 1.4))
    for i, (y, lab, c, unit, lim) in enumerate(((hum + eeg, "Electrode +: hum + brain", AMBER, "mV", 400), (hum, "Electrode −: hum only", AMBER, "mV", 400),
                                               (eeg * 1000 + 1.0 * np.sin(2 * np.pi * 50 * x), "Chip output (+ minus −)", GREEN, "µV", 30))):
        ax = axL(fig, (0.08, 0.64 - i * 0.22, 0.56, 0.18)); ax.set_xlim(0, 0.2); ax.set_ylim(-lim, lim)
        ax.set_ylabel(unit, color=MU, fontsize=10)
        if i < 2: ax.set_xticks([])
        if i < 2 or p > 0.45: ax.plot(x[:n], y[:n], color=c, lw=1.2)
        ax.text(0.002, lim * 0.72, lab, color=c, fontsize=11)
    side(fig, [("Your body picks up 50 Hz", FG, 17), ("mains hum: ~300 mV, the", FG, 17), ("SAME on every electrode.", AMBER, 17), ("", FG, 8),
               ("The chip keeps only the", FG, 17), ("difference, and shrinks the", FG, 17), ("shared part 316,000×.", GREEN, 17), ("", FG, 8),
               ("300 mV hum → ~1 µV", GREEN, 17)], p=p, step=0.06)

def s_gain(fig, p, t):
    title(fig, 6, "Programmable gain: 1, 2, 4, 6, 8, 12 or 24")
    gains = [1, 2, 4, 6, 8, 12, 24]; k = min(6, int(p * 8))
    ax = axL(fig, (0.14, 0.2, 0.5, 0.62), xlabel="input range it can measure: ± mV"); ax.set_xlim(0, 4800); ax.set_ylim(-0.6, 6.6)
    ax.set_yticks(range(7)); ax.set_yticklabels([f"gain {g}" for g in gains], color=FG, fontsize=12); ax.invert_yaxis()
    for i, g in enumerate(gains):
        r = 4500 / g
        ax.barh(i, r, color=BLUE if i == k else DIM, height=0.6)
        ax.text(r + 60, i, f"±{r:,.0f}", color=FG if i == k else MU, fontsize=11, va="center")
    ax.axvline(300, color=RED, ls="--", lw=1.4); ax.text(330, 6.45, "loose electrode ≈ 300 mV", color=RED, fontsize=10)
    side(fig, [("Like your LM358 gain of 10,", FG, 17), ("but set by software,", BLUE, 17), ("no resistors to swap.", BLUE, 17), ("", FG, 8),
               ("Range = ±4.5 V ÷ gain.", YELLOW, 17), ("Gain 24 → only ±187 mV.", FG, 17), ("Bigger inputs clip,", RED, 17),
               ("just like your clipping test.", RED, 17), ("", FG, 8), ("The Cyton uses gain 24.", MU, 16)], p=p, step=0.06)

def s_supply(fig, p, t):
    title(fig, 7, "Unipolar or bipolar supplies")
    x = np.linspace(0, 1, 300)
    for i, (lo, hi, mid, lab, c) in enumerate(((0, 5, 2.5, "Unipolar: 0 V and +5 V", AMBER), (-2.5, 2.5, 0, "Bipolar: −2.5 V and +2.5 V", GREEN))):
        ax = axL(fig, (0.07 + i * 0.31, 0.2, 0.25, 0.6), xlabel="time"); ax.set_xlim(0, 1); ax.set_ylim(-3, 5.5); ax.set_xticks([])
        ax.axhspan(lo, hi, color=c, alpha=0.12); ax.axhline(hi, color=c, lw=1); ax.axhline(lo, color=c, lw=1)
        ax.axhline(0, color=MU, ls=":", lw=1); ax.text(0.02, 0.15, "body = 0 V", color=MU, fontsize=10)
        if p > 0.15 + i * 0.3: ax.plot(x, mid + 1.5 * np.sin(2 * np.pi * 3 * x + t * 3), color=c, lw=1.8)
        ax.set_title(lab, color=c, fontsize=12); ax.set_ylabel("volts", color=MU, fontsize=10)
    side(fig, [("Analog side: 5 V total.", FG, 17), ("Unipolar: like your LM358", AMBER, 17), ("on USB: signal sits at 2.5 V.", AMBER, 17),
               ("Bipolar: like the TL072 on ±:", GREEN, 17), ("signal sits at 0 V, like", GREEN, 17), ("your body. Cyton uses this.", GREEN, 17), ("", FG, 8),
               ("Digital side: 1.8–3.6 V,", BLUE, 17), ("so 3.3 V talks straight", BLUE, 17), ("to the ESP32.", BLUE, 17)], p=p, step=0.06)

def s_biasdrive(fig, p, t):
    title(fig, 8, "Bias drive amplifier: noise-cancelling for your body")
    ax = blank(fig, (0.04, 0.55, 0.62, 0.32)); ax.set_ylim(-0.7, 3)
    box(ax, 0.2, 1.0, 2.0, 1.0, "electrodes", AMBER); box(ax, 3.0, 1.0, 2.0, 1.0, "average:\nshared hum", AMBER)
    box(ax, 5.8, 1.0, 1.6, 1.0, "flip ×(−1)", PURPLE); box(ax, 8.1, 1.0, 1.8, 1.0, "BIAS\nelectrode", GREEN)
    arrow(ax, (2.25, 1.5), (2.95, 1.5)); arrow(ax, (5.05, 1.5), (5.75, 1.5)); arrow(ax, (7.45, 1.5), (8.05, 1.5))
    ax.annotate("", xy=(1.2, 0.95), xytext=(9.0, 0.95), arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.4, connectionstyle="arc3,rad=-0.2"))
    ax.text(5.0, -0.55, "pushed back into the body", color=GREEN, fontsize=11, ha="center")
    ax2 = axL(fig, (0.06, 0.17, 0.58, 0.32), xlabel="seconds", ylabel="hum on body (mV)")
    x = np.linspace(0, 2, 2000); on = 0.8; amp = np.where(x < on, 300, 300 * np.exp(-(x - on) * 12) + 10)
    n = int(2000 * min(1, p * 1.2)); ax2.set_xlim(0, 2); ax2.set_ylim(-350, 350)
    ax2.plot(x[:n], (amp * np.sin(2 * np.pi * 50 * x))[:n], color=AMBER, lw=0.7); ax2.axvline(on, color=GREEN, ls="--", lw=1)
    ax2.text(on + 0.03, 280, "bias drive ON", color=GREEN, fontsize=10)
    side(fig, [("This is your green RL", FG, 17), ("electrode on the AD8232.", GREEN, 17), ("", FG, 8), ("1. Measure the hum that is", FG, 17),
               ("   common to all electrodes", FG, 17), ("2. Flip it upside down", PURPLE, 17), ("3. Push it back into you", GREEN, 17), ("", FG, 8),
               ("The hum mostly cancels", FG, 17), ("before it's even measured.", FG, 17)], p=p, step=0.06)

def s_leadoff(fig, p, t):
    title(fig, 9, "Lead-off detection")
    ax = axL(fig, (0.06, 0.2, 0.42, 0.62), xlabel="seconds", ylabel="voltage at the electrode (V)")
    x = np.linspace(0, 4, 800); off = 2.2; v = np.where(x < off, 0.0006 + 0.0003 * NOISE[:800], 2.5)
    n = int(800 * min(1, p * 1.15)); ax.set_xlim(0, 4); ax.set_ylim(-0.2, 2.8)
    ax.plot(x[:n], v[:n], color=TEAL, lw=1.8); ax.axhline(1.5, color=MU, ls=":", lw=1); ax.text(0.05, 1.56, "threshold", color=MU, fontsize=10)
    status = x[max(0, n - 1)] >= off
    a = blank(fig, (0.5, 0.42, 0.16, 0.25)); a.set_ylim(0, 4)
    box(a, 0.5, 1.2, 9, 1.8, "CH1: LEAD OFF" if status else "CH1: OK", RED if status else GREEN, fs=13)
    side(fig, [("Same idea as the AD8232's", FG, 17), ("LO+ / LO− pins you wired.", TEAL, 17), ("", FG, 8), ("The chip pushes a tiny", FG, 17),
               ("current (6 nA) into each", FG, 17), ("electrode.", FG, 17), ("On skin: voltage stays tiny.", GREEN, 17),
               ("Off: voltage shoots up.", RED, 17), ("→ the channel is flagged.", RED, 17)], p=p, step=0.06)

def s_test(fig, p, t):
    title(fig, 10, "Built-in test signals")
    ax = axL(fig, xlabel="seconds"); ax.set_xlim(0, 4); ax.set_ylim(-1, 8.2); ax.set_yticks(range(8)); ax.set_yticklabels([f"CH{i + 1}" for i in range(8)], color=FG)
    x = np.linspace(0, 4, 1600); sq = 0.35 * np.sign(np.sin(2 * np.pi * 1.0 * x)); n = int(1600 * min(1, p * 1.2))
    for ch in range(8): ax.plot(x[:n], (ch + sq)[:n], color=TEAL, lw=1.4)
    side(fig, [("The chip makes its own", FG, 17), ("square wave: ±1.9 mV,", TEAL, 17), ("about 1 or 2 Hz.", TEAL, 17), ("", FG, 8),
               ("Fed into all 8 channels,", FG, 17), ("no person needed.", FG, 17), ("", FG, 8), ("Like your fake sine data,", MU, 16),
               ("but made inside the chip.", MU, 16), ("Your first test on the board.", GREEN, 17)], p=p, step=0.06)

def s_osc(fig, p, t):
    title(fig, 11, "Built-in oscillator: the clock")
    ax = axL(fig, (0.06, 0.45, 0.58, 0.35)); ax.set_xlim(0, 40); ax.set_ylim(-0.3, 1.5); ax.set_yticks([]); ax.set_xticks([])
    x = np.linspace(0, 40, 4000); sh = t * 6; clk = (np.floor((x + sh) * 1) % 2 == 0).astype(float)
    ax.plot(x, clk, color=YELLOW, lw=1.6); ax.set_title("2,048,000 ticks every second (shown very slowed down)", color=YELLOW, fontsize=12, loc="left")
    a = blank(fig, (0.06, 0.17, 0.58, 0.25)); a.set_ylim(0, 3)
    if p > 0.35:
        a.text(0.2, 2.0, "2,048,000 ticks/s ÷ 250 samples/s", color=FG, fontsize=17)
        a.text(0.2, 0.9, "= 8,192 ticks per sample", color=GREEN, fontsize=17)
    side(fig, [("Every sample is timed by", FG, 17), ("a clock inside the chip.", FG, 17), ("", FG, 8), ("Built in = no external", GREEN, 17),
               ("crystal on your PCB.", GREEN, 17), ("", FG, 8), ("All 8 ADCs follow the", FG, 17), ("same clock, so they", FG, 17), ("stay in step.", FG, 17)], p=p, step=0.06)

def s_ref(fig, p, t):
    title(fig, 12, "Internal reference: the ruler")
    ax = blank(fig)
    ax.add_patch(Rectangle((0.5, 4.6), 9, 0.7, fc="#2a2410", ec=YELLOW, lw=1.5))
    for i in range(46): ax.plot([0.5 + i * 9 / 45] * 2, [4.6, 4.6 + (0.45 if i % 10 == 0 else 0.22)], color=YELLOW, lw=1)
    ax.text(0.5, 5.6, "0 V", color=YELLOW, fontsize=12); ax.text(9.5, 5.6, "4.5 V", color=YELLOW, fontsize=12, ha="right")
    lines = [("4.5 V  ÷  8,388,607 steps (24-bit)", FG), ("=  0.54 µV per step", FG), ("÷  gain 24", BLUE), ("=  0.022 µV per count", GREEN)]
    for i, (s, c) in enumerate(lines):
        if p > 0.15 + i * 0.15: ax.text(0.6, 3.5 - i * 0.85, s, color=c, fontsize=19)
    side(fig, [("The ADC measures every", FG, 17), ("voltage against a very", FG, 17), ("steady 4.5 V ruler.", YELLOW, 17), ("", FG, 8),
               ("This is the 4.5 in the", FG, 17), ("BrainFlow formula you used", FG, 17), ("for the fake Cyton!", GREEN, 17), ("", FG, 8),
               ("External ruler possible,", MU, 16), ("but Cyton uses internal.", MU, 16)], p=p, step=0.06)

def s_power(fig, p, t):
    title(fig, 13, "Flexible power-down and standby")
    on = 8 - min(6, int(p * 9))
    ax = blank(fig)
    for i in range(8):
        c = GREEN if i < on else DIM
        box(ax, 0.3 + i * 1.18, 4.6, 0.95, 1.1, f"CH{i + 1}", c, fs=11)
        ax.text(0.78 + i * 1.18, 4.25, "on" if i < on else "off", color=c, fontsize=10, ha="center")
    pw = on * 5; ax.text(0.3, 3.2, f"power: {pw} mW  (≈5 mW per channel)", color=AMBER, fontsize=16)
    ax.add_patch(Rectangle((0.3, 2.3), 9.0 * pw / 40, 0.5, fc=AMBER)); ax.text(0.3, 1.5, f"battery life: ×{8 / on:.1f}", color=GREEN, fontsize=16)
    ax.add_patch(Rectangle((0.3, 0.6), 9.0 * min(1, (8 / on) / 4), 0.5, fc=GREEN))
    side(fig, [("Switch off channels you", FG, 17), ("don't need, or put the", FG, 17), ("whole chip to sleep.", FG, 17), ("", FG, 8),
               ("Less power = longer", GREEN, 17), ("battery life.", GREEN, 17), ("", FG, 8), ("Matters for a headset", MU, 16), ("running on a LiPo.", MU, 16)], p=p, step=0.06)

def s_pincompat(fig, p, t):
    title(fig, 14, "Pin-compatible with the ADS129x")
    ax = blank(fig); names = ["ADS1299\n(EEG)", "ADS1298\n(ECG)"]; k = int(t / 1.5) % 2
    cx, cy, s = 5, 3.6, 2.4
    ax.add_patch(Rectangle((cx - s / 2, cy - s / 2), s, s, fc="#1b2329", ec=FG, lw=1.6))
    for i in range(16):
        d = -s / 2 + (i + 0.5) * s / 16
        for (x0, y0, x1, y1) in ((cx + d, cy + s / 2, cx + d, cy + s / 2 + 0.35), (cx + d, cy - s / 2, cx + d, cy - s / 2 - 0.35),
                                 (cx - s / 2, cy + d, cx - s / 2 - 0.35, cy + d), (cx + s / 2, cy + d, cx + s / 2 + 0.35, cy + d)):
            ax.plot([x0, x1], [y0, y1], color=MU, lw=1.6)
    ax.text(cx, cy, names[k], color=GREEN if k == 0 else BLUE, fontsize=17, ha="center", va="center")
    ax.text(cx, 0.6, "same 64 pins, same footprint on your PCB", color=FG, fontsize=14, ha="center")
    side(fig, [("TI's ECG chips (ADS1294,", FG, 17), ("ADS1296, ADS1298) use the", FG, 17), ("same pins and package.", BLUE, 17), ("", FG, 8),
               ("You could swap one in", GREEN, 17), ("without redrawing your PCB.", GREEN, 17), ("", FG, 8), ("Same registers too, so", MU, 16),
               ("most code carries over.", MU, 16)], p=p, step=0.06)

def s_spi(fig, p, t):
    title(fig, 15, "SPI: how the data reaches the ESP32")
    ax = axL(fig, (0.06, 0.2, 0.58, 0.62)); ax.set_xlim(0, 30); ax.set_ylim(-0.5, 8.5); ax.set_xticks([]); ax.set_yticks([1, 3.2, 5.4, 7.6])
    ax.set_yticklabels(["DOUT", "SCLK", "CS", "DRDY"], color=FG, fontsize=12)
    x = np.linspace(0, 30, 3000); cur = 30 * min(1, p * 1.2); m = x <= cur
    drdy = np.where(x < 3, 1, 0) * 0.9 + 7.6 - 0.45; cs = np.where(x < 4, 1, 0) * 0.9 + 5.4 - 0.45
    sclk = np.where((x > 5) & (np.floor((x - 5) * 1.6) % 2 == 0), 1, 0) * 0.9 + 3.2 - 0.45
    bits = np.array([int(b) for b in "101101001110010110101001011010011011"])
    dout = np.where(x > 5, bits[np.clip(((x - 5) * 0.8).astype(int), 0, len(bits) - 1)], 0) * 0.9 + 1 - 0.45
    for y, c in ((drdy, YELLOW), (cs, PURPLE), (sclk, BLUE), (dout, GREEN)): ax.plot(x[m], y[m], color=c, lw=1.6)
    for x0, lab in ((5, "status"), (12, "CH1"), (19, "CH2"), (26, "… CH8")):
        if cur > x0: ax.text(x0, -0.3, lab, color=MU, fontsize=10)
    side(fig, [("1. DRDY drops: 'data ready'", YELLOW, 17), ("2. ESP32 pulls CS low", PURPLE, 17), ("3. ESP32 ticks SCLK...", BLUE, 17),
               ("4. ...and reads DOUT bits", GREEN, 17), ("", FG, 8), ("27 bytes per sample:", FG, 17), ("3 status + 8 ch × 3 bytes", FG, 17), ("", FG, 8),
               ("The same 24 data bytes", MU, 16), ("as your fake Cyton packets.", MU, 16)], p=p, step=0.06)

def s_temp(fig, p, t):
    title(fig, 16, "Operating temperature: −40 °C to +85 °C")
    ax = axL(fig, (0.22, 0.2, 0.12, 0.62)); ax.set_xlim(0, 1); ax.set_ylim(-50, 95); ax.set_xticks([])
    ax.set_ylabel("°C", color=MU); ax.axhspan(-40, 85, color=GREEN, alpha=0.18)
    ax.bar(0.5, (min(1, p * 1.5)) * 125, bottom=-40, width=0.35, color=RED)
    marks = [(-18, "freezer"), (25, "your room"), (37, "body"), (70, "hot car")]
    for i, (v, s) in enumerate(marks):
        if p > 0.3 + i * 0.12: ax.axhline(v, color=MU, ls=":", lw=1); fig.text(0.355, 0.2 + 0.62 * (v + 50) / 145, f"{v} °C  {s}", color=FG, fontsize=13, va="center")
    side(fig, [("'Industrial grade': works", FG, 17), ("from a freezer to a hot car.", FG, 17), ("", FG, 8),
               ("Your board will only ever", GREEN, 17), ("see room temperature,", GREEN, 17), ("so you can ignore this one.", GREEN, 17)], p=p, step=0.08)

def s_end(fig, p, t):
    fig.text(0.5, 0.86, "ESP32 ADC vs AD8232 vs ADS1299", color=FG, fontsize=30, ha="center", weight="bold")
    rows = [("", "ESP32 ADC", "AD8232", "ADS1299"), ("Channels", "1 at a time", "1", "8 at once"), ("Resolution", "12-bit", "analog", "24-bit"),
            ("Noise", "~mV", "~10 µV", "~1 µV"), ("Good for", "ECG", "ECG", "EEG"), ("Bias drive, lead-off", "no", "yes", "yes, every channel")]
    for i, r in enumerate(rows):
        if p > i * 0.1:
            for j, s in enumerate(r):
                fig.text(0.1 + j * 0.22, 0.74 - i * 0.075, s, color=(GREEN if j == 3 else FG) if i else MU, fontsize=18, weight="bold" if i == 0 else None)
    if p > 0.7: fig.text(0.5, 0.24, "Next: find these on the Cyton schematic: BIAS, the reference caps, the SPI lines.", color=YELLOW, fontsize=17, ha="center")


SCENES = [
 ("This video explains the A D S twelve ninety nine's feature list, from page one of its datasheet. Sixteen features, one at a time.", s_title),
 ("Feature one: eight low noise amplifiers and eight A D Cs. Each channel has its own amplifier and its own converter, so all eight channels are measured at exactly the same instant. On the top, the dots line up vertically. The E S P thirty two has only one A D C, so it takes turns, and the dots slant. Brain methods compare channels at the same moment, so this matters.", s_channels),
 ("Feature two: input referred noise of one micro volt, peak to peak. That's the chip's own hiss. Alpha waves are about twenty micro volts, so the green wave stays clean. Now the E S P thirty two. One step of its A D C is about eight hundred micro volts, taller than this whole chart, so the brain wave disappears into a flat line. That's fine for E C G, but hopeless for E E G.", s_noise),
 ("Feature three: input bias current of three hundred pico amps. A tiny current leaks into every input pin, and flows through the electrode's resistance. Voltage equals current times resistance, so it creates a false voltage. With gel electrodes that's only three micro volts. Your L M three fifty eight leaks about seventy times more, which is why E E G chips aren't built from cheap op amps.", s_bias_current),
 ("Feature four: a data rate from two hundred fifty to sixteen thousand samples per second. More samples catch faster signals, but they also let in more noise. E E G lives below about one hundred hertz, so two hundred fifty or five hundred samples per second is plenty. The Cyton uses two hundred fifty, the same as your E C G sketch.", s_rate),
 ("Feature five: a common mode rejection ratio of minus one hundred ten decibels. Your body picks up fifty hertz mains hum, about three hundred milli volts, and it's the same on every electrode. The chip keeps only the difference between electrodes, and shrinks the shared part about three hundred sixteen thousand times. Three hundred milli volts of hum becomes about one micro volt.", s_cmrr),
 ("Feature six: programmable gain, from one to twenty four. It's like your L M three fifty eight with a gain of ten, but set in software, with no resistors to swap. The input range is plus or minus four point five volts divided by the gain. At gain twenty four, that's only plus or minus one hundred eighty seven milli volts. A loose electrode can go beyond that and clip, just like your clipping test. The Cyton uses gain twenty four.", s_gain),
 ("Feature seven: unipolar or bipolar supplies. The analog side needs five volts in total. Unipolar means zero and five volts, like your L M three fifty eight on U S B, so the signal sits at two and a half volts. Bipolar means minus and plus two and a half volts, like the T L zero seventy two, so the signal sits at zero volts, just like your body. The Cyton uses bipolar. The digital side runs from one point eight to three point six volts, so at three point three volts it talks straight to the E S P thirty two.", s_supply),
 ("Feature eight: a built in bias drive amplifier. This is your green R L electrode on the A D eight two three two. It measures the hum that's common to all electrodes, flips it upside down, and pushes it back into your body. When bias drive turns on, the hum on your body mostly cancels before it's even measured.", s_biasdrive),
 ("Feature nine: lead off detection. It's the same idea as the L O plus and L O minus pins you wired on the A D eight two three two. The chip pushes a tiny current into each electrode. On skin, the voltage stays tiny. When an electrode falls off, the voltage shoots up, and that channel gets flagged.", s_leadoff),
 ("Feature ten: built in test signals. The chip makes its own square wave, about plus or minus two milli volts, at one or two hertz, and feeds it into all eight channels. No person needed. It's like your fake sine data, but made inside the chip, and it will be your first test on the finished board.", s_test),
 ("Feature eleven: a built in oscillator. Every sample is timed by a clock inside the chip, ticking two point oh four eight million times a second. At two hundred fifty samples per second, that's eight thousand one hundred ninety two ticks per sample. Because it's built in, you don't need an external crystal on your board.", s_osc),
 ("Feature twelve: an internal reference. The A D C measures every voltage against a very steady four point five volt ruler. Divide it into eight point four million steps, then by the gain of twenty four, and each count is about zero point zero two two micro volts. That's the four point five in the Brain Flow formula you used for the fake Cyton.", s_ref),
 ("Feature thirteen: flexible power down and standby. You can switch off channels you don't need, or put the whole chip to sleep. Each channel uses about five milli watts, so fewer channels means longer battery life. That matters for a headset running on a lithium battery.", s_power),
 ("Feature fourteen: pin compatible with the A D S one two nine x family. T I's E C G chips, the A D S twelve ninety four, ninety six, and ninety eight, use the same sixty four pins and the same package. You could swap one in without redrawing your circuit board, and most of your code would carry over.", s_pincompat),
 ("Feature fifteen: an S P I serial interface. When a sample is ready, D R D Y drops low. The E S P thirty two pulls chip select low, ticks the clock, and reads the bits on D out. That's twenty seven bytes per sample: three status bytes, plus three bytes for each of the eight channels. Those are the same twenty four data bytes as in your fake Cyton packets.", s_spi),
 ("Feature sixteen: an operating temperature from minus forty to plus eighty five degrees. That's industrial grade, from a freezer to a hot car. Your board will only ever see room temperature, so you can ignore this one.", s_temp),
 ("To sum up: the E S P thirty two's A D C is fine for E C G, the A D eight two three two adds bias drive and lead off, and the A D S twelve ninety nine does it all on eight channels, quietly enough for E E G. Next, find these features on the Cyton schematic.", s_end),
]


def main():
    tmp = tempfile.mkdtemp()
    audio_files, durations = [], []
    for i, (text, _) in enumerate(SCENES):
        aiff = os.path.join(tmp, f"s{i}.aiff"); wav = os.path.join(tmp, f"s{i}.wav")
        subprocess.run(["say", "-v", VOICE, "-r", "160", "-o", aiff, text], check=True)
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", aiff]).strip()) + 0.8
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff, "-af", "apad", "-t", f"{d:.3f}", "-ar", "44100", "-ac", "1", wav], check=True)
        audio_files.append(wav); durations.append(d)
    lst = os.path.join(tmp, "list.txt"); open(lst, "w").write("".join(f"file '{a}'\n" for a in audio_files))
    narration = os.path.join(tmp, "narration.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", narration], check=True)
    silent = os.path.join(tmp, "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", silent], stdin=subprocess.PIPE)
    for (text, draw), d in zip(SCENES, durations):
        n = int(round(d * FPS))
        for k in range(n):
            fig = new_fig(); draw(fig, k / max(1, n - 1), k / FPS); caption(fig, text, k / max(1, n - 1))
            fig.canvas.draw(); ff.stdin.write(fig.canvas.buffer_rgba().tobytes()); plt.close(fig)
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", narration, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", OUT], check=True)
    print("saved", OUT, f"{sum(durations):.0f} s")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stills":
        d = sys.argv[2] if len(sys.argv) > 2 else "."
        for i, (text, draw) in enumerate(SCENES):
            p = 0.97
            fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
