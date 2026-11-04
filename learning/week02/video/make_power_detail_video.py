"""Narrated video, part 1: inside the inverter (LM2664), a positive LDO (U5/U4) and the negative LDO (VR1, with NR + C30).
Part 2: the Cyton's exact power-supply sheet (redrawn from the schematic), zooming block by block, then a power-up
showing how net labels (RAW, DVDD, -RAW) join the blocks.
Needs: matplotlib, numpy, ffmpeg, macOS `say`, and make_charge_pump_video.py next to this file.
Usage: python make_power_detail_video.py -> cyton_power_detail.mp4      Preview: python make_power_detail_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_charge_pump_video as cp

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyton_power_detail.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
RAWC, DVC, AVDC, NEGC, YEL, RED = "#ffb347", "#5aa9ff", "#2ec4a0", "#ff8a5c", "#ffd166", "#ef5b5b"
RNG = np.random.default_rng(3); NOISE = RNG.normal(0, 1, 4000)


def new_fig(units=True):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_facecolor(BG)
    if units: ax.set_xlim(0, 16); ax.set_ylim(0, 9)
    return fig, ax
def ease(x): x = min(1, max(0, x)); return 0.5 - 0.5 * math.cos(math.pi * x)
def ramp(p, a, b): return ease((p - a) / (b - a))
def sentence_at(text, p):
    parts = [x for x in re.split(r"(?<=[.?!])\s+", text) if x]; total = sum(len(x) for x in parts); acc = 0
    for x in parts:
        acc += len(x)
        if p <= acc / total: return x
    return parts[-1]
def caption(fig, text, p):
    fig.text(0.5, 0.035, "\n".join(textwrap.wrap(sentence_at(text, p), 92)), color=FG, fontsize=17, ha="center", va="bottom",
             bbox=dict(boxstyle="round,pad=0.45", fc="#14254a", ec="none"))
def title(fig, s): fig.text(0.025, 0.94, s, color=FG, fontsize=24, weight="bold", va="center")
def flow(ax, path, prog, c, n=14, ms=6, z=2.6):
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]; L = sum(seg)
    for k in range(n):
        d = ((k / n + prog) % 1) * L; acc = 0
        for (a, b), s in zip(zip(path, path[1:]), seg):
            if d <= acc + s:
                t = (d - acc) / s if s else 0
                ax.plot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, "o", ms=ms, color=c, zorder=z); break
            acc += s


# =====================================================================================
# Part 1a: inverter internals (reuses the charge-pump drawing)
# =====================================================================================
def s_inverter(fig, ax, p, t):
    title(fig, "Inside the inverter (U3)")
    phase = int(t * 1.1) % 2
    flips = min(10, 1 + int(ramp(p, 0.1, 0.85) * 9.99))
    cp.circuit(ax, inside=True, sw=("S1", "S2") if phase == 0 else ("S3", "S4"),
               plates=(cp.VIN, 0.0) if phase == 0 else (0.0, -cp.VIN), out_v=cp.HIST[flips],
               flows=[(cp.CHARGE_PATH, t * 0.5, cp.TEAL)] if phase == 0 else [(cp.FLIP_OUT, t * 0.5, cp.CORAL), (cp.FLIP_GND, t * 0.5, cp.CORAL)])
    cp.graph(ax, flips)
    ax.text(0.4, 7.7, "S1+S2: charge C31" if phase == 0 else "S3+S4: flip C31", color=cp.TEAL if phase == 0 else cp.CORAL, fontsize=17, weight="bold")


# =====================================================================================
# Part 1b/c: LDO internals (positive and negative)
# =====================================================================================
def ldo(ax, vin, vout, opening, iload, neg=False, nr=False, chip="U5"):
    cin, cout = (NEGC, NEGC) if neg else (RAWC, DVC)
    sgn = -1 if neg else 1
    ref = 1.2 * sgn; ratio = (2.5 if neg else 3.3) / 1.2
    fb = vout / ratio
    # chip outline
    x0 = 0.9 if nr else 2.4
    ax.add_patch(Rectangle((x0, 2.3), 9.0 - x0, 4.15, fc="none", ec=DIM, lw=1.5, ls="--"))
    ax.text(x0 + 0.1, 6.25, f"inside {chip}", color=MU, fontsize=12)
    # main path
    ax.plot([0.3, 4.6], [5.6, 5.6], color=cin, lw=3); ax.text(0.3, 5.9, f"IN  {vin:+.2f} V".replace("-", "−"), color=cin, fontsize=14, weight="bold")
    ax.add_patch(Rectangle((4.6, 5.0), 2.0, 1.2, fc=PANEL, ec=FG, lw=1.8, zorder=3))
    ax.add_patch(Rectangle((4.6, 5.6 - 0.55 * opening), 2.0, 1.1 * opening, fc=YEL, alpha=0.4, zorder=3))
    ax.text(5.6, 5.6, f"{int(round(opening * 100))}% open", color=YEL, fontsize=12, ha="center", va="center", zorder=4)
    ax.text(5.6, 6.55, "pass transistor (valve)", color=FG, fontsize=12, ha="center")
    ax.plot([6.6, 13.3], [5.6, 5.6], color=cout, lw=3)
    ax.text(13.35, 5.9, "OUT", color=cout, fontsize=14, weight="bold"); ax.text(13.35, 5.25, f"{vout:+.2f} V".replace("-", "−"), color=cout, fontsize=17, weight="bold")
    # divider
    for yy in (4.45, 3.05): ax.add_patch(Rectangle((7.85, yy), 0.3, 0.75, fc=PANEL, ec=FG, lw=1.4, zorder=3))
    ax.plot([8.0, 8.0], [5.6, 2.55], color=FG, lw=1.4); ax.plot(8.0, 5.6, "o", color=FG, ms=6)
    ax.text(8.3, 4.82, "R1", color=MU, fontsize=11); ax.text(8.3, 3.42, "R2", color=MU, fontsize=11)
    ax.plot(8.0, 4.12, "o", color=YEL, ms=6, zorder=4); ax.text(8.25, 4.12, f"feedback {fb:+.2f} V".replace("-", "−"), color=YEL, fontsize=12, va="center")
    cp.ground(ax, 8.0, 2.55)
    # error amp
    ax.add_patch(Polygon([[4.9, 3.0], [6.3, 3.0], [5.6, 4.2]], closed=True, fc=BG, ec=FG, lw=1.8, zorder=3))
    ax.text(5.6, 3.35, "error\namp", color=FG, fontsize=10, ha="center", va="center", zorder=4)
    ax.plot([5.6, 5.6], [4.2, 5.0], color=YEL, lw=2)
    ax.text(5.15, 3.12, "+", color=FG, fontsize=11, ha="center", zorder=4); ax.text(6.05, 3.12, "−", color=FG, fontsize=11, ha="center", zorder=4)
    ax.plot([8.0, 7.1, 7.1, 5.95, 5.95], [4.12, 4.12, 2.6, 2.6, 3.0], color=YEL, lw=1.4)
    # reference (+ NR filter)
    if nr:
        ax.add_patch(FancyBboxPatch((1.1, 2.75), 1.4, 0.5, boxstyle="round,pad=0.03", fc=PANEL, ec=YEL, lw=1.4))
        ax.text(1.8, 3.0, "−1.2 V ref", color=YEL, fontsize=11, ha="center", va="center")
        ax.plot([2.5, 2.75], [3.0, 3.0], color=YEL, lw=1.4); ax.add_patch(Rectangle((2.75, 2.88), 0.6, 0.24, fc=PANEL, ec=FG))
        ax.plot([3.35, 5.25, 5.25], [3.0, 3.0, 3.0], color=YEL, lw=1.4)
        ax.plot([3.75, 3.75], [3.0, 2.3], color=YEL, lw=1.4); ax.plot(3.75, 3.0, "o", color=YEL, ms=5)
        ax.text(3.95, 2.4, "NR pin", color=YEL, fontsize=11)
        ax.plot([3.75, 3.75], [2.3, 2.05], color=FG, lw=1.4); cp.cap_h(ax, 3.75, 2.05, 1.92)
        ax.plot([3.75, 3.75], [1.92, 1.75], color=FG, lw=1.4); ax.text(2.95, 1.98, "C30\n0.01 µF", color=FG, fontsize=10, ha="right", va="center")
    else:
        ax.add_patch(FancyBboxPatch((2.6, 2.35), 1.5, 0.5, boxstyle="round,pad=0.03", fc=PANEL, ec=YEL, lw=1.4))
        ax.text(3.35, 2.6, f"{ref:+.1f} V ref".replace("-", "−").replace("+", ""), color=YEL, fontsize=11, ha="center", va="center")
        ax.plot([4.1, 5.25, 5.25], [2.6, 2.6, 3.0], color=YEL, lw=1.4)
    # output capacitor and load
    ax.plot([10.0, 10.0], [5.6, 4.55], color=cout, lw=1.6); cp.cap_h(ax, 10.0, 4.55, 4.4); ax.plot([10.0, 10.0], [4.4, 2.55], color=FG, lw=1.4)
    cp.ground(ax, 10.0, 2.55); ax.text(10.6, 4.48, "output\ncapacitor", color=MU, fontsize=11, va="center")
    ax.plot([12.2, 12.2], [5.6, 4.75], color=cout, lw=1.6)
    ax.add_patch(plt.Circle((12.2, 4.4), 0.35, fc=PANEL, ec=FG, lw=1.4, zorder=3))
    ax.annotate("", xy=(12.2, 4.15), xytext=(12.2, 4.65), arrowprops=dict(arrowstyle="->", color=FG, lw=1.4), zorder=4)
    ax.plot([12.2, 12.2], [4.05, 2.55], color=FG, lw=1.4); cp.ground(ax, 12.2, 2.55)
    ax.text(12.7, 4.4, f"load\n{iload:.0f} mA", color=FG, fontsize=12, va="center")
    # verdict
    if opening >= 0.999: v, c = "DROPOUT: valve fully open, output follows the input down", RED
    elif abs(abs(fb) - 1.2) < 0.004: v, c = "feedback = reference  →  hold the valve where it is", AVDC
    else: v, c = "feedback below reference  →  open the valve wider", YEL
    ax.text(0.4, 7.7, v, color=c, fontsize=16, weight="bold")


def mini_plot(ax, series, ylo, yhi, label, x0=9.6, y0=6.55, w=6.0, h=1.45):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
    ax.text(x0 + 0.12, y0 + h - 0.2, label, color=MU, fontsize=11, va="center")
    for xs, ys, c in series:
        X = x0 + 0.2 + np.asarray(xs) * (w - 0.4)
        Y = y0 + 0.15 + (np.clip(np.asarray(ys), ylo, yhi) - ylo) / (yhi - ylo) * (h - 0.55)
        ax.plot(X, Y, color=c, lw=2)


def load_step_vout(q):
    return 3.3 if q < 0.35 else 3.3 - 0.09 * math.exp(-(q - 0.35) / 0.035)
def s_ldo_parts(fig, ax, p, t):
    title(fig, "Inside a regulator (U5 and U4)")
    ldo(ax, 5.7, 3.3, 0.3, 20)
def s_ldo_load(fig, ax, p, t):
    title(fig, "Regulator: a sudden load")
    iload = 20 if p < 0.35 else 100
    vout = load_step_vout(p); opening = 0.3 + 0.25 * ramp(p, 0.35, 0.45)
    ldo(ax, 5.7, vout, opening, iload)
    qs = np.linspace(0, p, 200); mini_plot(ax, [(qs, [load_step_vout(q) for q in qs], DVC)], 3.15, 3.36, "OUT over time: dip, then recovery")
def dropout_vals(q):
    vin = 5.7 - 2.4 * ramp(q, 0.1, 0.85); vout = min(3.3, vin - 0.2)
    return vin, vout, min(1.0, 0.55 + 0.45 * (5.7 - vin) / (5.7 - 3.5))
def s_ldo_drop(fig, ax, p, t):
    title(fig, "Regulator: the battery runs down")
    vin, vout, op = dropout_vals(p)
    ldo(ax, vin, vout, op, 100)
    qs = np.linspace(0, p, 200); vals = [dropout_vals(q) for q in qs]
    mini_plot(ax, [(qs, [v[0] for v in vals], RAWC), (qs, [v[1] for v in vals], DVC)], 2.8, 6.0, "IN (orange) and OUT (blue)")
def s_neg_ldo(fig, ax, p, t):
    title(fig, "Inside VR1: the negative regulator")
    vin = -3.3 + 0.04 * ((t * 3) % 1)
    ldo(ax, vin, -2.5, 0.35, 30, neg=True, nr=True, chip="VR1")
    k = int(t * 40) % 3000; xs = np.linspace(0, 1, 160); raw = NOISE[k:k + 160]
    smooth = np.convolve(raw, np.ones(25) / 25, mode="same") * 0.35
    show = ramp(p, 0.45, 0.6)
    series = [(xs, -1.2 + 0.05 * raw, MU)]
    if show > 0: series.append((xs, -1.2 + 0.05 * smooth, AVDC))
    mini_plot(ax, series, -1.4, -1.0, "reference noise: grey = without C30, green = with C30")


# =====================================================================================
# Part 2: the exact power-supply sheet (coordinates in schematic pixels, 2000 x 750)
# =====================================================================================
NETS = {
 "raw": [[(213, 262), (213, 225), (252, 225)], [(276, 225), (340, 225)], [(560, 474), (750, 474)], [(627, 474), (627, 512)]],
 "dvdd": [[(895, 474), (1120, 474), (1120, 434)], [(995, 474), (995, 512)], [(878, 143), (1020, 143)], [(943, 143), (943, 180), (878, 180)],
          [(1365, 474), (1532, 474)], [(1430, 474), (1430, 515)], [(1465, 474), (1465, 547), (1532, 547)]],
 "negraw": [[(878, 216), (1020, 216)], [(935, 216), (935, 240)], [(1330, 140), (1513, 140)], [(1390, 140), (1390, 172)], [(1447, 140), (1447, 177), (1513, 177)]],
 "avss": [[(1660, 140), (1905, 140), (1905, 163)], [(1760, 140), (1760, 185)], [(1832, 140), (1832, 185)]],
 "avdd": [[(1677, 474), (1910, 474), (1910, 434)], [(1778, 474), (1778, 515)], [(1850, 474), (1850, 515)]],
 "gnd": [[(213, 300), (213, 345)], [(730, 216), (695, 216), (695, 283), (935, 283)], [(935, 248), (935, 283)], [(815, 283), (815, 318)],
         [(1587, 198), (1587, 290)], [(1390, 250), (1832, 250)], [(1390, 180), (1390, 250)], [(1760, 193), (1760, 250)], [(1832, 193), (1832, 250)],
         [(1712, 223), (1712, 250)], [(750, 510), (703, 510), (703, 592)], [(627, 520), (627, 592), (995, 592)], [(995, 520), (995, 592)],
         [(820, 592), (820, 628)], [(1532, 510), (1485, 510), (1485, 592)], [(1430, 523), (1430, 592), (1850, 592)], [(1778, 523), (1778, 592)],
         [(1850, 523), (1850, 592)], [(1602, 592), (1602, 628)]],
 "flying": [[(730, 143), (670, 143), (670, 155)], [(670, 163), (670, 180), (730, 180)]],
 "en": [[(750, 547), (560, 547)]],
 "nr": [[(1660, 177), (1712, 177), (1712, 215)]],
 "nc": [[(895, 547), (932, 547)], [(1677, 547), (1712, 547)]],
}
NET_COL = {"raw": RAWC, "dvdd": DVC, "negraw": NEGC, "avss": NEGC, "avdd": AVDC, "gnd": "#9fb0c8", "flying": YEL, "en": YEL, "nr": YEL}
DOTS = [(1120, 474), (995, 474), (943, 143), (935, 216), (1390, 140), (1447, 140), (1760, 140), (1832, 140), (627, 474), (1430, 474), (1465, 474),
        (1778, 474), (1850, 474), (815, 283), (1587, 250), (820, 592), (703, 592), (1602, 592), (1485, 592), (1760, 250), (1712, 250), (995, 592), (1778, 592)]
CAPS = [  # x, y_top, name, value, label side
    (670, 155, "C31", "10uF", "L"), (935, 240, "C33", "10uF", "R"), (1390, 172, "C36", "2.2uF", "R"), (1760, 185, "C32", "2.2uF", "R"),
    (1832, 185, "C29", "10uF", "R"), (1712, 215, "C30", "0.01uF", "L"), (627, 512, "C39", "2.2uF", "L"), (995, 512, "C40", "2.2uF", "R"),
    (1430, 515, "C38", "2.2uF", "L"), (1778, 515, "C35", "2.2uF", "R"), (1850, 515, "C37", "10uF", "R")]
GROUNDS = [(213, 345), (815, 318), (1587, 290), (820, 628), (1602, 628)]
BOXES = [(730, 130, 878, 238), (1513, 125, 1660, 198), (750, 460, 895, 570), (1532, 460, 1677, 570)]
VIEWS = {"full": (1000, 350, 2040), "bat": (285, 300, 760), "inv": (840, 225, 820), "neg": (1640, 210, 900), "u5": (850, 545, 900), "u4": (1660, 545, 900)}
FLOW_PATHS = {"raw": [[(213, 262), (213, 225), (340, 225)], [(560, 474), (750, 474)]],
              "dvdd": [[(895, 474), (1120, 474), (1120, 434)], [(1020, 143), (878, 143)], [(1365, 474), (1532, 474)]],
              "negraw": [[(878, 216), (1020, 216)], [(1330, 140), (1513, 140)]],
              "avss": [[(1660, 140), (1905, 140), (1905, 163)]], "avdd": [[(1677, 474), (1910, 474), (1910, 434)]]}
JUMPS = {"raw": [((352, 232), (545, 466))], "dvdd": [((1120, 418), (985, 128)), ((1120, 418), (1395, 456))], "negraw": [((1030, 210), (1338, 128))]}


def set_view(ax, v):
    cx, cy, w = v; h = w * 9 / 16
    ax.set_xlim(cx - w / 2, cx + w / 2); ax.set_ylim(cy + h / 2, cy - h / 2)
    return 2040 / w                                              # text / line scale


def lerp_view(a, b, k): return tuple(x + (y - x) * k for x, y in zip(a, b))


def sheet(ax, view, on=(), focus=None, flows=(), jumps=(), t=0.0):
    s = set_view(ax, view)
    fs = lambda f: f * s; lw = lambda l: l * min(s, 2.4)
    T = lambda x, y, txt, f=7, **k: ax.text(x, y, txt, color=k.pop("c", FG), fontsize=fs(f), **k)
    def wire(pts, c, w=1.2): xs, ys = zip(*pts); ax.plot(xs, ys, color=c, lw=lw(w), solid_capstyle="round", zorder=2)
    for net, paths in NETS.items():
        c = NET_COL.get(net, FG) if net in on else FG
        for pts in paths: wire(pts, c, 1.6 if net in on else 1.1)
    for x, y in DOTS: ax.plot(x, y, "o", color=FG, ms=lw(3), zorder=3)
    for x0, y0, x1, y1 in BOXES: ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=BG, ec=FG, lw=lw(1.2), zorder=2.5))
    for x, y, nm, val, side in CAPS:
        ax.plot([x - 18, x + 18], [y, y], color=FG, lw=lw(1.6), zorder=3); ax.plot([x - 18, x + 18], [y + 8, y + 8], color=FG, lw=lw(1.6), zorder=3)
        hx = x - 24 if side == "L" else x + 22; ha = "right" if side == "L" else "left"
        T(hx, y - 4, nm, 6.5, ha=ha, va="center"); T(hx, y + 14, val, 6.5, ha=ha, va="center")
    for x, y in GROUNDS:
        c = NET_COL["gnd"] if "gnd" in on else FG
        for i, w2 in enumerate((14, 9, 4)): ax.plot([x - w2, x + w2], [y + i * 5, y + i * 5], color=c, lw=lw(1.2))
        T(x, y + 25, "AGND", 6.5, ha="center", va="center")
    # battery + D9
    for i, (w2, yy) in enumerate(((26, 270), (14, 278), (26, 286), (14, 294))): ax.plot([213 - w2, 213 + w2], [yy, yy], color=FG, lw=lw(1.6))
    ax.plot([213, 213], [262, 270], color=FG, lw=lw(1.1)); ax.plot([213, 213], [294, 300], color=FG, lw=lw(1.1))
    dc = RAWC if "raw" in on else FG
    ax.add_patch(Polygon([[252, 213], [252, 237], [272, 225]], closed=True, fc=BG, ec=dc, lw=lw(1.2), zorder=3)); ax.plot([274, 274], [213, 237], color=dc, lw=lw(1.4))
    T(262, 248, "D9", 6.5, ha="center"); T(222, 258, "2", 6); T(236, 266, "+", 6.5); T(222, 315, "3", 6); T(236, 306, "−", 6.5)
    T(168, 310, "B1", 6); T(168, 320, "BATT", 6); T(168, 330, "SM", 6)
    # net-label arrows
    def arrow(x0, y0, x1, y1, net):
        c = NET_COL.get(net, FG) if net in on else FG
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color=c, lw=lw(1.1)))
    arrow(330, 225, 345, 225, "raw"); T(352, 226, "RAW", 7, va="center")
    arrow(1010, 143, 1028, 143, "dvdd"); T(985, 133, "DVDD", 7, ha="center")
    arrow(1010, 216, 1028, 216, "negraw"); T(985, 206, "-RAW", 7, ha="center")
    arrow(1340, 140, 1324, 140, "negraw"); T(1360, 130, "-RAW", 7, ha="center")
    arrow(570, 474, 553, 474, "raw"); T(545, 475, "RAW", 7, ha="right", va="center")
    arrow(570, 547, 553, 547, "en"); T(545, 551, "3V Enable", 7, ha="right", va="center")
    arrow(1375, 474, 1358, 474, "dvdd"); T(1395, 463, "DVDD", 7, ha="center")
    for x, y, net in ((1120, 434, "dvdd"), (1910, 434, "avdd")):
        ax.plot([x - 12, x + 12], [y, y], color=NET_COL[net] if net in on else FG, lw=lw(1.6))
    ax.plot([1893, 1917], [163, 163], color=NEGC if "avss" in on else FG, lw=lw(1.6))
    T(1120, 422, "DVDD", 7, ha="center"); T(1150, 476, "3.3V", 7, va="center"); T(1915, 422, "AVDD", 7, ha="center")
    T(1945, 476, "+2.5V", 7, va="center"); T(1935, 142, "-2.5V", 7, va="center"); T(1905, 182, "AVSS", 7, ha="center")
    for x, y in ((932, 547), (1712, 547)):
        ax.plot([x - 5, x + 5], [y - 5, y + 5], color=FG, lw=lw(1.2)); ax.plot([x - 5, x + 5], [y + 5, y - 5], color=FG, lw=lw(1.2))
    # chip text and pins
    T(790, 156, "U3", 5.6); T(790, 166, "LM2664", 5.6); T(790, 176, "SOT-23-6", 5.6); T(805, 114, "Voltage Inverter", 6.5, ha="center")
    for y, l, r, nl, nr in ((143, "CAP+", "V+", "6", "5"), (180, "CAP-", "SD", "3", "4"), (216, "GND", "OUT", "1", "2")):
        T(736, y, l, 6.2, va="center"); T(872, y, r, 6.2, va="center", ha="right"); T(705, y - 8, nl, 6); T(905, y - 8, nr, 6)
    T(805, 262, "SWITCH THIS TO TCM828", 6.5, ha="center", va="center")
    T(1548, 141, "VR1", 5.4); T(1548, 150, "TPS72325", 5.4); T(1548, 159, "SM", 5.4)
    for y, l, r, nl, nr in ((140, "IN", "OUT", "2", "5"), (177, "EN", "NR", "3", "4")):
        T(1519, y, l, 6.2, va="center"); T(1654, y, r, 6.2, va="center", ha="right"); T(1475, y - 8, nl, 6); T(1690, y - 8, nr, 6)
    T(1587, 188, "GND", 5.5, ha="center", va="center", rotation=90); T(1593, 228, "1", 6)
    T(752, 431, "U5", 5.6); T(752, 441, "MCP1754T-3302E/OT", 5.6); T(752, 451, "SM", 5.6)
    for y, l, r, nl, nr in ((474, "VIN", "OUT", "1", "5"), (510, "GND", "", "2", ""), (547, "/SHDN", "PWRGD", "3", "4")):
        T(756, y, l, 6.2, va="center"); T(889, y, r, 6.2, va="center", ha="right"); T(712, y - 8, nl, 6); T(925, y - 8, nr, 6)
    T(1566, 486, "U4", 5.4); T(1566, 495, "TLV700xx LDO REG", 5.4); T(1566, 504, "SOT23-5", 5.4)
    for y, l, r, nl, nr in ((474, "IN", "OUT", "1", "5"), (510, "GND", "", "2", ""), (547, "EN", "NC", "3", "4")):
        T(1538, y, l, 6.2, va="center"); T(1671, y, r, 6.2, va="center", ha="right"); T(1495, y - 8, nl, 6); T(1708, y - 8, nr, 6)
    # block titles
    for x, y, txt in ((220, 437, "BATTERY CONNECT"), (835, 70, "VOLTAGE INVERTER"), (1580, 77, "-2.5V REGULATOR"),
                      (815, 410, "+3V REGULATOR"), (1620, 410, "+2.5V REGULATOR"), (1127, 715, "POWER SUPPLY")):
        T(x, y, txt, 11, ha="center", va="center", c=MU)
    if focus:
        x0, y0, x1, y1 = focus
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=4", fc="none", ec=YEL, lw=lw(1.4), ls="--", zorder=1))
    for net in flows:
        for path in FLOW_PATHS.get(net, []): flow(ax, path, t * 0.4, NET_COL[net], n=8, ms=lw(3.4), z=4)
    for net in jumps:
        for (a, b) in JUMPS.get(net, []):
            ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color=NET_COL[net], lw=lw(1.6), ls="--", connectionstyle="arc3,rad=-0.25"), zorder=5)


FOCUS = {"bat": (150, 200, 400, 395), "inv": (630, 95, 1040, 345), "neg": (1320, 95, 1960, 320), "u5": (520, 420, 1180, 655), "u4": (1350, 415, 1975, 655)}
def zoom_scene(key, nets, prev="full"):
    def draw(fig, ax, p, t):
        v = lerp_view(VIEWS[prev], VIEWS[key], ramp(p, 0.0, 0.18))
        sheet(ax, v, on=nets, focus=FOCUS[key] if p > 0.18 else None, flows=[n for n in nets if n in FLOW_PATHS], t=t)
    return draw
def s_sheet_full(fig, ax, p, t):
    title(fig, "The actual power-supply sheet")
    sheet(ax, VIEWS["full"], on=("gnd",) if p > 0.6 else ())
def s_powerup(fig, ax, p, t):
    title(fig, "Switch on: power flows through the net labels")
    v = lerp_view(VIEWS["u4"], VIEWS["full"], ramp(p, 0.0, 0.1))
    order = [("raw", 0.1), ("dvdd", 0.3), ("avdd", 0.5), ("negraw", 0.6), ("avss", 0.78)]
    on = [n for n, a in order if p >= a] + (["gnd"] if p > 0.9 else [])
    jumps = [n for n, a in (("raw", 0.18), ("dvdd", 0.4), ("negraw", 0.68)) if p >= a]
    sheet(ax, v, on=on, flows=[n for n in on if n in FLOW_PATHS], jumps=jumps, t=t)
def s_end(fig, ax, p, t):
    ax.set_xlim(0, 16); ax.set_ylim(0, 9)
    ax.text(8, 7.5, "One battery, five blocks, four clean supplies", color=FG, fontsize=28, ha="center", weight="bold")
    rows = [("RAW", "battery through D9", RAWC), ("DVDD +3.3 V", "U5 from RAW: digital side, PIC32, radio, SD", DVC),
            ("AVDD +2.5 V", "U4 from DVDD: ADS1299 analog top", AVDC), ("−RAW ≈ −3.3 V", "U3 inverter from DVDD", NEGC),
            ("AVSS −2.5 V", "VR1 from −RAW: ADS1299 analog bottom", NEGC)]
    for i, (a, b, c) in enumerate(rows):
        if p > 0.08 + i * 0.12:
            ax.text(3.0, 6.3 - i * 0.75, a, color=c, fontsize=19, weight="bold"); ax.text(6.4, 6.3 - i * 0.75, b, color=FG, fontsize=17)


def titled(name, fn):
    def d(fig, ax, p, t): title(fig, name); fn(fig, ax, p, t)
    return d


SCENES = [
 ("Part one: what happens inside the inverter and the regulators. Part two: the real Cyton power circuit, block by block.", s_sheet_full),
 ("First, the inverter. Inside U three, four switches take turns. Switches one and two charge the flying capacitor C thirty one from three point three volts. Then switches three and four flip it, so its bottom plate sits at minus three point three volts and pushes charge into C thirty three. Repeated many thousands of times a second, this holds minus raw near minus three point three volts.", s_inverter),
 ("Now a regulator, like U five or U four. Current flows from the input, through a pass transistor that acts as a valve, to the output. Two resistors, R one and R two, make a scaled-down copy of the output, called the feedback voltage. An error amplifier, which is an op amp, compares the feedback with a steady one point two volt reference.", s_ldo_parts),
 ("Watch what happens when the load suddenly draws more current. The output dips slightly, so the feedback falls below the reference. The error amplifier opens the valve wider, and within microseconds the output is back at three point three volts. The output capacitor supplies the extra current during that brief moment.", s_ldo_load),
 ("If the battery runs down, the valve opens further and further to keep up. Once it's fully open, the output can only follow the input down. That's dropout, and it's why the input needs some voltage to spare.", s_ldo_drop),
 ("V R one works the same way, mirrored for negative voltages: its reference is negative, and its valve sits between minus raw and the output. It has one extra pin, N R. The reference passes through an internal resistor to that pin, and capacitor C thirty forms a filter that removes the reference's own noise, so the minus two point five volt rail is extra quiet.", s_neg_ldo),
 ("Here is the real power supply sheet from the Cyton schematic. Five blocks, joined only by net labels: wires with the same name are connected, even when they're far apart on the page. Every A G N D symbol is the same analog ground.", s_sheet_full),
 ("Battery connect. B one's plus terminal, pin two, goes through diode D nine to the net called raw. Its minus terminal, pin three, goes to analog ground.", titled("Battery connect", zoom_scene("bat", ("raw", "gnd")))),
 ("Plus three volt regulator. Raw arrives at U five's input, pin one, with C thirty nine, two point two microfarads, to ground. Pin three, shutdown, is driven by the three volt enable line. The output, pin five, has C forty and becomes D V D D, three point three volts. Pin four, power good, is unused, so it's marked with an X.", titled("+3V regulator (U5)", zoom_scene("u5", ("raw", "dvdd", "en", "gnd"), prev="bat"))),
 ("Voltage inverter. D V D D enters U three's V plus, pin five, and its shutdown pin, four. C thirty one is the flying capacitor between pins six and three. The output, pin two, with C thirty three, is the net minus raw.", titled("Voltage inverter (U3)", zoom_scene("inv", ("dvdd", "negraw", "flying", "gnd"), prev="u5"))),
 ("Minus two point five volt regulator. Minus raw enters V R one's input, pin two, with C thirty six, and also its enable pin, three, so it's always on. Pin four, N R, has C thirty for low noise. The output, pin five, has C thirty two and C twenty nine, and becomes minus two point five volts: A V S S.", titled("−2.5V regulator (VR1)", zoom_scene("neg", ("negraw", "avss", "nr", "gnd"), prev="inv"))),
 ("Plus two point five volt regulator. D V D D enters U four's input, pin one, with C thirty eight, and is also tied to its enable, pin three. The output, pin five, with C thirty five and C thirty seven, becomes A V D D, plus two point five volts. Pin four isn't connected.", titled("+2.5V regulator (U4)", zoom_scene("u4", ("dvdd", "avdd", "gnd"), prev="neg"))),
 ("Now switch on. Raw comes up and jumps through its net label to U five. U five makes D V D D, which jumps to the inverter and to the plus two point five volt regulator. A V D D comes up. The inverter makes minus raw, which jumps to V R one, and A V S S comes up last.", s_powerup),
 ("That's the whole power supply: one battery, five blocks joined by net labels, and four clean supplies for the A D S twelve ninety nine and the rest of the board.", s_end),
]


def render_frame(draw, text, p, t):
    fig, ax = new_fig(); draw(fig, ax, p, t); caption(fig, text, p); return fig


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
            fig = render_frame(draw, text, k / max(1, n - 1), k / FPS)
            fig.canvas.draw(); ff.stdin.write(fig.canvas.buffer_rgba().tobytes()); plt.close(fig)
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", narration, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", "-movflags", "+faststart", OUT], check=True)
    print("saved", OUT, f"{sum(durs):.0f} s")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stills":
        d = sys.argv[2] if len(sys.argv) > 2 else "."
        for i, (text, draw) in enumerate(SCENES):
            fig = render_frame(draw, text, 0.8, 3.3); fig.savefig(os.path.join(d, f"pd{i:02d}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
