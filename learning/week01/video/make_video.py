"""Narrated explainer video: why the bottom of the G25 sine goes flat with an RC load.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_video.py  ->  flat_bottom_explained.mp4"""
import math, os, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flat_bottom_explained.mp4")
VOICE = "Samantha"
BG, FG, MU = "#0f1418", "#e8edf0", "#93a1aa"
GREEN, ORANGE, RED, BLUE, AMBER = "#6cc48a", "#f0a04b", "#ef6b5e", "#5aa9e6", "#d9a441"

# Simple model matching the measurement: capacitor ~1.72 V, pin can pull at most 0.12 mA back.
CAP, SINK, MID, AMP = 1.72, 0.12, 1.65, 0.75
def wanted(ph): return MID + AMP * math.sin(2 * math.pi * ph)
def actual(ph, loaded=True):
    w = wanted(ph)
    return max(w, CAP - SINK) if loaded else w
def current(ph):                       # mA through 1 kΩ, + = out of G25
    return (actual(ph) - CAP) / 1.0

# ---------- drawing helpers ----------
def new_fig():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    return fig
def sentence_at(text, p):
    import re
    parts = [x for x in re.split(r"(?<=[.?!])\s+", text) if x]
    total = sum(len(x) for x in parts); acc = 0
    for x in parts:
        acc += len(x)
        if p <= acc / total: return x
    return parts[-1]
def caption(fig, text, p=None):
    if p is not None: text = sentence_at(text, p)
    fig.text(0.5, 0.04, "\n".join(textwrap.wrap(text, 95)), ha="center", va="bottom", color=FG, fontsize=17,
             bbox=dict(boxstyle="round,pad=0.5", fc="#1b2329", ec="none"))
def title(fig, t):
    fig.text(0.04, 0.93, t, color=FG, fontsize=24, weight="bold", ha="left")

def zigzag(ax, x0, x1, y, color, lw=3):
    xs = np.linspace(x0, x1, 10); ys = [y] + [y + (0.35 if i % 2 else -0.35) for i in range(8)] + [y]
    ax.plot(xs, ys, color=color, lw=lw)

def gnd(ax, x, y):
    for i, w in enumerate([0.45, 0.3, 0.15]):
        ax.plot([x - w, x + w], [y - i * 0.18, y - i * 0.18], color=MU, lw=2.5)

def along(path, d):
    seg = [math.dist(path[i], path[i + 1]) for i in range(len(path) - 1)]; L = sum(seg); d %= L
    for i, s in enumerate(seg):
        if d <= s:
            t = d / s; return path[i][0] + (path[i + 1][0] - path[i][0]) * t, path[i][1] + (path[i + 1][1] - path[i][1]) * t
        d -= s
    return path[-1]

PUSH = [(2.5, 6.8), (2.5, 4.5), (5, 4.5), (6.5, 4.5), (9.5, 4.5), (11.5, 4.5), (11.5, 3.75)]
PULL = [(11.5, 3.75), (11.5, 4.5), (9.5, 4.5), (6.5, 4.5), (5, 4.5), (2.5, 4.5), (2.5, 2.1)]

