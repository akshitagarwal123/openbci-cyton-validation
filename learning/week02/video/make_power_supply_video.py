"""Narrated video: how the Cyton's power supply blocks work together.
Battery -> D9 -> RAW -> U5 (+3.3 V, DVDD) -> { digital chips, U4 (+2.5 V, AVDD), U3 inverter -> -RAW -> VR1 (-2.5 V, AVSS) }.
Also explains what an LDO regulator does inside, and the power-up order.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_power_supply_video.py -> cyton_power_supply.mp4
Preview frames: python make_power_supply_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyton_power_supply.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
RAWC, DVC, AVDC, NEGC, YEL = "#ffb347", "#5aa9ff", "#2ec4a0", "#ff8a5c", "#ffd166"

# ---- block map (axes units 16 x 9) ----
BOXES = {   # key: (x, y, w, h, title, subtitle, part)
    "bat": (0.4, 4.2, 1.6, 1.2, "Battery", "6 V (4×AA)", "B1"),
    "u5":  (4.0, 4.2, 2.0, 1.2, "U5", "+3.3 V LDO", "MCP1754"),
    "u4":  (7.8, 6.3, 2.2, 1.2, "U4", "+2.5 V LDO", "TLV700"),
    "u3":  (7.8, 2.0, 2.2, 1.2, "U3", "inverter", "LM2664"),
    "vr1": (10.9, 2.0, 2.2, 1.2, "VR1", "−2.5 V LDO", "TPS72325"),
    "ads": (13.8, 2.0, 1.9, 5.5, "ADS1299", "", ""),
}
WIRES = {   # key: (points, colour)
    "raw":  ([(2.0, 4.8), (2.4, 4.8)], RAWC), "raw2": ([(3.05, 4.8), (4.0, 4.8)], RAWC),
    "dvdd": ([(6.0, 4.8), (13.8, 4.8)], DVC), "bus": ([(6.8, 2.6), (6.8, 6.9)], DVC),
    "u4in": ([(6.8, 6.9), (7.8, 6.9)], DVC), "avdd": ([(10.0, 6.9), (13.8, 6.9)], AVDC),
    "u3in": ([(6.8, 2.6), (7.8, 2.6)], DVC), "negraw": ([(10.0, 2.6), (10.9, 2.6)], NEGC), "avss": ([(13.1, 2.6), (13.8, 2.6)], NEGC),
}
FLOWS = {
    "raw": [(0.4 + 1.6, 4.8), (4.0, 4.8)],
    "dvdd": [(6.0, 4.8), (13.8, 4.8)],
    "avdd": [(6.8, 4.8), (6.8, 6.9), (7.8, 6.9), (10.0, 6.9), (13.8, 6.9)],
    "avss": [(6.8, 4.8), (6.8, 2.6), (7.8, 2.6), (10.0, 2.6), (13.8, 2.6)],
}
STAGES = ["raw", "dvdd", "avdd", "avss"]          # power-up order


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
def info(ax, lines, p=1.0, x=0.4, y=7.75, step=0.12):
    for i, (s, c) in enumerate(lines):
        if p >= i * step: ax.text(x, y - i * 0.42, s, color=c, fontsize=14, va="center")
def flow(ax, path, prog, c, n=16):
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]; L = sum(seg)
    for k in range(n):
        d = ((k / n + prog) % 1) * L; acc = 0
        for (a, b), s in zip(zip(path, path[1:]), seg):
            if d <= acc + s:
                t = (d - acc) / s if s else 0
                ax.plot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, "o", ms=6, color=c, zorder=2.6); break
            acc += s


def power_map(ax, on=(), hi=(), flows=(), t=0.0, volts=True):
    """on: rails that are live (coloured). hi: boxes to highlight."""
    live = lambda r: r in on
    wire_rail = {"raw": "raw", "raw2": "raw", "dvdd": "dvdd", "bus": "dvdd", "u4in": "dvdd", "u3in": "dvdd",
                 "avdd": "avdd", "negraw": "avss", "avss": "avss"}
    for k, (pts, c) in WIRES.items():
        xs, ys = zip(*pts); ax.plot(xs, ys, color=c if live(wire_rail[k]) else DIM, lw=3, solid_capstyle="round", zorder=2)
    ax.plot(6.8, 4.8, "o", color=DVC if live("dvdd") else DIM, ms=8, zorder=3)
    # diode D9
    dc = RAWC if live("raw") else MU
    ax.add_patch(Polygon([[2.4, 4.55], [2.4, 5.05], [3.0, 4.8]], closed=True, fc=BG, ec=YEL if "d9" in hi else dc, lw=2, zorder=3))
    ax.plot([3.03, 3.03], [4.55, 5.05], color=YEL if "d9" in hi else dc, lw=2.5, zorder=3)
    ax.text(2.7, 5.25, "D9", color=YEL if "d9" in hi else MU, fontsize=12, ha="center")
    for k, (x, y, w, h, t1, t2, part) in BOXES.items():
        ec = YEL if k in hi else (FG if k != "ads" else MU)
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=PANEL, ec=ec, lw=2.4 if k in hi else 1.4, zorder=3))
        if k == "ads":
            ax.text(x + w / 2, y + h - 0.35, t1, color=ec if k in hi else FG, fontsize=15, ha="center", weight="bold", zorder=4)
            for yy, nm, c in ((6.9, "AVDD", AVDC), (4.8, "DVDD", DVC), (2.6, "AVSS", NEGC)):
                ax.text(x + 0.15, yy, nm, color=c if live({"AVDD": "avdd", "DVDD": "dvdd", "AVSS": "avss"}[nm]) else MU, fontsize=12, va="center", zorder=4)
            ax.text(x + w / 2, 5.85, "analog\n5 V total", color=MU, fontsize=11, ha="center", va="center", zorder=4)
            ax.text(x + w / 2, 3.7, "digital", color=MU, fontsize=11, ha="center", va="center", zorder=4)
        else:
            ax.text(x + w / 2, y + h * 0.72, t1, color=ec, fontsize=15, ha="center", va="center", weight="bold", zorder=4)
            ax.text(x + w / 2, y + h * 0.42, t2, color=FG, fontsize=12, ha="center", va="center", zorder=4)
            if part: ax.text(x + w / 2, y + h * 0.17, part, color=MU, fontsize=10, ha="center", va="center", zorder=4)
    # enable line into U5
    ec = YEL if "en" in hi else MU
    ax.annotate("", xy=(5.0, 4.15), xytext=(5.0, 3.35), arrowprops=dict(arrowstyle="->", color=ec, lw=1.8))
    ax.text(5.0, 3.05, "3V Enable (on/off)", color=ec, fontsize=11, ha="center")
    if volts:
        tags = [("raw", 3.45, 4.3, "RAW 5.7 V", RAWC), ("dvdd", 10.4, 5.1, "DVDD +3.3 V", DVC), ("avdd", 11.9, 7.2, "AVDD +2.5 V", AVDC),
                ("avss", 10.45, 3.45, "−RAW −3.3 V", NEGC), ("avss", 13.45, 1.75, "AVSS −2.5 V", NEGC)]
        for r, x, y, s, c in tags:
            if live(r): ax.text(x, y, s, color=c, fontsize=12, ha="center", weight="bold", zorder=5)
        if live("dvdd"): ax.text(10.4, 4.45, "also PIC32 · RFduino · SD · accel", color=MU, fontsize=10.5, ha="center", zorder=5)
    for r in flows:
        c = {"raw": RAWC, "dvdd": DVC, "avdd": AVDC, "avss": NEGC}[r]
        flow(ax, FLOWS[r], t * 0.35, c)


# ---- scenes ----
def s_title(ax, p, t):
    ax.text(8, 8.2, "The Cyton's power supply", color=FG, fontsize=34, ha="center", weight="bold")
    ax.text(8, 7.6, "one battery → four supply voltages", color=MU, fontsize=18, ha="center")
    n = int(ramp(p, 0.2, 0.9) * 4.99)
    power_map(ax, on=STAGES[:n], flows=STAGES[:n], t=t, volts=False)

def s_overview(ax, p, t):
    title(ax, "The big picture")
    n = 1 + int(ramp(p, 0.08, 0.8) * 3.99)
    power_map(ax, on=STAGES[:n], flows=STAGES[:n], t=t)

def s_battery(ax, p, t):
    title(ax, "Battery and D9")
    power_map(ax, on=("raw",), hi=("bat", "d9"), flows=("raw",), t=t)
    info(ax, [("6 V battery (4×AA), or a 3.7 V LiPo", FG), ("D9 blocks a reversed battery", YEL), ("costs ≈ 0.3 V  →  RAW ≈ 5.7 V", RAWC),
              ("RAW = unregulated: sags as the battery drains", MU)], p, step=0.15)

def s_ldo(ax, p, t):
    title(ax, "Inside any LDO regulator")
    vin = 6.0 - 2.6 * ramp(p, 0.25, 0.9)
    vout = min(3.3, vin - 0.25); drop = vout < 3.29
    G0, G1, VMAX = 2.4, 7.0, 7.0
    gy = lambda v: G0 + (G1 - G0) * v / VMAX
    for gx, v, lab, c in ((1.4, vin, "IN", RAWC), (14.0, vout, "OUT", DVC)):
        ax.add_patch(Rectangle((gx - 0.35, G0), 0.7, G1 - G0, fc=PANEL, ec=DIM, lw=1.2))
        ax.add_patch(Rectangle((gx - 0.35, G0), 0.7, gy(v) - G0, fc=c, alpha=0.85))
        ax.text(gx, G1 + 0.3, lab, color=c, fontsize=15, ha="center", weight="bold")
        ax.text(gx, G0 - 0.4, f"{v:.2f} V", color=c, fontsize=15, ha="center")
    ax.plot([1.75, 6.2], [5.5, 5.5], color=RAWC, lw=3); ax.plot([9.0, 13.65], [5.5, 5.5], color=DVC, lw=3)
    opening = min(1.0, 0.25 + 0.75 * (6.0 - vin) / (6.0 - 3.55))
    ax.add_patch(Rectangle((6.2, 4.9), 2.8, 1.2, fc=PANEL, ec=FG, lw=1.8))
    ax.add_patch(Rectangle((6.2, 5.5 - 0.5 * opening), 2.8, opening, fc=YEL, alpha=0.35))
    ax.text(7.6, 6.4, "pass transistor = valve", color=FG, fontsize=13, ha="center")
    ax.text(7.6, 5.5, f"{int(opening * 100)}% open", color=YEL, fontsize=13, ha="center", va="center")
    ax.add_patch(Polygon([[7.0, 3.0], [8.2, 3.0], [7.6, 4.1]], closed=True, fc=BG, ec=FG, lw=1.8))
    ax.plot([7.6, 7.6], [4.1, 4.9], color=FG, lw=1.5)
    ax.text(5.4, 3.35, "error amp\n(an op amp)", color=FG, fontsize=12, ha="center", va="center")
    ax.add_patch(Rectangle((11.0, 3.3), 0.3, 0.9, fc=PANEL, ec=FG)); ax.add_patch(Rectangle((11.0, 2.1), 0.3, 0.9, fc=PANEL, ec=FG))
    ax.plot([11.15, 11.15], [5.5, 4.2], color=FG, lw=1.2); ax.plot([11.15, 11.15], [3.3, 3.0], color=FG, lw=1.2)
    ax.plot([11.15, 10.2, 10.2, 8.0], [3.15, 3.15, 3.25, 3.25], color=FG, lw=1.2)
    ax.text(11.5, 3.75, "divider:\ncopy of OUT", color=MU, fontsize=11, va="center")
    ax.add_patch(FancyBboxPatch((6.2, 1.85), 1.3, 0.55, boxstyle="round,pad=0.03", fc=PANEL, ec=YEL))
    ax.text(6.85, 2.12, "1.2 V ref", color=YEL, fontsize=11, ha="center", va="center")
    ax.plot([7.2, 7.2], [2.4, 3.0], color=YEL, lw=1.2)
    ax.text(8, 7.75, "DROPOUT: valve fully open, output falls" if drop else "Regulating: output held at 3.30 V",
            color="#ef5b5b" if drop else DVC, fontsize=17, ha="center", weight="bold")

def s_u5(ax, p, t):
    title(ax, "U5: the main +3.3 V regulator")
    power_map(ax, on=("raw", "dvdd"), hi=("u5", "en"), flows=("raw", "dvdd"), t=t)
    info(ax, [("RAW in → DVDD 3.3 V out", DVC), ("/SHDN pin = 3V Enable: the main on switch", YEL), ("PWRGD unused (X = no connect)", MU),
              ("C39, C40 (2.2 µF): steady input and output", MU)], p, step=0.15)

def s_u4(ax, p, t):
    title(ax, "U4: +2.5 V for the analog side")
    power_map(ax, on=("raw", "dvdd", "avdd"), hi=("u4",), flows=("avdd",), t=t)
    info(ax, [("fed from DVDD, not RAW", DVC), ("clean input → extra-quiet AVDD", AVDC), ("EN tied to IN: on whenever DVDD is on", MU),
              ("C38 in, C35 + C37 out", MU)], p, step=0.15)

def s_neg(ax, p, t):
    title(ax, "U3 + VR1: the −2.5 V side")
    power_map(ax, on=("raw", "dvdd", "avdd", "avss"), hi=("u3", "vr1"), flows=("avss",), t=t)
    info(ax, [("U3 flips DVDD → −RAW ≈ −3.3 V (with ripple)", NEGC), ("VR1 cleans it → AVSS −2.5 V", NEGC),
              ("NR pin + C30 (0.01 µF): quieter reference", YEL), ("C36 in, C32 + C29 out", MU)], p, step=0.15)

def s_ads(ax, p, t):
    title(ax, "What the ADS1299 receives")
    power_map(ax, on=STAGES, hi=("ads",), flows=STAGES, t=t)
    info(ax, [("AVDD +2.5 V and AVSS −2.5 V", AVDC), ("= 5 V for the analog side, centred on 0 V", FG), ("DVDD +3.3 V: its digital side, and the", DVC),
              ("PIC32, RFduino, SD card, accelerometer", DVC)], p, step=0.15)

def s_end(ax, p, t):
    title(ax, "Switch on: the power-up order")
    n = int(ramp(p, 0.05, 0.75) * 4.99)
    power_map(ax, on=STAGES[:n], flows=STAGES[:n], t=t)
    steps = ["1  Battery → D9 → RAW", "2  U5 → DVDD 3.3 V", "3  U4 → AVDD +2.5 V", "4  U3 + VR1 → AVSS −2.5 V"]
    cols = [RAWC, DVC, AVDC, NEGC]
    for i, s in enumerate(steps):
        if i < n: ax.text(0.4, 7.75 - i * 0.42, s, color=cols[i], fontsize=14, va="center")


SCENES = [
 ("One battery has to feed every part of the Cyton. This video shows how the five blocks on the power supply sheet work together to make four different supply voltages.", s_title),
 ("Here's the big picture. The battery feeds a protection diode, then a three point three volt regulator. That regulator's output, called D V D D, feeds everything else: the digital chips directly, a plus two point five volt regulator for the analog side, and the voltage inverter, whose negative output goes to a minus two point five volt regulator.", s_overview),
 ("It starts at the battery, for example four double A cells, about six volts. Diode D nine protects the board if the battery is connected backwards, at the cost of about a third of a volt. What's left is called raw: the unregulated battery voltage, which sags as the battery drains.", s_battery),
 ("Each regulator on this sheet is a linear, low dropout regulator. Inside, an op amp compares a scaled copy of the output with a steady reference, and opens or closes a transistor, like a valve, to hold the output exactly. As the input falls, the valve opens wider. When the input gets too close to the output, the valve is fully open and the output starts to fall. That's called dropout.", s_ldo),
 ("U five, an M C P seventeen fifty four, turns raw into a steady three point three volts, called D V D D. Its shutdown pin is wired to the three volt enable line, so it acts as the board's main on switch. Its power good pin isn't used. Capacitors C thirty nine and C forty keep its input and output steady.", s_u5),
 ("U four makes plus two point five volts for the analog side, called A V D D. Notice it's fed from D V D D, not from raw. Its input is already clean, so its output is extra quiet. Its enable pin is tied to its input, so it runs whenever D V D D is on.", s_u4),
 ("For the negative side, the inverter U three flips D V D D into minus raw, about minus three point three volts, with some ripple. V R one, a T P S seventy two three twenty five, cleans it into a steady minus two point five volts, called A V S S. Capacitor C thirty on its noise reduction pin filters its internal reference, for an even quieter output.", s_neg),
 ("The A D S twelve ninety nine gets all three. A V D D at plus two point five and A V S S at minus two point five give its analog side five volts in total, centred on zero. D V D D at three point three volts powers its digital side, along with the PIC thirty two, the radio, the SD card and the accelerometer.", s_ads),
 ("So when you switch on: the battery feeds raw, U five makes D V D D, and both analog supplies start from it. One battery, one main regulator, and three more supplies built from its output.", s_end),
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
            fig.savefig(os.path.join(d, f"ps{i}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
