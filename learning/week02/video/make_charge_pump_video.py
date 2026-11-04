"""Narrated video: how the Cyton's voltage inverter (U3, LM2664 charge pump) makes -RAW from DVDD.
Redraws the schematic, opens the chip to show its 4 switches, animates charge -> flip -> repeat,
plots -RAW settling near -3.3 V, then shows why a -2.5 V regulator follows.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_charge_pump_video.py -> charge_pump_inverter.mp4
Preview frames: python make_charge_pump_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Arc

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charge_pump_inverter.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM = "#0b1730", "#eef2f7", "#8a97ab", "#33415c"
TEAL, CORAL, YEL, RED = "#2ec4a0", "#ff8a5c", "#ffd166", "#ef5b5b"
VIN = 3.3

# ---- circuit geometry (axes units: 16 x 9) ----
BOX = (5.0, 2.6, 4.8, 4.0)                      # U3 outline x, y, w, h
Y_TOP, Y_MID, Y_BOT = 6.0, 4.9, 3.2             # CAP+/V+, CAP-/SD, GND/OUT rows
GND_Y = 1.95
C31_X, C33_X = 3.4, 11.4
SW = {  # internal switches: (a, b) endpoints of the switch gap
    "S1": ((9.0, Y_TOP), (8.3, Y_TOP)),         # V+  -> CAP+
    "S2": ((6.0, 4.4), (6.0, 3.75)),            # CAP- -> GND
    "S3": ((7.6, 4.45), (7.6, 3.8)),            # CAP+ -> GND
    "S4": ((8.8, 4.4), (8.8, 3.75)),            # CAP- -> OUT
}
CHARGE_PATH = [(14.6, Y_TOP), (9.8, Y_TOP), (8.3, Y_TOP), (5.0, Y_TOP), (C31_X, Y_TOP), (C31_X, 5.62),
               (C31_X, 5.28), (C31_X, Y_MID), (5.0, Y_MID), (6.0, Y_MID), (6.0, Y_BOT), (5.0, Y_BOT),
               (4.2, Y_BOT), (4.2, GND_Y), (7.4, GND_Y)]
FLIP_OUT = [(C31_X, 5.28), (C31_X, Y_MID), (5.0, Y_MID), (8.8, Y_MID), (8.8, Y_BOT), (9.8, Y_BOT), (C33_X, Y_BOT), (C33_X, 2.6)]
FLIP_GND = [(C31_X, 5.62), (C31_X, Y_TOP), (5.0, Y_TOP), (7.6, Y_TOP), (7.6, Y_BOT), (5.0, Y_BOT), (4.2, Y_BOT), (4.2, GND_Y), (7.4, GND_Y)]


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
    ax.text(8, 0.35, "\n".join(textwrap.wrap(sentence_at(text, p), 92)), color=FG, fontsize=17, ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.45", fc="#14254a", ec="none"))
def title(ax, s): ax.text(0.4, 8.45, s, color=FG, fontsize=24, weight="bold", va="center")


def line(ax, pts, c=FG, lw=2, a=1.0):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=c, lw=lw, alpha=a, solid_capstyle="round", zorder=2)
def ground(ax, x, y, c=FG):
    for i, w in enumerate((0.35, 0.22, 0.09)): ax.plot([x - w, x + w], [y - i * 0.12] * 2, color=c, lw=2)
def cap_h(ax, x, ytop, ybot, c=FG):                     # vertical capacitor drawn as two horizontal plates
    ax.plot([x - 0.5, x + 0.5], [ytop] * 2, color=c, lw=3.5); ax.plot([x - 0.5, x + 0.5], [ybot] * 2, color=c, lw=3.5)
def switch(ax, name, closed, c):
    (x1, y1), (x2, y2) = SW[name]
    for x, y in ((x1, y1), (x2, y2)): ax.plot(x, y, "o", ms=6, mfc=BG, mec=c, mew=1.8, zorder=4)
    if closed: ax.plot([x1, x2], [y1, y2], color=c, lw=3, zorder=3)
    elif x1 == x2: ax.plot([x1, x1 + 0.38], [y1, y2 + 0.08], color=c, lw=2.2, zorder=3)
    else: ax.plot([x1, x2 + 0.06], [y1, y1 + 0.38], color=c, lw=2.2, zorder=3)
    lx, ly = ((x1 + x2) / 2, y1 + 0.28) if y1 == y2 else (x1 - 0.18, (y1 + y2) / 2)
    ax.text(lx, ly, name, color=c, fontsize=12, ha="center" if y1 == y2 else "right", va="center", zorder=5)
def flow(ax, path, prog, c, n=14):
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]; L = sum(seg)
    for k in range(n):
        d = ((k / n + prog) % 1) * L; acc = 0
        for (a, b), s in zip(zip(path, path[1:]), seg):
            if d <= acc + s:
                t = (d - acc) / s if s else 0
                ax.plot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, "o", ms=7, color=c, zorder=6); break
            acc += s


def circuit(ax, inside=False, sw=(), hi=(), plates=None, flows=(), out_v=None, tag_alpha=1.0, short_out=False):
    """Draw the schematic. hi: names to highlight ('vin','sd','c31','out','c33','gnd')."""
    col = lambda k, base=FG: YEL if k in hi else base
    x, y, w, h = BOX
    ax.add_patch(Rectangle((x, y), w, h, fc="#0f1f3d", ec=FG, lw=2, zorder=1))
    if not inside:
        ax.text(x + w / 2, y + h / 2 + 0.25, "U3", color=FG, fontsize=15, ha="center")
        ax.text(x + w / 2, y + h / 2 - 0.25, "LM2664", color=MU, fontsize=13, ha="center")
    for yy, nm, pin in ((Y_TOP, "CAP+", 6), (Y_MID, "CAP−", 3), (Y_BOT, "GND", 1)):
        ax.text(x + 0.12, yy, nm, color=MU, fontsize=11, va="center"); ax.text(x - 0.2, yy + 0.18, str(pin), color=MU, fontsize=10, ha="right")
    for yy, nm, pin in ((Y_TOP, "V+", 5), (Y_MID, "SD", 4), (Y_BOT, "OUT", 2)):
        ax.text(x + w - 0.12, yy, nm, color=MU, fontsize=11, va="center", ha="right"); ax.text(x + w + 0.2, yy + 0.18, str(pin), color=MU, fontsize=10)
    # outside wiring
    line(ax, [(14.6, Y_TOP), (x + w, Y_TOP)], col("vin")); line(ax, [(C33_X, Y_TOP), (C33_X, Y_MID), (x + w, Y_MID)], col("sd"))
    ax.plot(C33_X, Y_TOP, "o", color=col("sd"), ms=6)
    ax.annotate("", xy=(14.9, Y_TOP), xytext=(14.6, Y_TOP), arrowprops=dict(arrowstyle="->", color=col("vin"), lw=2))
    ax.text(15.0, Y_TOP + 0.3, "DVDD", color=col("vin"), fontsize=14, ha="right"); ax.text(15.0, Y_TOP - 0.42, "+3.3 V in", color=col("vin", MU), fontsize=12, ha="right")
    line(ax, [(x, Y_TOP), (C31_X, Y_TOP), (C31_X, 5.62)], col("c31")); line(ax, [(C31_X, 5.28), (C31_X, Y_MID), (x, Y_MID)], col("c31"))
    cap_h(ax, C31_X, 5.62, 5.28, col("c31")); ax.text(C31_X - 0.75, 5.45, "C31\n10 µF", color=col("c31", MU), fontsize=12, ha="right", va="center")
    out_end = 12.3 if short_out else 14.6
    line(ax, [(x + w, Y_BOT), (out_end, Y_BOT)], col("out")); ax.plot(C33_X, Y_BOT, "o", color=col("out"), ms=6)
    if not short_out:
        ax.annotate("", xy=(14.9, Y_BOT), xytext=(14.6, Y_BOT), arrowprops=dict(arrowstyle="->", color=col("out"), lw=2))
        ax.text(15.0, Y_BOT + 0.3, "−RAW", color=col("out"), fontsize=14, ha="right")
        if out_v is not None: ax.text(15.0, Y_BOT - 0.42, f"{out_v:+.2f} V".replace("-", "−"), color=CORAL, fontsize=14, ha="right", weight="bold")
    line(ax, [(C33_X, Y_BOT), (C33_X, 2.6)], col("c33")); line(ax, [(C33_X, 2.3), (C33_X, GND_Y)], col("c33"))
    cap_h(ax, C33_X, 2.6, 2.3, col("c33")); ax.text(C33_X + 0.7, 2.45, "C33  10 µF", color=col("c33", MU), fontsize=12, va="center")
    line(ax, [(x, Y_BOT), (4.2, Y_BOT), (4.2, GND_Y), (C33_X, GND_Y)], col("gnd")); ground(ax, 7.4, GND_Y, col("gnd"))
    ax.text(7.4, GND_Y - 0.5, "AGND", color=col("gnd", MU), fontsize=12, ha="center")
    if plates:                                           # C31 plate voltages
        top, bot = plates
        ax.text(C31_X + 0.65, 5.75, ("0 V" if abs(top) < 0.05 else f"{top:+.1f} V".replace("-", "−")), color=TEAL if top > 0 else FG, fontsize=13, va="center", weight="bold")
        ax.text(C31_X + 0.65, 5.12, (f"{bot:+.1f} V".replace("-", "−") if abs(bot) >= 0.05 else "0 V"), color=CORAL if bot < 0 else FG, fontsize=13, va="center", weight="bold")
    if inside:                                           # the 4 switches
        c = lambda n: (TEAL if n in ("S1", "S2") else CORAL) if n in sw else MU
        line(ax, [(x, Y_TOP), (8.3, Y_TOP)], c("S1") if "S1" in sw else (c("S3") if "S3" in sw else MU), 1.8)
        line(ax, [(9.0, Y_TOP), (x + w, Y_TOP)], c("S1"), 1.8)
        line(ax, [(x, Y_MID), (8.8, Y_MID)], c("S2") if "S2" in sw else (c("S4") if "S4" in sw else MU), 1.8)
        line(ax, [(x, Y_BOT), (7.6, Y_BOT)], c("S2") if "S2" in sw else (c("S3") if "S3" in sw else MU), 1.8)
        line(ax, [(6.0, Y_MID), (6.0, 4.4)], c("S2"), 1.8); line(ax, [(6.0, 3.75), (6.0, Y_BOT)], c("S2"), 1.8)
        ax.add_patch(Arc((7.6, Y_MID), 0.3, 0.3, theta1=270, theta2=90, color=c("S3"), lw=1.8))     # hop over the CAP- wire
        line(ax, [(7.6, Y_TOP), (7.6, Y_MID + 0.15)], c("S3"), 1.8); line(ax, [(7.6, Y_MID - 0.15), (7.6, 4.45)], c("S3"), 1.8)
        line(ax, [(7.6, 3.8), (7.6, Y_BOT)], c("S3"), 1.8)
        line(ax, [(8.8, Y_MID), (8.8, 4.4)], c("S4"), 1.8); line(ax, [(8.8, 3.75), (8.8, Y_BOT), (x + w, Y_BOT)], c("S4"), 1.8)
        for n in SW: switch(ax, n, n in sw, c(n))
    for path, prog, c in flows: flow(ax, path, prog, c)


def out_history(n):
    v, vc, hist = 0.0, 0.0, [0.0]
    for _ in range(n):
        vc = VIN; nv = (v - vc) / 2; v = nv; hist.append(v)
    return hist
HIST = out_history(10)


def graph(ax, upto, x0=10.2, y0=6.85, w=5.4, h=1.55, ripple=0.0, t=0.0):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.05", fc="#0f1f3d", ec=DIM, lw=1))
    ax.text(x0 + 0.1, y0 + h - 0.18, "−RAW after each flip", color=MU, fontsize=11, va="center")
    Y = lambda v: y0 + h - 0.35 - (-v / VIN) * (h - 0.55)
    ax.plot([x0 + 0.2, x0 + w - 0.1], [Y(-VIN)] * 2, color=CORAL, lw=1, ls="--", alpha=0.6)
    ax.text(x0 + 0.25, Y(-VIN) - 0.2, "−3.3 V", color=CORAL, fontsize=10)
    n = int(upto); xs = [x0 + 0.3 + i * (w - 0.6) / 10 for i in range(n + 1)]
    ys = [Y(v) for v in HIST[:n + 1]]
    if ripple:
        tt = np.linspace(0, 1, 200); xx = x0 + 0.3 + tt * (w - 0.6)
        saw = (((tt * 12 + t * 2) % 1)) * ripple * (h - 0.55) / VIN
        ax.plot(xx, Y(-VIN) + 0.12 + saw, color=CORAL, lw=1.8)
    else:
        ax.plot(xs, ys, color=CORAL, lw=2); ax.plot(xs, ys, "o", color=CORAL, ms=5)


# ---- scenes: draw(ax, p, t) ----
def s_title(ax, p, t):
    ax.text(8, 8.2, "Inside the voltage inverter", color=FG, fontsize=36, ha="center", weight="bold")
    ax.text(8, 7.55, "U3 · LM2664 charge pump on the OpenBCI Cyton", color=MU, fontsize=18, ha="center")
    circuit(ax, hi=("vin", "out") if p > 0.5 else ())

def s_tour(ax, p, t):
    title(ax, "The circuit, as drawn on the schematic")
    stages = [(0.0, ("vin",)), (0.2, ("sd",)), (0.38, ("c31",)), (0.62, ("out", "c33")), (0.85, ("gnd",))]
    hi = ()
    for a, h in stages:
        if p >= a: hi = h
    circuit(ax, hi=hi)

def s_inside(ax, p, t):
    title(ax, "Inside U3: four switches")
    circuit(ax, inside=True, hi=())
    ax.text(12.9, 7.6, "S1  V+ → CAP+", color=TEAL, fontsize=14); ax.text(12.9, 7.15, "S2  CAP− → GND", color=TEAL, fontsize=14)
    ax.text(12.9, 6.7 + 0.0, "", color=FG)
    ax.text(9.0, 7.6, "S3  CAP+ → GND", color=CORAL, fontsize=14); ax.text(9.0, 7.15, "S4  CAP− → OUT", color=CORAL, fontsize=14)

def s_charge(ax, p, t):
    title(ax, "Step 1 · Charge")
    on = p > 0.12
    circuit(ax, inside=True, sw=("S1", "S2") if on else (), plates=(VIN * ramp(p, 0.15, 0.6), 0.0),
            flows=[(CHARGE_PATH, t * 0.35, TEAL)] if on else [])
    ax.text(10.4, 7.6, "S1 + S2 closed", color=TEAL, fontsize=16, weight="bold")
    ax.text(10.4, 7.1, "C31 fills to 3.3 V", color=FG, fontsize=15)

def s_flip(ax, p, t):
    title(ax, "Step 2 · Flip")
    on = p > 0.12; k = ramp(p, 0.15, 0.55)
    circuit(ax, inside=True, sw=("S3", "S4") if on else (), plates=(VIN * (1 - k), -VIN * k), out_v=HIST[1] * ramp(p, 0.4, 0.8),
            flows=[(FLIP_OUT, t * 0.35, CORAL), (FLIP_GND, t * 0.35, CORAL)] if on else [])
    ax.text(10.4, 7.6, "S3 + S4 closed", color=CORAL, fontsize=16, weight="bold")
    ax.text(10.4, 7.1, "top plate → 0 V, bottom → −3.3 V", color=FG, fontsize=15)

def s_repeat(ax, p, t):
    title(ax, "Charge, flip, repeat")
    k = int(t * 2.2); phase = k % 2
    flips = min(10, 1 + int(ramp(p, 0.05, 0.9) * 9.99))
    circuit(ax, inside=True, sw=("S1", "S2") if phase == 0 else ("S3", "S4"), plates=(VIN, 0.0) if phase == 0 else (0.0, -VIN),
            out_v=HIST[flips], flows=[(CHARGE_PATH, t * 0.6, TEAL)] if phase == 0 else [(FLIP_OUT, t * 0.6, CORAL)])
    graph(ax, flips)

def s_ripple(ax, p, t):
    title(ax, "Why a regulator comes next")
    circuit(ax, short_out=True, hi=("out",))
    rx, ry = 12.4, 2.75
    ax.add_patch(FancyBboxPatch((rx, ry), 2.6, 0.9, boxstyle="round,pad=0.05", fc="#0f1f3d", ec=YEL, lw=2))
    ax.text(rx + 1.3, ry + 0.58, "−2.5 V regulator", color=YEL, fontsize=13, ha="center"); ax.text(rx + 1.3, ry + 0.22, "TPS72325", color=MU, fontsize=11, ha="center")
    ax.annotate("", xy=(rx + 1.3, 2.15), xytext=(rx + 1.3, ry - 0.05), arrowprops=dict(arrowstyle="->", color=TEAL, lw=2))
    ax.text(rx + 1.3, 1.85, "AVSS  −2.5 V, clean", color=TEAL, fontsize=13, ha="center")
    graph(ax, 10, ripple=0.35 * ramp(p, 0.05, 0.3), t=t)
    if p > 0.45:
        ax.text(10.2, 6.55, "small sawtooth ripple on −RAW", color=CORAL, fontsize=12)

def s_end(ax, p, t):
    ax.text(8, 7.3, "Fill · Flip · Empty · Repeat", color=FG, fontsize=34, ha="center", weight="bold")
    pts = ["S1+S2: C31 charges to +3.3 V from DVDD", "S3+S4: C31 flipped, pushes −3.3 V into C33", "Thousands of times a second → −RAW ≈ −3.3 V",
           "−2.5 V regulator cleans it into AVSS for the ADS1299"]
    for i, s in enumerate(pts):
        if p > 0.1 + i * 0.15: ax.text(3.0, 6.0 - i * 0.75, "•  " + s, color=FG if i < 3 else TEAL, fontsize=19)
    if p > 0.75: ax.text(8, 2.3, "SD (pin 4) tied to V+ keeps it always running.  \"Switch this to TCM828\" = a pin-compatible swap.", color=MU, fontsize=14, ha="center")


SCENES = [
 ("This is the voltage inverter on the Cyton: U three, an L M twenty six sixty four. It turns plus three point three volts into about minus three point three volts.", s_title),
 ("Here is the circuit as drawn. Plus three point three volts from D V D D enters pin five. The shutdown pin, pin four, is tied to it, so the chip always runs. Capacitor C thirty one sits between pins six and three. This is the flying capacitor. Pin two is the output, minus raw, with capacitor C thirty three holding it steady. Pin one goes to analog ground.", s_tour),
 ("Inside the chip are four switches. A built-in clock opens and closes them in pairs, many thousands of times every second.", s_inside),
 ("Step one: charge. Switches one and two close. C thirty one is connected between plus three point three volts and ground, and fills up. Its top plate sits at plus three point three volts, and its bottom plate at zero.", s_charge),
 ("Step two: flip. Switches one and two open, and three and four close. The top plate is pulled down to ground. The capacitor still holds three point three volts across it, so the bottom plate is pushed to minus three point three volts, and its charge pours into C thirty three.", s_flip),
 ("Charge, flip, repeat. Each flip tops up C thirty three, so the output steps down: minus one point six, minus two point five, minus two point nine, until it settles near minus three point three volts.", s_repeat),
 ("The result isn't perfect. Between flips the load drains C thirty three a little, leaving a small sawtooth ripple. So the Cyton feeds minus raw into a minus two point five volt regulator, which turns it into a clean, steady supply for the A D S twelve ninety nine.", s_ripple),
 ("So the inverter works like a bucket: fill the capacitor, flip it upside down, empty it into the output, and repeat. That's how a battery powered board gets a negative supply.", s_end),
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
            fig, ax = new_fig(); draw(ax, 0.8, 3.3); caption(ax, text, 0.8)
            fig.savefig(os.path.join(d, f"cp{i}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