def circuit(fig, rect, I=0.0, off=0.0, show_r=True, state=None, v_pin=None, v_cap=None, inside=True, buffer=False):
    ax = fig.add_axes(rect); ax.set_xlim(0, 16); ax.set_ylim(0.8, 8.2); ax.axis("off"); ax.set_facecolor(BG)
    if inside:
        ax.add_patch(FancyBboxPatch((0.4, 1.4), 4.6, 6.4, boxstyle="round,pad=0.1", fc="none", ec=MU, ls="--", lw=1.5))
        ax.text(0.6, 7.95, "op-amp buffer" if buffer else "inside the ESP32 (G25 output)", color=MU, fontsize=13)
        ax.text(2.5, 7.0, "3.3 V", color=MU, ha="center", fontsize=13)
        ax.plot([2.5, 2.5], [6.8, 6.3], color=MU, lw=2.5); ax.plot([2.5, 2.5], [5.3, 3.6], color=MU, lw=2.5); ax.plot([2.5, 2.5], [2.6, 2.1], color=MU, lw=2.5)
        gnd(ax, 2.5, 2.1)
        pc = GREEN if state == "push" else "#26313a"
        ax.add_patch(Rectangle((0.8, 5.3), 3.4, 1.0, fc=pc, ec=MU, lw=1.5))
        ax.text(2.5, 5.8, "push: strong", color=BG if state == "push" else FG, ha="center", va="center", fontsize=14, weight="bold")
        qc = RED if state == "stuck" else (ORANGE if state == "pull" else "#26313a")
        ax.add_patch(Rectangle((0.8, 2.6), 3.4, 1.0, fc=qc, ec=MU, lw=1.5))
        lab = "pull: strong" if buffer else ("pull: MAXED OUT" if state == "stuck" else "pull: weak")
        ax.text(2.5, 3.1, lab, color=BG if state in ("pull", "stuck") else FG, ha="center", va="center", fontsize=12.5, weight="bold")
    ax.plot([2.5, 6.5] if inside else [5, 6.5], [4.5, 4.5], color=MU, lw=2.5)
    ax.plot([5], [4.5], "o", color=FG, ms=9); ax.text(5.15, 4.95, "G25", color=FG, fontsize=15, weight="bold")
    if show_r:
        zigzag(ax, 6.5, 9.5, 4.5, AMBER); ax.text(8, 5.25, "1 kΩ resistor", color=AMBER, ha="center", fontsize=14)
        ax.plot([9.5, 11.5], [4.5, 4.5], color=MU, lw=2.5)
    else:
        ax.text(8, 5.25, "resistor removed", color=MU, ha="center", fontsize=14, style="italic")
        ax.plot([9.5, 11.5], [4.5, 4.5], color=MU, lw=2.5)
    ax.plot([11.5, 11.5], [4.5, 3.75], color=MU, lw=2.5)
    ax.plot([10.7, 12.3], [3.75, 3.75], color=BLUE, lw=5); ax.plot([10.7, 12.3], [3.35, 3.35], color=BLUE, lw=5)
    ax.plot([11.5, 11.5], [3.35, 2.1], color=MU, lw=2.5); gnd(ax, 11.5, 2.1)
    ax.text(12.6, 3.45, "47 µF\ncapacitor", color=BLUE, fontsize=14, va="center")
    ax.text(6.2, 6.6, "G35 measures here", color=MU, fontsize=12); ax.annotate("", (6.0, 4.6), (6.6, 6.4), arrowprops=dict(arrowstyle="->", color=MU))
    ax.text(11.0, 6.6, "G34 measures here", color=MU, fontsize=12); ax.annotate("", (11.5, 4.6), (11.6, 6.4), arrowprops=dict(arrowstyle="->", color=MU))
    if v_pin is not None: ax.text(5.15, 3.75, f"{v_pin:.2f} V", color=FG, fontsize=15)
    if v_cap is not None: ax.text(12.6, 2.5, f"{v_cap:.2f} V", color=BLUE, fontsize=15, weight="bold")
    if abs(I) > 0.004 and show_r:
        path = PUSH if I > 0 else PULL; col = GREEN if I > 0 else (RED if state == "stuck" else ORANGE)
        L = sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))
        for d in np.arange(0, L, 0.9):
            x, y = along(path, d + off); ax.plot(x, y, "o", color=col, ms=9)
        ax.text(7.6, 2.95, ("current: G25 → R → capacitor" if I > 0 else "current: capacitor → R → G25") + f"   ({abs(I):.2f} mA)",
                color=col, ha="center", fontsize=14, weight="bold")
    return ax

def chart(fig, rect, ph=None, loaded=True, show_cap=True, show_want=True):
    ax = fig.add_axes(rect, facecolor=BG)
    p = np.linspace(0, 2, 400)
    if show_want: ax.plot(p, [wanted(x) for x in p], "--", color=MU, lw=1.8, label="wanted (what the code asks)")
    ax.plot(p, [actual(x, loaded) for x in p], color=ORANGE, lw=3, label="G25 actual")
    if show_cap: ax.plot(p, [CAP] * len(p), color=BLUE, lw=2.5, label="capacitor")
    if loaded:
        for k in range(2):
            a = k + 0.5 + math.asin((CAP - SINK - MID) / AMP) / (2 * math.pi) * -1 + 0.0
        mask = np.array([wanted(x) < CAP - SINK for x in p])
        ax.fill_between(p, 0.8, 2.5, where=mask, color=RED, alpha=0.15, lw=0)
    if ph is not None:
        ax.axvline(ph, color=FG, lw=1.2); ax.plot([ph], [actual(ph, loaded)], "o", color=ORANGE, ms=10)
    ax.set_ylim(0.8, 2.5); ax.set_xlim(0, 2)
    ax.set_xticks([0, 0.5, 1, 1.5, 2]); ax.set_xticklabels(["0", "5", "10", "15", "20 ms"], color=MU, fontsize=11)
    ax.set_yticks([0.9, 1.6, 2.4]); ax.set_yticklabels(["0.90 V", "1.60 V", "2.40 V"], color=MU, fontsize=11)
    for s in ax.spines.values(): s.set_color("#33404a")
    ax.grid(color="#26313a"); ax.legend(loc="upper right", fontsize=11, facecolor="#1b2329", edgecolor="none", labelcolor=FG, ncol=3)
    return ax

