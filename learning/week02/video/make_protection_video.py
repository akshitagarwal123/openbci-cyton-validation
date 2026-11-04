"""Narrated video: the Cyton's input protection block (TVS + 2.2 kOhm + 1 nF on every electrode line).
Zap clamped by the TVS, current limited by the resistor, radio filtered by the RC, parts packed 4 to a package,
the group mapping on the Cyton sheet, and why matched C0G capacitors (rev A) keep CMRR high.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_protection_video.py -> input_protection.mp4
Preview frames: python make_protection_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_protection.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
RED, AMB, TEAL, PUR, YEL, BLUE = "#ef5b5b", "#ffb347", "#2ec4a0", "#a77bff", "#ffd166", "#5aa9ff"


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
def box(ax, x, y, w, h, t1, t2="", ec=FG, c1=FG, fc=PANEL, fs=15):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec=ec, lw=2, zorder=3))
    ax.text(x + w / 2, y + h / 2 + (0.17 if t2 else 0), t1, color=c1, fontsize=fs, ha="center", va="center", weight="bold", zorder=4)
    if t2: ax.text(x + w / 2, y + h / 2 - 0.24, t2, color=MU, fontsize=11.5, ha="center", va="center", zorder=4)
def ground(ax, x, y, c=FG):
    for i, w in enumerate((0.3, 0.19, 0.08)): ax.plot([x - w, x + w], [y - i * 0.1] * 2, color=c, lw=2)
def panel(ax, x0, y0, w, h, label):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
    ax.text(x0 + 0.12, y0 + h - 0.2, label, color=MU, fontsize=11, va="center")


# ---- one channel (shared by several scenes) ----
WY = 4.9
def chain(ax, hi=(), tvs_glow=0.0, dots=None):
    box(ax, 0.3, WY - 0.5, 1.9, 1.0, "Electrode", "header pin", ec=YEL if "hdr" in hi else FG)
    ax.plot([2.2, 12.5], [WY, WY], color=FG, lw=2.2, zorder=2)
    # TVS
    tc = RED if ("tvs" in hi or tvs_glow > 0) else FG
    ax.plot(3.8, WY, "o", color=FG, ms=6); ax.plot([3.8, 3.8], [WY, 4.0], color=tc, lw=2)
    box(ax, 3.2, 3.2, 1.2, 0.8, "TVS", ec=tc, c1=tc, fc=RED if tvs_glow > 0.5 else PANEL)
    ax.plot([3.8, 3.8], [3.2, 2.75], color=tc, lw=2); ground(ax, 3.8, 2.75, tc)
    # resistor
    rc = AMB if "res" in hi else FG
    box(ax, 5.4, WY - 0.3, 1.9, 0.6, "2.2 kΩ", ec=rc, c1=rc)
    # capacitor
    cc = TEAL if "cap" in hi else FG
    ax.plot(9.0, WY, "o", color=FG, ms=6); ax.plot([9.0, 9.0], [WY, 4.0], color=cc, lw=2)
    box(ax, 8.4, 3.2, 1.2, 0.8, "1 nF", ec=cc, c1=cc)
    ax.plot([9.0, 9.0], [3.2, 2.75], color=cc, lw=2); ground(ax, 9.0, 2.75, cc)
    box(ax, 12.5, WY - 0.5, 2.6, 1.0, "ADS1299", "input pin", ec=PUR)
    for x, s, c in ((3.8, "1 · lightning rod", RED), (6.35, "2 · speed bump", AMB), (9.0, "3 · radio filter", TEAL)):
        ax.text(x, 2.05, s, color=c if any(k in hi for k in ("tvs", "res", "cap")) else MU, fontsize=13, ha="center")
    if dots:
        for path, prog, c, n in dots:
            seg = [math.dist(a, b) for a, b in zip(path, path[1:])]; L = sum(seg)
            for k in range(n):
                d = ((k / n + prog) % 1) * L; acc = 0
                for (a, b), s in zip(zip(path, path[1:]), seg):
                    if d <= acc + s:
                        tt = (d - acc) / s if s else 0
                        ax.plot(a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt, "o", ms=7, color=c, zorder=6); break
                    acc += s


# ---- scenes ----
def s_title(ax, p, t):
    ax.text(8, 7.6, "The input protection block", color=FG, fontsize=34, ha="center", weight="bold")
    ax.text(8, 6.95, "every wire from your head, before it reaches the ADS1299", color=MU, fontsize=17, ha="center")
    chain(ax)

def s_where(ax, p, t):
    title(ax, "About 20 lines come in")
    box(ax, 0.5, 2.3, 2.6, 4.8, "Electrode", "header", ec=YEL)
    labels = ["1P 1N", "2P 2N", "3P 3N", "4P 4N", "5P 5N", "6P 6N", "7P 7N", "8P 8N", "SRB1 SRB2", "BIAS"]
    n = int(ramp(p, 0.05, 0.6) * 10.99)
    for i, s in enumerate(labels[:n]):
        y = 6.75 - i * 0.44
        ax.plot([3.1, 9.6], [y, y], color=BLUE, lw=1.6); ax.text(3.3, y + 0.12, s, color=FG, fontsize=11)
    ax.add_patch(Rectangle((6.0, 2.3), 2.0, 4.8, fc=PANEL, ec=RED, lw=2, zorder=3))
    ax.text(7.0, 4.7, "protection\nblock", color=RED, fontsize=15, ha="center", va="center", weight="bold", zorder=4)
    box(ax, 9.6, 2.3, 2.8, 4.8, "ADS1299", ec=PUR)
    if p > 0.6: ax.text(13.0, 5.0, "8 channels × P, N\n+ SRB1, SRB2, BIAS\n≈ 20 lines", color=FG, fontsize=15, va="center")

def s_chain(ax, p, t):
    title(ax, "Three parts on every line")
    order = ["hdr", "tvs", "res", "cap"]
    k = int(ramp(p, 0.05, 0.85) * 3.99)
    chain(ax, hi=tuple(order[1:k + 1]))

def s_tvs(ax, p, t):
    title(ax, "1 · The TVS diode: a lightning rod")
    hit = ramp(p, 0.25, 0.4)
    glow = 1.0 if 0.38 < p < 0.75 else 0.0
    dots = []
    if 0.25 < p < 0.4: dots.append(([(1.2, WY + 0.5), (2.2, WY), (3.8, WY)], t * 1.5, RED, 6))
    if glow: dots.append(([(3.8, WY), (3.8, 2.75)], t * 1.2, RED, 6))
    chain(ax, hi=("tvs",), tvs_glow=glow, dots=dots)
    panel(ax, 9.3, 6.25, 6.3, 1.8, "voltage during a static zap")
    tt = np.linspace(0, 1, 300)
    spike = 8000 * np.exp(-((tt - 0.3) / 0.05) ** 2)
    clamp = np.minimum(spike, 10)
    X = lambda u: 9.5 + u * 5.9
    Ylog = lambda v: 6.4 + np.log10(1 + v) / np.log10(9000) * 1.35
    upto = int(300 * ramp(p, 0.2, 0.7))
    if upto > 1:
        ax.plot(X(tt[:upto]), Ylog(spike[:upto]), color=RED, lw=2); ax.plot(X(tt[:upto]), Ylog(clamp[:upto]), color=TEAL, lw=2.4)
    ax.text(15.5, 7.5, "at the electrode: ~8,000 V", color=RED, fontsize=11, ha="right")
    ax.text(15.5, 6.65, "after the TVS: ~10 V", color=TEAL, fontsize=11, ha="right")
    ax.text(0.4, 7.7, "normally invisible · on a zap: switches on in nanoseconds" if hit else "normally: does nothing", color=RED if glow else MU, fontsize=15)

def s_res(ax, p, t):
    title(ax, "2 · The 2.2 kΩ resistor: a speed bump")
    dots = [([(3.8, WY), (12.5, WY)], t * 0.4, AMB, 5)] if p > 0.15 else []
    chain(ax, hi=("res",), dots=dots)
    ax.text(0.4, 7.7, "limits current into the ADS1299's own small protection diodes", color=AMB, fontsize=15)
    if p > 0.35: ax.text(0.4, 7.15, "I = V / R = 10 V / 2.2 kΩ ≈ 4.5 mA  (safe)", color=FG, fontsize=15)
    if p > 0.65: ax.text(0.4, 6.6, "on the BIAS line: also limits current into your body", color=YEL, fontsize=15)

def s_filter(ax, p, t):
    title(ax, "3 · Resistor + capacitor: a radio filter")
    chain(ax, hi=("res", "cap"))
    panel(ax, 0.4, 5.85, 15.2, 2.15, "how much gets through (cutoff ≈ 72 kHz)")
    fc = 1 / (2 * math.pi * 2200 * 1e-9)
    L0, L1 = 0, 10                                             # log10 Hz range
    X = lambda lf: 1.2 + (lf - L0) / (L1 - L0) * 13.8
    lfs = np.linspace(L0, L1, 300); gains = 1 / np.sqrt(1 + (10 ** lfs / fc) ** 2)
    Y = lambda g: 6.0 + g * 1.45
    ax.plot(X(lfs), Y(gains), color=TEAL, lw=2.4)
    for lf, s in ((1, "10 Hz EEG"), (math.log10(fc), "72 kHz"), (math.log10(9e8), "phone"), (math.log10(2.4e9), "Wi-Fi")):
        ax.plot([X(lf)] * 2, [6.0, 7.5], color=DIM, lw=1, ls="--"); ax.text(X(lf), 5.72, s, color=MU, fontsize=10.5, ha="center", va="center")
    lf = L0 + (L1 - L0) * ramp(p, 0.1, 0.9); g = 1 / math.sqrt(1 + (10 ** lf / fc) ** 2)
    ax.plot(X(lf), Y(g), "o", color=YEL, ms=11, zorder=5)
    f = 10 ** lf; fs = f"{f / 1e9:.1f} GHz" if f >= 1e9 else f"{f / 1e6:.1f} MHz" if f >= 1e6 else f"{f / 1e3:.1f} kHz" if f >= 1e3 else f"{f:.0f} Hz"
    ax.text(12.4, 3.35, f"{fs}:  {g * 100:.1f}% passes" if g > 0.001 else f"{fs}:  blocked", color=TEAL if g > 0.5 else RED, fontsize=15, weight="bold", ha="center")

def quad(ax, x, y, kind, c):
    ax.add_patch(FancyBboxPatch((x, y), 2.6, 3.0, boxstyle="round,pad=0.05", fc=PANEL, ec=c, lw=2))
    for i in range(4):
        yy = y + 2.55 - i * 0.68
        ax.plot([x - 0.4, x + 0.5], [yy, yy], color=FG, lw=1.6); ax.plot([x + 2.1, x + 3.0], [yy, yy], color=FG, lw=1.6)
        if kind == "R":
            zx = np.linspace(x + 0.5, x + 2.1, 13); zy = yy + np.array([0, .15, -.15] * 4 + [0])[:13]
            ax.plot(zx, zy, color=c, lw=2)
        elif kind == "C":
            ax.plot([x + 0.5, x + 1.2], [yy, yy], color=c, lw=2); ax.plot([x + 1.2, x + 1.2], [yy - .2, yy + .2], color=c, lw=3)
            ax.plot([x + 1.4, x + 1.4], [yy - .2, yy + .2], color=c, lw=3); ax.plot([x + 1.4, x + 2.1], [yy, yy], color=c, lw=2)
        else:
            ax.plot([x + 0.5, x + 2.1], [yy, yy], color=c, lw=2)
            ax.add_patch(Polygon([[x + 1.05, yy - .2], [x + 1.05, yy + .2], [x + 1.35, yy]], closed=True, fc=c, ec=c))
            ax.add_patch(Polygon([[x + 1.65, yy - .2], [x + 1.65, yy + .2], [x + 1.35, yy]], closed=True, fc=c, ec=c))

def s_arrays(ax, p, t):
    title(ax, "Four in one package")
    for i, (kind, c, name, part) in enumerate((("T", RED, "Quad TVS", "TPD4E1B06"), ("R", AMB, "4 × 2.2 kΩ", "CAY16-F4"), ("C", TEAL, "4 × 1 nF", "CKCL44"))):
        if p > 0.05 + i * 0.15:
            x = 1.4 + i * 4.6; quad(ax, x, 3.3, kind, c)
            ax.text(x + 1.3, 6.65, name, color=c, fontsize=16, ha="center", weight="bold"); ax.text(x + 1.3, 2.85, part, color=MU, fontsize=12, ha="center")
    if p > 0.6:
        ax.text(14.2, 5.6, "≈ 20 lines", color=FG, fontsize=18, ha="center"); ax.text(14.2, 4.9, "÷ 4 = 5 groups", color=FG, fontsize=18, ha="center")
        ax.text(14.2, 4.0, "15 parts", color=TEAL, fontsize=22, ha="center", weight="bold"); ax.text(14.2, 3.4, "instead of ~60", color=MU, fontsize=15, ha="center")

def s_groups(ax, p, t):
    title(ax, "On the Cyton sheet")
    rows = [("D2", "R1", "C3", "1P, 1N, SRB1, SRB2"), ("D3", "R2", "C9", "2P, 2N, 3P, 3N"), ("D4", "R3", "C11", "4P, 4N, 5P, 5N"),
            ("D5", "R4", "C26", "6P, 6N, 7P, 7N"), ("D6", "R6", "C34", "8P, 8N, BIAS → BIAS_DRV"), ("D7", "–", "–", "header BIAS, AVDD, AGND pins")]
    for j, (h, x) in enumerate((("TVS", 2.0), ("Resistors", 4.3), ("Caps", 6.6), ("Lines protected", 9.0))):
        ax.text(x, 7.3, h, color=MU, fontsize=15, weight="bold")
    for i, r in enumerate(rows):
        if p > 0.05 + i * 0.13:
            y = 6.6 - i * 0.72
            for (x, c), s in zip(((2.0, RED), (4.3, AMB), (6.6, TEAL), (9.0, FG)), r): ax.text(x, y, s, color=c, fontsize=17)

def lp(sig, fc, fs):
    a = 1 / (1 + fs / (2 * math.pi * fc)); out = np.zeros_like(sig); y = 0.0
    for i, s in enumerate(sig): y += a * (s - y); out[i] = y
    return out
def s_cmrr(ax, p, t):
    title(ax, "One weakness: mismatched capacitors")
    fs = 6e6; tt = np.arange(0, 2.4e-4, 1 / fs); f = 60e3
    hum = np.sin(2 * np.pi * f * tt)
    cy = (lp(hum, 1 / (2 * math.pi * 2200 * 1.2e-9), fs), lp(hum, 1 / (2 * math.pi * 2200 * 0.8e-9), fs))
    ra = (lp(hum, 1 / (2 * math.pi * 2200 * 47.9e-12), fs), lp(hum, 1 / (2 * math.pi * 2200 * 46.1e-12), fs))
    sel = int(len(tt) * 0.3)
    xs = np.linspace(0, 1, len(tt) - sel)
    for j, ((p1, n1), lab, sub) in enumerate(((cy, "Cyton: 1.2 nF vs 0.8 nF", "±20% X7R"), (ra, "rev A: 47.9 pF vs 46.1 pF", "±2% C0G"))):
        x0 = 0.6 + j * 7.8; show = p > 0.08 + j * 0.45
        if not show: continue
        panel(ax, x0, 2.0, 7.2, 5.9, lab)
        ax.text(x0 + 7.05, 7.7, sub, color=MU, fontsize=11, ha="right", va="center")
        X = lambda u: x0 + 0.3 + u * 6.6
        ax.plot(X(xs), 6.4 + 0.6 * p1[sel:], color=BLUE, lw=1.8); ax.text(x0 + 0.35, 7.25, "P wire after filter", color=BLUE, fontsize=11)
        ax.plot(X(xs), 4.6 + 0.6 * n1[sel:], color=AMB, lw=1.8); ax.text(x0 + 0.35, 5.45, "N wire after filter", color=AMB, fontsize=11)
        d = p1[sel:] - n1[sel:]
        ax.plot(X(xs), 2.85 + 1.6 * d, color=RED if j == 0 else TEAL, lw=2.2)
        ax.text(x0 + 0.35, 3.7, "P − N  (what the ADS1299 measures)", color=RED if j == 0 else TEAL, fontsize=11)
        ax.text(x0 + 3.6, 2.2, "fake signal!" if j == 0 else "≈ zero: rejected", color=RED if j == 0 else TEAL, fontsize=14, ha="center", weight="bold")

def s_end(ax, p, t):
    ax.text(8, 7.4, "Lightning rod · speed bump · radio filter", color=FG, fontsize=30, ha="center", weight="bold")
    pts = [("TVS: diverts static zaps to ground in nanoseconds", RED), ("2.2 kΩ: limits current into the chip, and into you", AMB),
           ("R + C: blocks radio, EEG passes untouched", TEAL), ("BrainTech-8: keep all three, use quad arrays,", YEL), ("and small, tightly matched C0G capacitors", YEL)]
    for i, (s, c) in enumerate(pts):
        if p > 0.1 + i * 0.12: ax.text(2.0, 6.2 - i * 0.75, ("•  " if i < 4 else "    ") + s, color=c, fontsize=18)


SCENES = [
 ("Every wire from your head passes through a protection block before it reaches the A D S twelve ninety nine. Let's see what each part does.", s_title),
 ("On the Cyton, about twenty lines come in from the electrode header: eight channels with P and N inputs, plus the two S R B pins and bias. Each line passes through the same three parts.", s_where),
 ("First, a T V S diode to ground. Then a two point two kilo-ohm resistor in series. Then a one nanofarad capacitor to ground. Then the A D S twelve ninety nine's input pin.", s_chain),
 ("The T V S diode is a lightning rod. Normally it does nothing at all. But when a static zap of thousands of volts hits an electrode, it switches on within nanoseconds and dumps the energy to ground. What's left is clamped to just a few volts.", s_tvs),
 ("The two point two kilo-ohm resistor is a speed bump. It limits the current from whatever gets past the T V S, into the chip's own tiny protection diodes. On the bias line, it also limits any current that could flow into your body if something fails.", s_res),
 ("Together, the resistor and the one nanofarad capacitor form a low pass filter, with a cutoff near seventy two kilohertz. Brain signals, below a hundred hertz, pass completely untouched. Phone and Wi-Fi signals, at gigahertz, are shunted to ground before the A D S twelve ninety nine can turn them into noise.", s_filter),
 ("Each part comes four to a package: a quad T V S, a four resistor array, and a four capacitor array. Twenty lines need only five groups: about fifteen parts instead of sixty. That's a great trick for a compact board.", s_arrays),
 ("On the Cyton sheet, D two, R one and C three protect channel one and the S R B pins. D three to D six cover channels two to eight and bias, and D seven protects the header's bias and supply pins.", s_groups),
 ("One weakness. The Cyton's capacitors can vary by twenty percent. If the P and N capacitors differ, the same interference on both wires is filtered differently, and the difference looks like a real signal. That weakens common mode rejection. Your rev A design uses forty seven picofarad C zero G capacitors, matched within two percent, so both wires are filtered almost identically.", s_cmrr),
 ("So the protection block is a lightning rod, a speed bump, and a radio filter on every line. For BrainTech eight, keep all three, use the four in one arrays to save space, and use small, tightly matched capacitors.", s_end),
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
            fig, ax = new_fig(); draw(ax, 0.55, 3.3); caption(ax, text, 0.55)
            fig.savefig(os.path.join(d, f"pr{i}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
