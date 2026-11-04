"""Narrated video: the ADS1299's top row of pins on the Cyton schematic (U6 pins 53-63).
Answers: why 4 bias pins (BIAS_REF/INV/OUT/IN), why so many AVDD/AVSS pins, and what VCAP3 is.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_ads_top_pins_video.py -> ads1299_top_pins.mp4
Preview frames: python make_ads_top_pins_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ads1299_top_pins.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
BIASC, AVDDC, AVSSC, VCAPC, YEL, TEAL, RED = "#ff8a5c", "#2ec4a0", "#5aa9ff", "#ffd166", "#ffd166", "#2ec4a0", "#ef5b5b"
RNG = np.random.default_rng(7); NOISE = RNG.normal(0, 1, 6000)

PINS = [(61, "BIAS_INV", "bias"), (63, "BIAS_OUT", "bias"), (62, "BIAS_IN", "bias"), (60, "BIAS_REF", "bias"),
        (21, "AVDD", "avdd"), (19, "AVDD", "avdd"), (58, "AVSS", "avss"), (57, "AVSS", "avss"), (20, "AVSS", "avss"), (23, "AVSS", "avss"),
        (56, "AVDD", "avdd"), (59, "AVDD", "avdd"), (22, "AVDD", "avdd"), (55, "VCAP3", "vcap"), (54, "AVDD_1", "avdd"), (53, "AVSS_1", "avss")]
GCOL = {"bias": BIASC, "avdd": AVDDC, "avss": AVSSC, "vcap": VCAPC}
PX = lambda i: 2.9 + i * 0.72


def new_fig():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off"); ax.set_facecolor(BG)
    return fig, ax
def ease(x): x = min(1, max(0, x)); return 0.5 - 0.5 * math.cos(math.pi * x)
def ramp(p, a, b): return ease((p - a) / (b - a))
def sentence_at(text, p):
    parts = [x for x in re.split(r"(?<=[.?!])\s+", text) if x]; total = sum(len(x) for x in parts); acc = 0
    for x in parts:
        acc += len(x)
        if p <= acc / total: return x
    return parts[-1]
def caption(ax, text, p):
    ax.text(8, 0.3, "\n".join(textwrap.wrap(sentence_at(text, p), 92)), color=FG, fontsize=17, ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.45", fc="#14254a", ec="none"))
def title(ax, s): ax.text(0.4, 8.45, s, color=FG, fontsize=24, weight="bold", va="center")
def box(ax, x, y, w, h, t1, t2="", ec=FG, c1=FG):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=PANEL, ec=ec, lw=2, zorder=3))
    ax.text(x + w / 2, y + h / 2 + (0.18 if t2 else 0), t1, color=c1, fontsize=15, ha="center", va="center", weight="bold", zorder=4)
    if t2: ax.text(x + w / 2, y + h / 2 - 0.25, t2, color=MU, fontsize=11.5, ha="center", va="center", zorder=4)
def ground(ax, x, y, c=FG, up=False):
    s = -1 if up else 1
    for i, w in enumerate((0.25, 0.16, 0.07)): ax.plot([x - w, x + w], [y - s * i * 0.09] * 2, color=c, lw=1.8)
def cap_v(ax, x, y, c=FG):                      # capacitor in a horizontal wire: two vertical plates
    ax.plot([x - 0.06, x - 0.06], [y - 0.2, y + 0.2], color=c, lw=2.6); ax.plot([x + 0.06, x + 0.06], [y - 0.2, y + 0.2], color=c, lw=2.6)
def cap_h(ax, x, y, c=FG):                      # capacitor in a vertical wire: two horizontal plates
    ax.plot([x - 0.2, x + 0.2], [y + 0.06] * 2, color=c, lw=2.6); ax.plot([x - 0.2, x + 0.2], [y - 0.06] * 2, color=c, lw=2.6)


def strip(ax, hi=()):
    """The exact top row of U6 as on the Cyton schematic."""
    col = lambda g: GCOL[g] if g in hi else FG
    ax.add_patch(Rectangle((2.5, 1.45), 11.75, 1.3, fc=PANEL, ec=FG, lw=1.8, zorder=2))
    ax.text(14.35, 1.45, "U6", color=MU, fontsize=12)
    for i, (num, name, g) in enumerate(PINS):
        x = PX(i); c = col(g)
        ax.plot([x, x], [2.75, 3.55], color=c, lw=1.8)
        ax.text(x + 0.05, 3.4, str(num), color=MU, fontsize=9.5, ha="left")
        ax.text(x, 2.1, name, color=c, fontsize=9, ha="center", va="center", rotation=90, zorder=3)
    # AVDD bus and AVSS bus
    ax.plot([PX(4), PX(14)], [5.0, 5.0], color=col("avdd"), lw=1.8)
    for i, (_, _, g) in enumerate(PINS):
        if g == "avdd": ax.plot([PX(i)] * 2, [3.55, 5.0], color=col("avdd"), lw=1.8); ax.plot(PX(i), 5.0, "o", color=col("avdd"), ms=4)
        if g == "avss": ax.plot([PX(i)] * 2, [3.55, 4.4], color=col("avss"), lw=1.8); ax.plot(PX(i), 4.4, "o", color=col("avss"), ms=4)
    ax.plot([PX(9) - 1.8, 15.75], [4.4, 4.4], color=col("avss"), lw=1.8)
    ax.plot([7.9, 7.9], [5.0, 5.35], color=col("avdd"), lw=1.8); ax.plot([7.7, 8.1], [5.35, 5.35], color=col("avdd"), lw=2.2)
    ax.text(7.9, 5.55, "AVDD +2.5 V", color=col("avdd"), fontsize=12, ha="center")
    ax.plot([15.5, 15.5], [4.4, 4.05], color=col("avss"), lw=1.8); ax.plot([15.3, 15.7], [4.05, 4.05], color=col("avss"), lw=2.2)
    ax.text(15.5, 3.55, "AVSS\n−2.5 V", color=col("avss"), fontsize=10.5, ha="center")
    for x, nm in ((14.45, "C21"), (14.9, "C18")):
        ax.plot([x, x], [4.4, 3.85], color=col("avss"), lw=1.4); cap_h(ax, x, 3.75, col("avss")); ax.plot([x, x], [3.65, 3.35], color=FG, lw=1.4)
    ax.plot([14.45, 14.9], [3.35, 3.35], color=FG, lw=1.4); ground(ax, 14.68, 3.35)
    ax.text(14.68, 2.95, "C21, C18\n1 µF → AGND", color=col("avss") if "avss" in hi else MU, fontsize=9.5, ha="center", va="top")
    # VCAP3 -> C15 || C19 -> AVSS
    xv = PX(13); c = col("vcap")
    ax.plot([xv, xv], [3.55, 6.5], color=c, lw=1.8); ax.plot([xv, 13.2], [6.5, 6.5], color=c, lw=1.8)
    cap_v(ax, 13.3, 6.5, c); ax.plot([13.4, 15.75, 15.75], [6.5, 6.5, 4.4], color=c, lw=1.8)
    ax.text(13.3, 6.85, "C15 0.1 µF ‖ C19 1 µF", color=c, fontsize=11, ha="center")
    # bias network
    cb = col("bias")
    ax.plot([PX(0), PX(0), 0.5], [3.55, 5.3, 5.3], color=cb, lw=1.8); ax.text(0.4, 5.0, "BIAS_INV → J2", color=cb, fontsize=11)
    ax.plot([PX(1), PX(1)], [3.55, 6.9], color=cb, lw=1.8); ax.plot([PX(2), PX(2), PX(1)], [3.55, 6.9, 6.9], color=cb, lw=1.8)
    ax.plot(PX(1), 6.9, "o", color=cb, ms=5)
    ax.add_patch(Rectangle((1.6, 6.75), 0.9, 0.3, fc=BG, ec=cb, lw=1.6, zorder=3)); ax.text(2.05, 7.25, "R5 1 MΩ", color=cb, fontsize=11, ha="center")
    ax.plot([PX(1), 2.5], [6.9, 6.9], color=cb, lw=1.8); ax.plot([1.6, 0.9], [6.9, 6.9], color=cb, lw=1.8)
    ax.plot([0.9, 0.9, 1.95], [6.9, 6.35, 6.35], color=cb, lw=1.8); cap_v(ax, 2.05, 6.35, cb); ax.plot([2.15, PX(1)], [6.35, 6.35], color=cb, lw=1.8)
    ax.text(2.05, 6.0, "C16 1 nF", color=cb, fontsize=11, ha="center")
    ax.plot([0.9, 0.35], [6.9, 6.9], color=cb, lw=1.8); ax.text(0.35, 7.15, "BIAS_DRV", color=cb, fontsize=11)
    ax.plot([PX(3), PX(3)], [3.55, 6.3], color=cb, lw=1.8); ground(ax, PX(3), 6.3, cb, up=True); ax.text(PX(3), 6.6, "AGND", color=cb, fontsize=11, ha="center")


# ---- scenes ----
def s_title(ax, p, t):
    ax.text(8, 8.2, "ADS1299: the top row of pins", color=FG, fontsize=32, ha="center", weight="bold")
    ax.text(8, 7.6, "why 4 bias pins? why so many AVDD / AVSS? what is VCAP3?", color=YEL, fontsize=17, ha="center")
    strip(ax)

def s_overview(ax, p, t):
    title(ax, "Three groups of pins")
    hi = [g for g, a in (("bias", 0.05), ("avdd", 0.3), ("avss", 0.45), ("vcap", 0.7)) if p >= a]
    strip(ax, hi=hi)

def opamp(ax, x, y, s=1.0, c=BIASC):
    ax.add_patch(Polygon([[x, y + 1.6 * s], [x, y], [x + 2.2 * s, y + 0.8 * s]], closed=True, fc=PANEL, ec=c, lw=2.5, zorder=3))
    ax.text(x + 0.25 * s, y + 1.2 * s, "−", color=FG, fontsize=18, va="center", zorder=4); ax.text(x + 0.25 * s, y + 0.4 * s, "+", color=FG, fontsize=18, va="center", zorder=4)

def s_opamp(ax, p, t):
    title(ax, "The bias drive is an op amp inside the chip")
    opamp(ax, 6.2, 3.6, s=1.4)
    show = lambda a: p >= a
    if show(0.1):
        ax.plot([4.4, 6.2], [4.16, 4.16], color=BIASC, lw=2.5)
        ax.text(4.3, 4.3, "BIAS_REF (60) · + input", color=BIASC, fontsize=14, ha="right", va="center", weight="bold")
        ax.text(4.3, 3.85, "the target voltage", color=MU, fontsize=12, ha="right", va="center")
    if show(0.3):
        ax.plot([4.4, 6.2], [5.28, 5.28], color=BIASC, lw=2.5)
        ax.text(4.3, 5.42, "BIAS_INV (61) · − input", color=BIASC, fontsize=14, ha="right", va="center", weight="bold")
        ax.text(4.3, 4.97, "averaged electrodes arrive", color=MU, fontsize=12, ha="right", va="center")
    if show(0.5):
        ax.plot([9.28, 11.0], [4.72, 4.72], color=BIASC, lw=2.5)
        ax.text(11.1, 4.9, "BIAS_OUT (63) · output", color=BIASC, fontsize=14, va="center", weight="bold")
        ax.text(11.1, 4.45, "drives the BIAS electrode", color=MU, fontsize=12, va="center")
    if show(0.62): ax.text(8, 7.3, "same three terminals as your LM358:  +IN · −IN · OUT", color=YEL, fontsize=16, ha="center")
    if show(0.75):
        ax.plot([10.2, 10.2, 11.0], [4.72, 2.6, 2.6], color=VCAPC, lw=2, ls="--")
        ax.text(11.1, 2.78, "BIAS_IN (62) · measure", color=VCAPC, fontsize=14, va="center", weight="bold")
        ax.text(11.1, 2.33, "not part of the amp", color=MU, fontsize=12, va="center")

def s_why4(ax, p, t):
    title(ax, "Q1 · Why four bias pins?")
    cards = [("You choose the feedback parts", "INV + OUT on pins → set loop strength and stability"),
             ("You choose the target", "REF on a pin → the Cyton uses AGND = 0 V, mid-supply"),
             ("You can measure the bias line", "IN → test it, or check the bias electrode touches"),
             ("Chips can share one loop", "16-channel Cyton + Daisy: one amp, 16 electrodes")]
    for i, (a, b) in enumerate(cards):
        if p >= 0.05 + i * 0.2:
            y = 6.6 - i * 1.25
            ax.add_patch(FancyBboxPatch((1.2, y - 0.45), 13.6, 1.0, boxstyle="round,pad=0.05", fc=PANEL, ec=BIASC, lw=1.5))
            ax.text(1.6, y + 0.18, f"{i + 1}.  {a}", color=BIASC, fontsize=17, weight="bold", va="center")
            ax.text(1.95, y - 0.22, b, color=FG, fontsize=14, va="center")

def flow(ax, path, prog, c, n=10):
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]; L = sum(seg)
    for k in range(n):
        d = ((k / n + prog) % 1) * L; acc = 0
        for (a, b), s in zip(zip(path, path[1:]), seg):
            if d <= acc + s:
                tt = (d - acc) / s if s else 0
                ax.plot(a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt, "o", ms=7, color=c, zorder=6); break
            acc += s

def s_loop(ax, p, t):
    title(ax, "The loop closes through your body")
    box(ax, 0.6, 3.4, 2.6, 2.0, "Your body", "shared hum", ec=YEL)
    box(ax, 4.6, 5.9, 3.2, 1.0, "8 electrodes", "→ channel inputs", ec=TEAL)
    box(ax, 9.4, 5.9, 3.6, 1.0, "average → BIAS_INV", "pin 61", ec=BIASC)
    box(ax, 9.4, 3.6, 3.6, 1.0, "bias amp", "+ = BIAS_REF = AGND", ec=BIASC)
    box(ax, 4.6, 1.75, 3.6, 1.0, "BIAS_OUT → R5‖C16", "pin 63 → R6 → electrode", ec=BIASC)
    ax.plot([PX(1) * 0 + 13.4, 13.4], [0, 0], alpha=0)
    path = [(3.2, 5.0), (3.9, 5.0), (3.9, 6.4), (4.6, 6.4), (7.8, 6.4), (9.4, 6.4), (11.2, 6.4), (11.2, 5.9), (11.2, 4.6), (11.2, 3.6),
            (11.2, 2.25), (8.2, 2.25), (4.6, 2.25), (1.9, 2.25), (1.9, 3.4)]
    xs, ys = zip(*path); ax.plot(xs, ys, color=DIM, lw=2, zorder=1)
    flow(ax, path, t * 0.25, BIASC, n=14)
    ax.text(13.3, 3.95, "BIAS_IN tied to BIAS_OUT:\nthe chip can watch\nits own output", color=VCAPC, fontsize=12, va="center")
    tt = np.linspace(0, 1, 200); amp = 1 - 0.85 * ramp(p, 0.35, 0.8)
    ax.add_patch(FancyBboxPatch((13.2, 5.9), 2.5, 1.5, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
    ax.plot(13.3 + tt * 2.3, 6.65 + 0.55 * amp * np.sin(2 * np.pi * 6 * tt), color=YEL, lw=1.6)
    ax.text(14.45, 7.6, "hum on the body", color=MU, fontsize=11, ha="center")

def s_r5(ax, p, t):
    title(ax, "R5 and C16 on the bias output")
    strip(ax, hi=("bias",))
    ax.add_patch(FancyBboxPatch((4.6, 6.0), 7.3, 1.9, boxstyle="round,pad=0.05", fc=PANEL, ec=BIASC, lw=1.5))
    ax.text(4.85, 7.5, "R5 = 1 MΩ: worst case 2.5 V ÷ 1 MΩ ≈ 2.5 µA into you", color=BIASC, fontsize=13, va="center")
    if p > 0.45: ax.text(4.85, 6.9, "C16 = 1 nF: fast changes bypass R5, loop stays stable", color=FG, fontsize=13, va="center")
    if p > 0.75: ax.text(4.85, 6.3, "BIAS_REF → AGND: the loop holds your body at 0 V", color=TEAL, fontsize=13, va="center")

def s_many(ax, p, t):
    title(ax, "Q2 · Why so many AVDD and AVSS pins?")
    for j, (lab, npins) in enumerate((("one power pin", 1), ("many power pins (the real chip)", 6))):
        x0 = 0.5 + j * 7.8
        ax.text(x0 + 3.6, 7.6, lab, color=FG, fontsize=16, ha="center", weight="bold")
        ax.add_patch(Rectangle((x0 + 1.0, 4.0), 5.2, 3.1, fc=PANEL, ec=FG, lw=1.8))
        blocks = [(x0 + 1.4, 6.2), (x0 + 2.7, 6.2), (x0 + 4.0, 6.2), (x0 + 1.4, 4.4), (x0 + 2.7, 4.4), (x0 + 4.0, 4.4)]
        for k, (bx, by) in enumerate(blocks):
            ax.add_patch(Rectangle((bx, by), 1.0, 0.55, fc=BG, ec=AVDDC if j else MU, lw=1.2))
            ax.text(bx + 0.5, by + 0.27, f"CH{k + 1}" if k < 5 else "ref", color=FG, fontsize=10, ha="center", va="center")
        pins = [(x0 + 1.0, 5.55)] if npins == 1 else [(x0 + 1.9, 7.1), (x0 + 3.2, 7.1), (x0 + 4.5, 7.1), (x0 + 1.9, 4.0), (x0 + 3.2, 4.0), (x0 + 4.5, 4.0)]
        for (px, py) in pins:
            ax.plot(px, py, "s", color=AVDDC, ms=9, zorder=4)
        for k, (bx, by) in enumerate(blocks):
            src = pins[0] if npins == 1 else pins[k]
            ax.plot([src[0], bx + 0.5], [src[1], by + 0.27], color=AVDDC, lw=1, alpha=0.6)
            if p > 0.25:
                pr = (t * 0.6 + k * 0.17) % 1
                ax.plot(src[0] + (bx + 0.5 - src[0]) * pr, src[1] + (by + 0.27 - src[1]) * pr, "o", color=AVDDC, ms=5, zorder=5)
        ax.add_patch(FancyBboxPatch((x0 + 0.6, 1.7), 6.0, 1.8, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
        ax.text(x0 + 0.75, 3.3, "supply at the chip when it draws a burst", color=MU, fontsize=10.5, va="center")
        if p > 0.45:
            tt = np.linspace(0, 1, 300); bursts = (np.sin(2 * np.pi * 9 * tt + t * 4) > 0.6).astype(float)
            bounce = (0.75 if j == 0 else 0.12) * bursts * np.exp(-((tt * 9 + t * 4 / (2 * np.pi)) % 1) * 4)
            ax.plot(x0 + 0.8 + tt * 5.6, 2.6 - bounce, color=RED if j == 0 else TEAL, lw=1.8)
            ax.text(x0 + 3.6, 1.85, "big bounce → noise" if j == 0 else "tiny bounce", color=RED if j == 0 else TEAL, fontsize=12, ha="center", weight="bold")

def s_decouple(ax, p, t):
    title(ax, "Same two rails, capacitors at the pins")
    strip(ax, hi=("avdd", "avss"))
    ax.add_patch(FancyBboxPatch((4.8, 6.0), 7.0, 1.9, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1.2))
    ax.text(5.3, 7.5, "6 AVDD pins → one +2.5 V rail", color=AVDDC, fontsize=15, va="center")
    ax.text(5.3, 6.95, "5 AVSS pins → one −2.5 V rail", color=AVSSC, fontsize=15, va="center")
    if p > 0.5: ax.text(5.3, 6.4, "+ decoupling pairs (C12–C28) by net name", color=FG, fontsize=13.5, va="center")

def s_vcap(ax, p, t):
    title(ax, "Q3 · What is VCAP3?")
    ax.add_patch(Rectangle((0.8, 3.0), 6.6, 4.3, fc=PANEL, ec=FG, lw=1.8)); ax.text(1.0, 7.0, "inside the ADS1299", color=MU, fontsize=12)
    box(ax, 1.5, 4.4, 3.8, 1.5, "internal circuit", "needs a reservoir", ec=VCAPC)
    ax.plot([5.3, 7.4], [5.15, 5.15], color=VCAPC, lw=2.2); ax.plot(7.4, 5.15, "s", color=VCAPC, ms=10)
    ax.text(7.55, 5.45, "VCAP3 (pin 55)", color=VCAPC, fontsize=14, weight="bold")
    with_cap = p > 0.5
    if with_cap:
        ax.plot([7.4, 9.0], [5.15, 5.15], color=VCAPC, lw=2.2); cap_h(ax, 9.0, 4.75, VCAPC)
        ax.plot([9.0, 9.0], [5.15, 4.81], color=VCAPC, lw=2.2); ax.plot([9.0, 9.0], [4.69, 4.2], color=VCAPC, lw=2.2)
        ax.text(9.35, 4.75, "C19 1 µF ‖ C15 0.1 µF", color=VCAPC, fontsize=13, va="center"); ax.text(9.0, 3.95, "AVSS", color=AVSSC, fontsize=12, ha="center")
    ax.add_patch(FancyBboxPatch((9.0, 5.85), 6.6, 1.9, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
    ax.text(9.15, 7.55, "voltage on the internal node", color=MU, fontsize=11, va="center")
    tt = np.linspace(0, 1, 300); k = int(t * 30) % 5000
    n = NOISE[k:k + 300]
    v = (np.convolve(n, np.ones(40) / 40, mode="same") * 0.25) if with_cap else n * 0.35
    ax.plot(9.2 + tt * 6.2, 6.7 + v, color=TEAL if with_cap else RED, lw=1.5)
    ax.text(12.3, 6.05, "steady (with the capacitors)" if with_cap else "wobbles (no capacitor)", color=TEAL if with_cap else RED, fontsize=12.5, ha="center", weight="bold")
    ax.text(0.9, 2.45, "not a supply input · the datasheet asks for 1 µF ‖ 0.1 µF to AVSS", color=FG, fontsize=14)

def s_end(ax, p, t):
    ax.text(8, 7.5, "Three answers", color=FG, fontsize=32, ha="center", weight="bold")
    rows = [("4 bias pins", "the bias op amp's + (REF), − (INV) and output (OUT) are yours to set, plus IN to measure", BIASC),
            ("Many AVDD / AVSS", "feed every part of the chip from close by, many pins in parallel → tiny bounce", AVDDC),
            ("VCAP3", "a pin to an internal circuit that needs its capacitors: 1 µF ‖ 0.1 µF to AVSS", VCAPC)]
    for i, (a, b, c) in enumerate(rows):
        if p > 0.08 + i * 0.22:
            y = 6.2 - i * 1.4
            ax.text(1.2, y, a, color=c, fontsize=19, weight="bold", va="center")
            ax.text(1.2, y - 0.5, b, color=FG, fontsize=15, va="center")


SCENES = [
 ("This strip of the Cyton schematic is the top row of the A D S twelve ninety nine's pins. It answers three questions: why there are four bias pins, why there are so many A V D D and A V S S pins, and what V CAP three is.", s_title),
 ("There are three groups. On the left, four bias pins. In the middle, many analog power pins: A V D D at plus two point five volts, and A V S S at minus two point five. And on the right, V CAP three, connected to two capacitors.", s_overview),
 ("The bias drive is an op amp inside the chip, and the A D S twelve ninety nine gives you a pin for each of its terminals. Bias ref is the plus input: the target voltage. Bias inv is the minus input, where the averaged electrode signals arrive. Bias out is the output, which drives the bias electrode. These are the same three terminals as your L M three fifty eight. The fourth pin, bias in, isn't part of the amplifier. It's a measuring input.", s_opamp),
 ("So why put them all on pins? First, so you can choose the feedback parts that set the loop's strength and stability. Second, so you can choose the target: the Cyton ties bias ref to analog ground, zero volts, the middle of its supply. Third, bias in lets the chip measure the bias line, to test it, or to check that the bias electrode is touching. And fourth, two chips can share one bias loop, as on the sixteen channel Cyton with Daisy.", s_why4),
 ("Here's the loop on the Cyton. The electrodes pick up the hum your whole body shares. The chip averages them into bias inv. The amplifier compares that with zero volts, and bias out pushes the opposite back into your body through the bias electrode. The hum shrinks. Bias in is tied to bias out, so the chip can watch its own output.", s_loop),
 ("Between bias out and the electrode sit R five and C sixteen. R five, one megohm, limits the current into your body to about two and a half microamps, even in the worst case. C sixteen, one nanofarad, lets faster changes bypass R five, which keeps the loop stable.", s_r5),
 ("Now, why so many power pins? The analog circuits for eight channels and the reference are spread across the chip. If they all shared one pin, their current would crowd through it, and every burst would make the supply bounce, adding noise. Power pins on every side feed each part from close by, and many pins in parallel have far less resistance and inductance, so the supply barely moves.", s_many),
 ("All six A V D D pins join one plus two point five volt rail, and all five A V S S pins join one minus two point five volt rail. Capacitors sit right at the pins: C twenty one and C eighteen on A V S S here, plus the decoupling pairs, connected by net name.", s_decouple),
 ("Finally, V CAP three. It's not a supply input. It connects to a circuit inside the chip that needs an external capacitor as a reservoir, to stay stable and quiet. The datasheet asks for one microfarad in parallel with point one microfarad, to A V S S. On the Cyton that's C nineteen and C fifteen. Without them, the internal voltage would wobble and add noise to every channel.", s_vcap),
 ("So: four bias pins, because the bias amplifier's inputs and output are yours to configure, plus one pin to measure. Many power pins, to feed every part of the chip from close by with almost no bounce. And V CAP three, a pin that simply needs its capacitors.", s_end),
]


def main():
    tmp = tempfile.mkdtemp(); wavs, durs = [], []
    for i, (text, _) in enumerate(SCENES):
        aiff, wav = os.path.join(tmp, f"s{i}.aiff"), os.path.join(tmp, f"s{i}.wav")
        subprocess.run(["say", "-v", VOICE, "-r", "165", "-o", aiff, text], check=True)
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", aiff]).strip()) + 0.9
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff, "-af", "apad", "-t", f"{d:.3f}", "-ar", "44100", "-ac", "1", wav], check=True)
        wavs.append(wav); durs.append(d)
    lst = os.path.join(tmp, "list.txt"); open(lst, "w").write("".join(f"file '{w}'\n" for w in wavs))
    narration = os.path.join(tmp, "narration.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", narration], check=True)
    silent = os.path.join(tmp, "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", silent], stdin=subprocess.PIPE)
    for (text, draw), d in zip(SCENES, durs):
        n = int(round(d * FPS))
        for k in range(n):
            fig, ax = new_fig(); p = k / max(1, n - 1); draw(ax, p, k / FPS); caption(ax, text, p)
            fig.canvas.draw(); ff.stdin.write(fig.canvas.buffer_rgba().tobytes()); plt.close(fig)
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", narration, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", "-movflags", "+faststart", OUT], check=True)
    print("saved", OUT, f"{sum(durs):.0f} s")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stills":
        d = sys.argv[2] if len(sys.argv) > 2 else "."
        for i, (text, draw) in enumerate(SCENES):
            fig, ax = new_fig(); draw(ax, 0.85, 3.3); caption(ax, text, 0.85)
            fig.savefig(os.path.join(d, f"tp{i}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