def state_of(ph):
    I = current(ph)
    if wanted(ph) < CAP - SINK: return "stuck", I
    return ("push" if I > 0.004 else "pull" if I < -0.004 else "idle"), I

# ---------- scenes: (narration, draw(fig, progress, t_seconds)) ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.6, "Why does the bottom of the wave go flat?", color=FG, fontsize=36, weight="bold", ha="center")
    fig.text(0.5, 0.5, "ESP32 pin G25  →  1 kΩ resistor  →  47 µF capacitor,  100 Hz sine", color=MU, fontsize=20, ha="center")
    fig.text(0.5, 0.42, "BrainTech-8 · week 1 bench lesson", color=MU, fontsize=15, ha="center")

def s_circuit(fig, p, t):
    title(fig, "The circuit"); circuit(fig, [0.03, 0.2, 0.94, 0.66], inside=False)

def s_seen(fig, p, t):
    title(fig, "What the plotter showed"); chart(fig, [0.08, 0.22, 0.86, 0.6], ph=None, show_cap=p > 0.55, show_want=p > 0.3)

def s_inside(fig, p, t):
    title(fig, "Inside G25: a strong pusher and a weak puller")
    circuit(fig, [0.0, 0.45, 1.0, 0.44], state="push" if (t % 4) < 2 else "pull", inside=True)
    ax = fig.add_axes([0.2, 0.2, 0.6, 0.2], facecolor=BG)
    ax.barh([1, 0], [34, 0.12], color=[GREEN, RED]); ax.set_yticks([1, 0]); ax.set_yticklabels(["push\n(out of pin)", "pull\n(into pin)"], color=FG, fontsize=13)
    ax.set_xscale("log"); ax.set_xlim(0.05, 100); ax.tick_params(colors=MU)
    ax.text(34, 1, "  ~34 mA", va="center", color=FG, fontsize=14, ha="right"); ax.text(0.14, 0, " 0.12 mA", va="center", color=FG, fontsize=14)
    ax.set_title("how much current each stage can handle (log scale)", color=MU, fontsize=12)
    for s in ax.spines.values(): s.set_color("#33404a")

def s_rule(fig, p, t):
    title(fig, "The rule: current flows from higher voltage to lower voltage")
    up = p < 0.5
    circuit(fig, [0.03, 0.2, 0.94, 0.66], I=0.5 if up else -0.08, off=t * 3, state="push" if up else "pull",
            v_pin=2.2 if up else 1.65, v_cap=CAP)
    fig.text(0.5, 0.86, "G25 ABOVE the capacitor  →  current flows OUT of G25" if up else "G25 BELOW the capacitor  →  current flows back INTO G25",
             color=GREEN if up else ORANGE, fontsize=19, ha="center", weight="bold")

def make_cycle(cycles):
    def s(fig, p, t):
        ph = (p * cycles) % 1.0
        st, I = state_of(ph)
        title(fig, {"push": "Going up: G25 pushes", "pull": "Going down: G25 pulls (small current, OK)",
                    "stuck": "Bottom: the pull is maxed out, so G25 is stuck", "idle": "Crossing over"}[st])
        circuit(fig, [0.0, 0.45, 1.0, 0.44], I=I, off=t * (1.5 + 6 * abs(I)), state=st, v_pin=actual(ph), v_cap=CAP)
        chart(fig, [0.08, 0.2, 0.86, 0.22], ph=ph)
    return s

