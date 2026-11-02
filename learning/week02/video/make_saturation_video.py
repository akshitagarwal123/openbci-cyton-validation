"""Narrated explainer video: why the op-amp 'virtual short' (V+ = V-) stops holding once the output saturates.
Uses the inverting amplifier of Fig. 8.3 (R_in = 10k, R_F = 100k, gain -10, rails about +/-14 V) drawn as a seesaw.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_saturation_video.py  ->  virtual_short_saturation.mp4
Preview frames: python make_saturation_video.py --stills DIR"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "virtual_short_saturation.mp4")
VOICE = "Samantha"
BG, FG, MU = "#0f1418", "#e8edf0", "#93a1aa"
GRAY, PURPLE, ORANGE, RED, GREEN, BLUE = "#a8a6a0", "#9a92ec", "#f0a04b", "#ef6b5e", "#6cc48a", "#5b9be0"

RIN, RF, A_OL, RAIL = 10.0, 100.0, 100_000, 14.0
XIN, XOUT = 1.0, 9.0
XM = XIN + (XOUT - XIN) * RIN / (RIN + RF)          # where V- sits on the seesaw


def solve(vin):
    vout = max(-RAIL, min(RAIL, -RF / RIN * vin)) + 0.0
    vm = vin + (vout - vin) * RIN / (RIN + RF)
    return vout, vm


# ---------- drawing helpers ----------
def new_fig(): return plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
def sentence_at(text, p):
    parts = [x for x in re.split(r"(?<=[.?!])\s+", text) if x]
    total = sum(len(x) for x in parts); acc = 0
    for x in parts:
        acc += len(x)
        if p <= acc / total: return x
    return parts[-1]
def caption(fig, text, p):
    fig.text(0.5, 0.04, "\n".join(textwrap.wrap(sentence_at(text, p), 95)), ha="center", va="bottom", color=FG, fontsize=17,
             bbox=dict(boxstyle="round,pad=0.5", fc="#1b2329", ec="none"))
def title(fig, t): fig.text(0.04, 0.93, t, color=FG, fontsize=24, weight="bold", ha="left")
def ease(p): return 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, p)))
def seg(p, a, b): return ease((p - a) / (b - a))   # 0 before a, eases to 1 at b


def seesaw(fig, vin, rect=(0.04, 0.2, 0.6, 0.68), floor=True, labels=True):
    ax = fig.add_axes(rect); ax.set_facecolor(BG)
    ax.set_xlim(-0.2, 10.6); ax.set_ylim(-17, 17); ax.axis("off")
    vout, vm = solve(vin)
    ax.axhline(0, color=MU, lw=0.8, ls="-")
    ax.text(10.0, 0.6, "0 V", color=MU, fontsize=13)
    if floor:
        for y, lab in ((RAIL, "+14 V ceiling"), (-RAIL, "-14 V floor")):
            ax.axhline(y, color=RED, lw=1.2, ls="--", alpha=0.8)
            ax.text(5.0, y + (0.7 if y > 0 else -1.9), lab, color=RED, fontsize=12, ha="center")
        ax.fill_between([-0.2, 10.6], -17, -RAIL, color=RED, alpha=0.08)
    ax.plot([XIN, XOUT], [vin, vout], color=PURPLE, lw=5, solid_capstyle="round", zorder=2)
    gap = vm - 0.0
    if abs(gap) > 0.05:
        ax.plot([XM, XM], [0, vm], color=RED, lw=4, zorder=3)
    ax.plot(XIN, vin, "o", ms=13, color=GRAY, zorder=4)
    ax.plot(XOUT, vout, "o", ms=13, color=ORANGE, zorder=4)
    ax.plot(XM, vm, "o", ms=13, color=PURPLE if abs(gap) <= 0.05 else RED, mec=FG, mew=1.5, zorder=5)
    if labels:
        ax.text(XIN - 0.15, vin + 1.6, f"Vin\n{vin:+.2f} V", color=GRAY, fontsize=13, ha="center", va="bottom")
        ax.text(XM - 0.1, vm - 1.3, f"V-\n{vm:+.2f} V", color=FG, fontsize=13, ha="right", va="top")
        ax.text(XOUT, vout + (1.4 if vout >= 0 else -2.4), f"Vout {vout + 0.0:+.1f} V", color=ORANGE, fontsize=13, ha="center",
                va="bottom" if vout >= 0 else "top")
    return ax, vout, vm


def side_panel(fig, lines, y0=0.78):
    for i, (txt, col, size) in enumerate(lines):
        fig.text(0.665, y0 - i * 0.075, txt, color=col, fontsize=size, ha="left", va="top")


def opamp(ax, x, y, s=1.0):
    ax.add_patch(Polygon([[x, y + s], [x, y - s], [x + 1.6 * s, y]], closed=True, fc="#1b2329", ec=FG, lw=2))
    ax.text(x + 0.18 * s, y + 0.45 * s, "-", color=FG, fontsize=22, va="center")
    ax.text(x + 0.15 * s, y - 0.5 * s, "+", color=FG, fontsize=20, va="center")


# ---------- scenes ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.62, "Why the virtual short breaks", color=FG, fontsize=42, ha="center", weight="bold")
    fig.text(0.5, 0.52, "when the op amp output hits its limit", color=MU, fontsize=24, ha="center")
    seesaw(fig, 0.4 + 1.6 * ease(p), rect=(0.3, 0.17, 0.4, 0.3), labels=False)


def s_machine(fig, p, t):
    title(fig, "An op amp only does one thing")
    ax = fig.add_axes([0.05, 0.25, 0.45, 0.6]); ax.set_xlim(0, 10); ax.set_ylim(-5, 5); ax.axis("off"); ax.set_facecolor(BG)
    opamp(ax, 3.2, 0, 2.2)
    ax.plot([0.8, 3.2], [1.0, 1.0], color=PURPLE, lw=3); ax.text(0.6, 1.0, "V-", color=PURPLE, fontsize=18, ha="right", va="center")
    ax.plot([0.8, 3.2], [-1.1, -1.1], color=GREEN, lw=3); ax.text(0.6, -1.1, "V+", color=GREEN, fontsize=18, ha="right", va="center")
    ax.plot([6.7, 9.0], [0, 0], color=ORANGE, lw=3); ax.text(9.1, 0, "Vout", color=ORANGE, fontsize=18, va="center")
    fig.text(0.53, 0.76, "Vout = 100,000 × (V+  -  V-)", color=FG, fontsize=26, weight="bold")
    rows = [("difference 0.0001 V", "→  output 10 V", GREEN), ("difference 0.001 V", "→  wants 100 V", ORANGE),
            ("difference 0.1 V", "→  wants 10,000 V", RED)]
    for i, (a, b, c) in enumerate(rows):
        if p > 0.25 + 0.15 * i:
            fig.text(0.55, 0.62 - i * 0.08, a, color=FG, fontsize=20); fig.text(0.79, 0.62 - i * 0.08, b, color=c, fontsize=20)
    if p > 0.75:
        fig.text(0.55, 0.34, "But it only has ±15 V to work with,\nso the output stops near ±14 V.", color=RED, fontsize=20)


def s_seesaw_intro(fig, p, t):
    title(fig, "Feedback turns the resistors into a seesaw")
    seesaw(fig, 0.0)
    side_panel(fig, [("Left end = Vin (you set it)", GRAY, 17),
                     ("Right end = Vout (op amp moves)", ORANGE, 17),
                     ("Point near left end = V-", PURPLE, 17),
                     ("V+ is wired to 0 V, so the", GREEN, 17),
                     ("op amp keeps V- on the 0 V line.", FG, 17)])


def s_working(fig, p, t):
    title(fig, "Normal case: the op amp keeps V- on 0 V")
    vin = 1.0 * seg(p, 0.1, 0.7)
    _, vout, vm = seesaw(fig, vin)
    side_panel(fig, [(f"Vin rises to {vin:.2f} V", GRAY, 18),
                     (f"Vout pushed to {vout:.1f} V", ORANGE, 18),
                     (f"V- stays at {vm:+.2f} V", PURPLE, 18),
                     ("V+ = V-   ✓  virtual short", GREEN, 20)])


def s_why_virtual(fig, p, t):
    title(fig, "Why only 'virtually' equal?")
    seesaw(fig, 1.0, rect=(0.06, 0.2, 0.5, 0.68))
    fig.text(0.6, 0.76, "To make -10 V the op amp needs", color=FG, fontsize=20)
    fig.text(0.6, 0.68, "V+ - V-  =  10 / 100,000", color=FG, fontsize=24, weight="bold")
    fig.text(0.6, 0.60, "           =  0.0001 V", color=GREEN, fontsize=24, weight="bold")
    if p > 0.45:
        fig.text(0.6, 0.48, "Tiny, but not zero.", color=MU, fontsize=20)
        fig.text(0.6, 0.41, "That's why it's called a virtual short.", color=MU, fontsize=20)
    if p > 0.7:
        fig.text(0.6, 0.30, "It only works because the output\nis free to move wherever needed.", color=ORANGE, fontsize=20)


def s_floor(fig, p, t):
    title(fig, "Now push Vin further")
    vin = 1.0 + 1.0 * seg(p, 0.12, 0.8)
    _, vout, vm = seesaw(fig, vin)
    want = -RF / RIN * vin
    side_panel(fig, [(f"Vin = {vin:.2f} V", GRAY, 18),
                     (f"needs Vout = {want:.1f} V", FG, 18),
                     (f"gets  Vout = {vout:.1f} V", ORANGE, 18),
                     (f"V- = {vm:+.2f} V", RED if abs(vm) > 0.05 else PURPLE, 18),
                     ("V+ = 0 V", GREEN, 18)])
    if abs(vm) > 0.05:
        fig.text(0.70, 0.36, "Output is on the floor.\nV- lifts off 0 V.\nNo virtual short.", color=RED, fontsize=20, weight="bold", va="top")


def s_stuck(fig, p, t):
    title(fig, "Why can't feedback fix it?")
    seesaw(fig, 2.0, rect=(0.06, 0.2, 0.5, 0.68))
    lines = [("The op amp sees V- 0.55 V above V+.", FG),
             ("It shouts: 'push the output lower!'", ORANGE),
             ("0.55 V × 100,000 = 55,000 V wanted.", ORANGE),
             ("But the output is already on the floor.", RED),
             ("It can't move, so it can't pull V- back.", RED),
             ("The feedback loop is broken.", RED)]
    for i, (txt, c) in enumerate(lines):
        if p > i * 0.14:
            fig.text(0.58, 0.78 - i * 0.075, txt, color=c, fontsize=19)


def s_heater(fig, p, t):
    title(fig, "Like a thermostat with the heater at full blast")
    ax = fig.add_axes([0.08, 0.22, 0.84, 0.6]); ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off"); ax.set_facecolor(BG)
    for x, lab, val, col in ((1.0, "Mild day", "room 22 °C ✓", GREEN), (5.6, "Freezing day", "room 15 °C ✗", RED)):
        ax.add_patch(FancyBboxPatch((x, 1.2), 3.4, 3.8, boxstyle="round,pad=0.1", fc="#1b2329", ec=MU))
        ax.text(x + 1.7, 4.55, lab, color=FG, fontsize=20, ha="center", weight="bold")
        heat = 0.5 if x < 3 else 1.0
        ax.add_patch(FancyBboxPatch((x + 0.4, 1.6), 2.6 * heat, 0.5, boxstyle="round,pad=0.02", fc=ORANGE, ec="none"))
        ax.text(x + 1.7, 2.45, "heater " + ("half on" if heat < 1 else "100 %, maxed out"), color=ORANGE, fontsize=15, ha="center")
        if (x < 3 and p > 0.15) or (x > 3 and p > 0.45):
            ax.text(x + 1.7, 3.5, val, color=col, fontsize=22, ha="center", weight="bold")
    if p > 0.7:
        ax.text(5, 0.4, "thermostat = feedback     heater = op amp output     22 °C target = V- on 0 V", color=MU, fontsize=16, ha="center")


def s_graph(fig, p, t):
    title(fig, "The whole story in two graphs")
    v = np.linspace(0, 2.5, 300); res = [solve(x) for x in v]
    vo = np.array([r[0] for r in res]); vmm = np.array([r[1] for r in res])
    cur = 2.5 * seg(p, 0.05, 0.8); k = v <= cur
    for i, (y, lab, col, lim) in enumerate(((vo, "Vout (V)", ORANGE, (-16, 2)), (vmm * 1000, "V- (mV)", PURPLE, (-50, 650)))):
        ax = fig.add_axes([0.08 + i * 0.47, 0.24, 0.38, 0.58]); ax.set_facecolor(BG)
        for s_ in ax.spines.values(): s_.set_color(MU)
        ax.tick_params(colors=MU, labelsize=12); ax.set_xlim(0, 2.5); ax.set_ylim(*lim)
        ax.set_xlabel("Vin (V)", color=MU, fontsize=14); ax.set_title(lab, color=col, fontsize=18)
        ax.axvline(1.4, color=RED, ls="--", lw=1); ax.text(1.45, lim[0] + 0.9 * (lim[1] - lim[0]), "output hits\nthe floor", color=RED, fontsize=13, va="top")
        ax.plot(v[k], y[k], color=col, lw=3)
        if i == 0: ax.axhline(-14, color=RED, lw=0.8, alpha=0.6)
        else: ax.axhline(0, color=GREEN, lw=0.8); ax.text(0.05, 25, "V+ = 0", color=GREEN, fontsize=12)


def s_rule(fig, p, t):
    fig.text(0.5, 0.74, "The rule", color=FG, fontsize=34, ha="center", weight="bold")
    steps = ["1.  Assume V+ = V- and work out Vout.",
             "2.  Is Vout inside the supply (about ±14 V)?",
             "      Yes → your answer is right.",
             "      No  → the op amp is saturated: Vout = the rail, and V+ ≠ V-."]
    for i, s in enumerate(steps):
        if p > 0.05 + i * 0.17:
            fig.text(0.18, 0.62 - i * 0.075, s, color=[FG, FG, GREEN, RED][i], fontsize=22)
    if p > 0.8:
        fig.text(0.5, 0.22, "Same thing you saw in week 1: the ESP32 sine with the flat bottom.", color=MU, fontsize=19, ha="center")


SCENES = [
 ("Why does the virtual short stop working when an op amp saturates? Let's see it on a seesaw.", s_title),
 ("An op amp only does one thing. It takes the difference between its two inputs, and multiplies it by about one hundred thousand. A ten thousandth of a volt gives ten volts. But a bigger difference asks for hundreds or thousands of volts, and the op amp only has a fifteen volt supply. So its output stops near fourteen volts. That limit is saturation.", s_machine),
 ("In the inverting amplifier, the two resistors act like a seesaw. The left end is your input. The right end is the output, which the op amp can move. The point near the left end is the minus input. The plus input is wired to zero volts, so the op amp tries to keep that point sitting on the zero volt line.", s_seesaw_intro),
 ("Raise the input to one volt. The op amp pushes its end of the seesaw down to minus ten volts, exactly enough to keep the minus input on zero. Plus and minus inputs are equal. That is the virtual short.", s_working),
 ("Why only virtually? To make minus ten volts, the op amp needs a difference of ten divided by one hundred thousand. That's a ten thousandth of a volt. Tiny, but not zero. And it only works because the output is free to move wherever it needs to.", s_why_virtual),
 ("Now push the input further. At one point four volts, the output reaches the floor at minus fourteen volts. Keep going, and the output can't follow. The seesaw now pivots around the stuck output end, so the minus input lifts off zero. At two volts it sits at about half a volt. There is no virtual short any more.", s_floor),
 ("Why can't feedback fix it? The op amp sees the minus input half a volt too high, and tries to push the output lower. It wants fifty five thousand volts. But the output is already on the floor. It cannot move, so it cannot pull the minus input back down. The feedback loop is broken.", s_stuck),
 ("Think of a thermostat. On a mild day, it turns the heater half on and holds the room at twenty two degrees. On a freezing day, the heater is already at one hundred percent, and the room still drops. The thermostat isn't broken. It just has nothing left to give. The op amp's output at the rail is that heater at full blast.", s_heater),
 ("Here's the whole story. On the left, the output follows the input down, until it hits the floor and goes flat. On the right, the minus input stays at zero the whole time the output is free. The moment the output goes flat, the minus input starts rising.", s_graph),
 ("So, the rule. First assume plus equals minus, and work out the output. If it's inside the supply, your answer is right. If not, the op amp is saturated. The output is stuck at the rail, and the two inputs are no longer equal. You saw the same effect in week one: the ESP32 sine wave with the flat bottom.", s_rule),
]


def main():
    tmp = tempfile.mkdtemp()
    audio_files, durations = [], []
    for i, (text, _) in enumerate(SCENES):
        aiff = os.path.join(tmp, f"s{i}.aiff"); wav = os.path.join(tmp, f"s{i}.wav")
        subprocess.run(["say", "-v", VOICE, "-r", "165", "-o", aiff, text], check=True)
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
            for p in (0.5, 0.97):
                fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}_{int(p*100)}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
