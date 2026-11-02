"""Narrated explainer video: why the input resistance of the op-amp differential amplifier is Zin = 2*R1.
Circuit as in ALL ABOUT ELECTRONICS 'Op-Amp as Differential Amplifier': floating Vin, R1 to each input, R2 feedback, R2 to ground.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_diffamp_zin_video.py  ->  diffamp_input_resistance.mp4
Preview frames: python make_diffamp_zin_video.py --stills DIR"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diffamp_input_resistance.mp4")
VOICE = "Samantha"
BG, FG, MU = "#0f1418", "#e8edf0", "#93a1aa"
WIRE, R1C, R2C, CUR, GREEN, RED, AMBER = "#8fb8e8", "#f0a04b", "#9a92ec", "#ffd166", "#6cc48a", "#ef6b5e", "#d9a441"


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


# ---------- schematic primitives ----------
def wire(ax, pts, col=WIRE, lw=2.5, alpha=1.0):
    x, y = zip(*pts); ax.plot(x, y, color=col, lw=lw, alpha=alpha, solid_capstyle="round", solid_joinstyle="round")

def resistor(ax, a, b, col, label, lab_off=(0, 0.45), lw=2.5, alpha=1.0, n=6, amp=0.22):
    (x0, y0), (x1, y1) = a, b
    L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L; nx, ny = -uy, ux
    pts = [a]
    for i in range(1, 2 * n):
        t = i / (2 * n); s = amp * (1 if i % 2 else -1)
        pts.append((x0 + ux * L * t + nx * s, y0 + uy * L * t + ny * s))
    pts.append(b); wire(ax, pts, col, lw, alpha)
    ax.text((x0 + x1) / 2 + lab_off[0], (y0 + y1) / 2 + lab_off[1], label, color=col, fontsize=17, ha="center", va="center", weight="bold", alpha=alpha)

def source(ax, c, r=0.55, label="Vin", alpha=1.0):
    ax.add_patch(Circle(c, r, fc=BG, ec=FG, lw=2.5, alpha=alpha))
    t = np.linspace(-1, 1, 40); ax.plot(c[0] + t * r * 0.55, c[1] + 0.18 * np.sin(t * math.pi), color=FG, lw=2, alpha=alpha)
    ax.text(c[0] - r - 0.25, c[1], label, color=FG, fontsize=18, ha="right", va="center", alpha=alpha)
    ax.text(c[0] + 0.05, c[1] + r + 0.15, "+", color=FG, fontsize=13, ha="left", alpha=alpha)

def ground(ax, x, y, alpha=1.0):
    for i, w in enumerate((0.45, 0.3, 0.15)):
        ax.plot([x - w, x + w], [y - i * 0.16, y - i * 0.16], color=WIRE, lw=2.5, alpha=alpha)

def dots_along(ax, pts, phase, col=CUR, spacing=0.9, size=9):
    seglens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]; total = sum(seglens)
    d = (phase * spacing) % spacing
    while d < total:
        acc = 0
        for (a, b), L in zip(zip(pts, pts[1:]), seglens):
            if d <= acc + L:
                t = (d - acc) / L; ax.plot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, "o", color=col, ms=size); break
            acc += L
        d += spacing


# circuit coordinates
SRC = (2.5, 5.0)
TOP_PATH = [(2.5, 5.55), (2.5, 7.0), (4.2, 7.0)]
R1T = ((4.2, 7.0), (6.8, 7.0))
NEG = (8.7, 7.0)
BOT_R1 = ((7.0, 3.0), (4.4, 3.0))
POSN = (8.5, 3.0)

def circuit(fig, rect=(0.04, 0.17, 0.62, 0.72), dim_r2=1.0, vshort=False, phase=None, labels_v=False):
    ax = fig.add_axes(rect); ax.set_xlim(0.5, 15.5); ax.set_ylim(0.3, 10.0); ax.axis("off"); ax.set_facecolor(BG)
    source(ax, SRC)
    wire(ax, TOP_PATH); resistor(ax, *R1T, R1C, "R1"); wire(ax, [(6.8, 7.0), NEG, (9.5, 7.0)])
    wire(ax, [(2.5, 4.45), (2.5, 3.0), (4.4, 3.0)]); resistor(ax, (4.4, 3.0), (7.0, 3.0), R1C, "R1", lab_off=(0, -0.5))
    wire(ax, [(7.0, 3.0), POSN, (8.5, 5.0), (9.5, 5.0)])
    # op amp
    ax.add_patch(Polygon([[9.5, 8.0], [9.5, 4.0], [12.2, 6.0]], closed=True, fc=BG, ec=WIRE, lw=2.5))
    ax.text(9.75, 7.0, "−", color=FG, fontsize=20, va="center"); ax.text(9.72, 5.0, "+", color=FG, fontsize=18, va="center")
    wire(ax, [(12.2, 6.0), (14.3, 6.0)]); ax.text(14.45, 6.0, "Vout", color=FG, fontsize=17, va="center")
    # R2 feedback and R2 to ground
    wire(ax, [NEG, (8.7, 9.0), (9.7, 9.0)], alpha=dim_r2); resistor(ax, (9.7, 9.0), (12.3, 9.0), R2C, "R2", alpha=dim_r2)
    wire(ax, [(12.3, 9.0), (13.3, 9.0), (13.3, 6.0)], alpha=dim_r2)
    wire(ax, [POSN, (8.5, 2.6)], alpha=dim_r2); resistor(ax, (8.5, 2.6), (8.5, 1.1), R2C, "R2", lab_off=(0.65, 0), alpha=dim_r2, n=4)
    ground(ax, 8.5, 1.0, alpha=dim_r2)
    for p in (NEG, POSN): ax.plot(*p, "o", color=WIRE, ms=7)
    if vshort:
        ax.plot([9.25, 9.25], [5.0, 7.0], color=GREEN, lw=3, ls=(0, (3, 2)))
        ax.text(9.0, 6.0, "same\nvoltage", color=GREEN, fontsize=13, ha="right", va="center", weight="bold")
    if phase is not None:
        dots_along(ax, TOP_PATH + [(6.8, 7.0), NEG], phase)
        dots_along(ax, [(7.0, 3.0), (2.5, 3.0), (2.5, 4.45)], phase)
    if labels_v:
        ax.text(3.35, 7.45, "I", color=CUR, fontsize=20, ha="center", weight="bold")
        ax.text(3.45, 2.25, "I", color=CUR, fontsize=20, ha="center", weight="bold")
    return ax


def series_loop(fig, rect, p_drop=1.0, nums=False):
    ax = fig.add_axes(rect); ax.set_xlim(0, 12); ax.set_ylim(-0.2, 8.2); ax.axis("off"); ax.set_facecolor(BG)
    source(ax, (2.0, 4.0))
    wire(ax, [(2.0, 4.55), (2.0, 6.5), (3.6, 6.5)]); resistor(ax, (3.6, 6.5), (6.6, 6.5), R1C, "R1")
    wire(ax, [(6.6, 6.5), (8.5, 6.5), (8.5, 1.5), (6.6, 1.5)]); resistor(ax, (6.6, 1.5), (3.6, 1.5), R1C, "R1", lab_off=(0, -0.5))
    wire(ax, [(3.6, 1.5), (2.0, 1.5), (2.0, 3.45)])
    ax.plot(8.5, 4.0, "o", color=GREEN, ms=12); ax.text(8.9, 4.0, "Vx  (− and +)", color=GREEN, fontsize=15, va="center")
    if p_drop > 0.3:
        ax.text(5.1, 7.7, "0.5 V" if nums else "I × R1", color=CUR, fontsize=17, ha="center", weight="bold")
    if p_drop > 0.6:
        ax.text(5.1, 0.2, "0.5 V" if nums else "I × R1", color=CUR, fontsize=17, ha="center", weight="bold")
    return ax


# ---------- scenes ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.88, "Why is Zin = 2 R1?", color=FG, fontsize=40, ha="center", weight="bold")
    fig.text(0.5, 0.81, "input resistance of the op-amp differential amplifier", color=MU, fontsize=20, ha="center")
    circuit(fig, rect=(0.2, 0.15, 0.6, 0.62), phase=t * 1.2)

def s_circuit(fig, p, t):
    title(fig, "The circuit")
    circuit(fig)
    notes = [("Vin connects only via the two R1s", R1C), ("R2 from − to the output (feedback)", R2C),
             ("R2 from + to ground", R2C), ("Op amp inputs take no current", MU)]
    for i, (s, c) in enumerate(notes):
        if p > 0.1 + i * 0.2: fig.text(0.67, 0.74 - i * 0.08, s, color=c, fontsize=16)

def s_question(fig, p, t):
    title(fig, "The question")
    circuit(fig, phase=t * 1.2)
    fig.text(0.67, 0.74, "How hard is it for Vin", color=FG, fontsize=19)
    fig.text(0.67, 0.68, "to push current in?", color=FG, fontsize=19)
    if p > 0.4:
        fig.text(0.67, 0.56, "Zin = Vin ÷ I", color=CUR, fontsize=30, weight="bold")
        fig.text(0.67, 0.49, "(voltage ÷ current, Ohm's law)", color=MU, fontsize=15)

def s_current(fig, p, t):
    title(fig, "Step 1: follow the current")
    circuit(fig, phase=t * 1.2, labels_v=True)
    lines = [("Current I leaves the top of Vin,", FG), ("goes through the top R1.", R1C),
             ("It comes back through the", FG), ("bottom R1 into Vin.", R1C),
             ("Vin has no other wire, so", FG), ("it's the SAME I both ways.", CUR)]
    for i, (s, c) in enumerate(lines):
        if p > i * 0.13: fig.text(0.67, 0.76 - i * 0.065, s, color=c, fontsize=17)

def s_vshort(fig, p, t):
    title(fig, "Step 2: the virtual short")
    circuit(fig, vshort=p > 0.25)
    lines = [("The op amp keeps − and +", FG), ("at the same voltage.", GREEN), ("Call it Vx.", GREEN),
             ("So the ends of the two R1s", FG), ("meet at the same voltage,", FG), ("as if joined by a wire.", GREEN)]
    for i, (s, c) in enumerate(lines):
        if p > 0.1 + i * 0.13: fig.text(0.67, 0.76 - i * 0.065, s, color=c, fontsize=17)

def s_simplify(fig, p, t):
    title(fig, "Step 3: what Vin actually sees")
    if p < 0.35:
        circuit(fig, vshort=True, dim_r2=1 - p / 0.35 * 0.8)
    else:
        series_loop(fig, (0.08, 0.2, 0.55, 0.68), p_drop=0)
        fig.text(0.67, 0.70, "Two R1s, one after the other,", color=FG, fontsize=19)
        fig.text(0.67, 0.64, "with the same current I.", color=FG, fontsize=19)
        if p > 0.65: fig.text(0.67, 0.52, "That's R1 in series with R1.", color=R1C, fontsize=19, weight="bold")

def s_math(fig, p, t):
    title(fig, "Step 4: add the voltage drops")
    series_loop(fig, (0.04, 0.2, 0.5, 0.68), p_drop=p * 1.6)
    eqs = [("drop on top R1     = I × R1", FG, 20), ("drop on bottom R1 = I × R1", FG, 20),
           ("Vin = I×R1 + I×R1 = 2 × I × R1", CUR, 22), ("Zin = Vin ÷ I = 2 R1", GREEN, 30)]
    for i, (s, c, f) in enumerate(eqs):
        if p > 0.1 + i * 0.2: fig.text(0.56, 0.74 - i * 0.11, s, color=c, fontsize=f, weight="bold" if i >= 2 else "normal")

def s_numbers(fig, p, t):
    title(fig, "With numbers: R1 = 10 kΩ, Vin = 1 V")
    series_loop(fig, (0.04, 0.2, 0.5, 0.68), p_drop=1.0, nums=True)
    eqs = [("Zin = 2 × 10 kΩ = 20 kΩ", FG), ("I = 1 V ÷ 20 kΩ = 50 µA", CUR), ("each R1 drops 50 µA × 10 kΩ = 0.5 V", FG),
           ("0.5 V + 0.5 V = 1 V  ✓", GREEN)]
    for i, (s, c) in enumerate(eqs):
        if p > 0.1 + i * 0.2: fig.text(0.56, 0.72 - i * 0.1, s, color=c, fontsize=21)

def s_r2(fig, p, t):
    title(fig, "Why don't the R2s count?")
    circuit(fig, vshort=True, dim_r2=0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 4)))
    lines = [("Vin's loop is: R1 → Vx → R1.", R1C), ("The R2s hang off the middle point.", R2C),
             ("They set Vx (and so the gain),", FG), ("but not the current Vin must push.", FG)]
    for i, (s, c) in enumerate(lines):
        if p > 0.05 + i * 0.18: fig.text(0.67, 0.74 - i * 0.075, s, color=c, fontsize=17)

def s_eeg(fig, p, t):
    title(fig, "Why this matters for EEG")
    ax = fig.add_axes([0.04, 0.2, 0.5, 0.68]); ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis("off"); ax.set_facecolor(BG)
    source(ax, (2.0, 4.0), label="brain")
    wire(ax, [(2.0, 4.55), (2.0, 6.5), (3.2, 6.5)]); resistor(ax, (3.2, 6.5), (6.4, 6.5), RED, "electrode 50 kΩ")
    wire(ax, [(6.4, 6.5), (8.5, 6.5), (8.5, 5.6)]); resistor(ax, (8.5, 5.6), (8.5, 2.4), R1C, "Zin 20 kΩ", lab_off=(1.6, 0))
    wire(ax, [(8.5, 2.4), (8.5, 1.5), (2.0, 1.5), (2.0, 3.45)])
    frac = 20 / 70
    if p > 0.3:
        fig.text(0.58, 0.76, "Electrode and Zin split the signal:", color=FG, fontsize=19)
        fig.text(0.58, 0.69, "20 ÷ (50 + 20) = 29 % gets in", color=RED, fontsize=19, weight="bold")
        bx = fig.add_axes([0.58, 0.56, 0.36, 0.06]); bx.axis("off"); bx.set_xlim(0, 1); bx.set_ylim(0, 1)
        bx.add_patch(Rectangle((0, 0), 1, 1, fc="#1b2329")); bx.add_patch(Rectangle((0, 0), frac * min(1, (p - 0.3) / 0.25), 1, fc=RED))
    if p > 0.65:
        fig.text(0.58, 0.45, "Fix: put a buffer before each input.", color=GREEN, fontsize=19, weight="bold")
        fig.text(0.58, 0.39, "That's the instrumentation amplifier,", color=FG, fontsize=18)
        fig.text(0.58, 0.34, "built into the ADS1299.", color=FG, fontsize=18)

def s_end(fig, p, t):
    fig.text(0.5, 0.72, "Zin = 2 R1", color=GREEN, fontsize=44, ha="center", weight="bold")
    steps = ["1. The same current I goes through both R1s.", "2. The virtual short puts − and + at the same voltage.",
             "3. So Vin sees R1 + R1 in series.", "4. Zin = Vin ÷ I = 2 R1."]
    for i, s in enumerate(steps):
        if p > 0.05 + i * 0.18: fig.text(0.24, 0.6 - i * 0.075, s, color=FG, fontsize=22)


SCENES = [
 ("Why is the input resistance of this differential amplifier equal to two times R one? Let's work it out step by step.", s_title),
 ("Here's the circuit from the video. The input source, V in, connects to the op amp only through the two R one resistors. One R two goes from the minus input to the output. The other R two goes from the plus input to ground. And remember: the op amp's inputs take no current.", s_circuit),
 ("Input resistance answers one question: how hard is it for V in to push current into the circuit? By Ohm's law, it's the input voltage divided by the current that flows.", s_question),
 ("Step one. Follow the current. It leaves the top of V in and goes through the top R one. It comes back through the bottom R one into the bottom of V in. V in has no other wire, so whatever current leaves one end must return at the other. It's the same current, I, in both resistors.", s_current),
 ("Step two. The virtual short. With negative feedback, the op amp keeps its minus and plus inputs at the same voltage. Call it V x. So the inner ends of the two R one resistors sit at the same voltage, as if they were joined by a wire.", s_vshort),
 ("Step three. Fade out everything V in doesn't directly see. What's left is a simple loop: V in, then R one, then the point V x, then the other R one, and back. Two R ones, one after the other, carrying the same current. That's R one in series with R one.", s_simplify),
 ("Step four. Add up the voltage drops. The top R one drops I times R one. The bottom R one drops I times R one. Together they must equal V in. So V in equals two times I times R one. Divide by I, and the input resistance is two R one.", s_math),
 ("Let's check with numbers. If R one is ten kilo ohms, Z in is twenty kilo ohms. With one volt in, the current is fifty micro amps. Each R one drops half a volt. Half plus half is one volt. It works.", s_numbers),
 ("Why don't the R two resistors count? Because they hang off the middle point. They decide what voltage V x is, and so they set the gain. But they don't change the current that V in has to push through its own loop.", s_r2),
 ("Why does this matter for E E G? Twenty kilo ohms is low. Your skin electrode can be fifty kilo ohms. The electrode and the input split the signal, and only about twenty nine percent of the brain signal gets through. The fix is to put a buffer in front of each input. That's the instrumentation amplifier, and it's built into the A D S twelve ninety nine.", s_eeg),
 ("To sum up. The same current flows through both R ones. The virtual short puts both inputs at the same voltage. So V in sees two R ones in series, and the input resistance is two R one.", s_end),
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
            for p in (0.2, 0.97):
                fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}_{int(p*100)}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