def s_math(fig, p, t):
    title(fig, "The numbers at the bottom of the wave")
    lines = ["Capacitor holds about 1.72 V",
             "Code wants G25 at 0.90 V",
             "Current that would flow back = (1.72 − 0.90) V ÷ 1 kΩ = 0.82 mA",
             "G25 can only pull 0.12 mA",
             "Lowest G25 can get = 1.72 V − 0.12 mA × 1 kΩ = 1.60 V   →   flat bottom"]
    for i, l in enumerate(lines):
        if p > i / len(lines) * 0.9:
            fig.text(0.08, 0.76 - i * 0.1, l, color=RED if i >= 3 else FG, fontsize=21, weight="bold" if i == 4 else "normal")

def s_nores(fig, p, t):
    title(fig, "Remove the resistor: nothing flows back, so the full sine appears")
    circuit(fig, [0.0, 0.45, 1.0, 0.44], show_r=False, state="push" if math.sin(t * 3) > 0 else "pull", inside=True)
    chart(fig, [0.08, 0.2, 0.86, 0.22], ph=(t * 0.4) % 2, loaded=False, show_cap=False)

def s_fix(fig, p, t):
    title(fig, "The fix: an op-amp buffer pushes AND pulls strongly")
    ph = (t * 0.25) % 1; I = (wanted(ph) - CAP)
    circuit(fig, [0.0, 0.45, 1.0, 0.44], I=I, off=t * 4, state="push" if I > 0 else "pull", buffer=True, v_cap=MID)
    ax = chart(fig, [0.08, 0.2, 0.86, 0.22], loaded=False, show_cap=False)

def s_end(fig, p, t):
    fig.text(0.5, 0.62, "A pin can only reach a voltage", color=FG, fontsize=32, ha="center", weight="bold")
    fig.text(0.5, 0.53, "if it can handle the current that voltage causes.", color=FG, fontsize=32, ha="center", weight="bold")
    fig.text(0.5, 0.4, "Check that a source can both push and pull before connecting a load.", color=MU, fontsize=19, ha="center")

SCENES = [
 ("Why does the bottom of the sine wave go flat? Let's look at exactly what happens inside the circuit.", s_title),
 ("Here is the circuit. ESP32 pin G25 makes a sine wave. It goes through a 1 kilo-ohm resistor into a 47 microfarad capacitor, which connects to ground. G35 measures the voltage before the resistor, and G34 measures the voltage on the capacitor.", s_circuit),
 ("On the plotter, the top half of the wave looked like a sine. But the bottom half was flat. The dashed line is what the code asked for. The blue line is the capacitor, sitting at about 1.72 volts.", s_seen),
 ("Inside G25 there are two jobs. A push stage sends current out of the pin. It is strong: you measured about 34 milliamps. A pull stage takes current back into the pin. It is weak: only about 0.12 milliamps. That is around 300 times weaker.", s_inside),
 ("Now the key rule. Current always flows from the higher voltage to the lower voltage. The capacitor holds about 1.72 volts, like a tiny battery. When G25 is above the capacitor, current flows out of G25, through the resistor, into the capacitor. When G25 goes below the capacitor, current flows the other way: from the capacitor, back through the resistor, into G25.", s_rule),
 ("Let's watch one cycle in slow motion. Going up, G25 is above the capacitor, so it pushes current out. The push stage is strong, so the voltage follows the sine perfectly. Coming down, G25 drops below the capacitor and current reverses. While it is small, the weak pull stage can handle it. But near the bottom, the capacitor sends back more current than the pull stage can take. The pull stage is maxed out, so G25 cannot go any lower. It stays stuck. That is the flat bottom, shown in red.", make_cycle(2.0)),
 ("Here are the numbers. To reach 0.9 volts, about 0.82 milliamps would have to flow back into G25. It can only take 0.12 milliamps. So the lowest it can reach is 1.72 volts minus 0.12 volts, which is 1.6 volts. Exactly the flat bottom you measured.", s_math),
 ("When you pulled out the resistor, nothing could flow back into G25. The pin only had to show a voltage, not swallow current. So the weak pull stage was enough, and the full sine wave appeared.", s_nores),
 ("The fix is an op-amp buffer between G25 and the filter. An op-amp output can push and pull several milliamps, so the whole sine reaches the filter. You will build this next week.", s_fix),
 ("The lesson: a pin can only reach a voltage if it can handle the current that voltage causes. Always check that a source can both push and pull before you connect a load.", s_end),
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
    main()
