"""Narrated explainer video: positive feedback and the Schmitt trigger (book section 8.5, Fig. 8.17).
Circuit: Vin -> R1 (10k) -> V+ ; R2 (100k) from Vout back to V+ ; V- grounded ; rails +/-15 V.
Thresholds +/-VT = +/-15 * R1/R2 = +/-1.5 V, hysteresis 3 V.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_positive_feedback_video.py  ->  positive_feedback_schmitt.mp4
Preview frames: python make_positive_feedback_video.py --stills DIR"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positive_feedback_schmitt.mp4")
VOICE = "Samantha"
BG, FG, MU = "#0f1418", "#e8edf0", "#93a1aa"
GRAY, PURPLE, ORANGE, RED, GREEN, BLUE, AMBER = "#a8a6a0", "#9a92ec", "#f0a04b", "#ef6b5e", "#6cc48a", "#5b9be0", "#d9a441"
R1, R2, RAIL = 10.0, 100.0, 15.0
VT = RAIL * R1 / R2            # 1.5 V
XIN, XOUT = 1.0, 9.0
XP = XIN + (XOUT - XIN) * R1 / (R1 + R2)


def vplus(vin, vout): return vin + (vout - vin) * R1 / (R1 + R2)


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
def seg(p, a, b): return ease((p - a) / (b - a))
def side(fig, lines, x=0.665, y0=0.78, dy=0.07, p=1.0, step=0.0):
    for i, (s, c, f) in enumerate(lines):
        if p >= i * step: fig.text(x, y0 - i * dy, s, color=c, fontsize=f, va="top")


# a fixed noisy signal that wanders around 0 V (like the book's Vin trace)
_rng = np.random.default_rng(3)
T = np.linspace(0, 1, 700)
NOISY = 2.6 * np.sin(2 * np.pi * 2.2 * T + 0.4) + 0.55 * np.convolve(_rng.normal(0, 1, 700), np.ones(5) / 5, "same") * 2.2

def plain_comparator(v): return np.where(v > 0, RAIL, -RAIL)
def schmitt(v, start=RAIL):
    out = np.empty_like(v); s = start
    for i, x in enumerate(v):
        if s > 0 and x < -VT: s = -RAIL
        elif s < 0 and x > VT: s = RAIL
        out[i] = s
    return out


def wave_axes(fig, rect, p, out, show_thr=False):
    n = max(2, int(len(T) * p))
    a1 = fig.add_axes([rect[0], rect[1] + rect[3] * 0.55, rect[2], rect[3] * 0.42]); a2 = fig.add_axes([rect[0], rect[1], rect[2], rect[3] * 0.42])
    for ax in (a1, a2):
        ax.set_facecolor(BG); ax.set_xlim(0, 1); ax.set_xticks([])
        for s_ in ax.spines.values(): s_.set_color("#2a343b")
        ax.tick_params(colors=MU, labelsize=11)
    a1.set_ylim(-4.5, 4.5); a2.set_ylim(-19, 19); a2.set_yticks([-15, 0, 15])
    a1.axhline(0, color=MU, lw=0.8)
    if show_thr:
        for v in (VT, -VT): a1.axhline(v, color=AMBER, lw=1.2, ls="--")
        a1.text(1.01, VT, "+1.5 V", color=AMBER, fontsize=12, va="center", transform=a1.get_yaxis_transform())
        a1.text(1.01, -VT, "-1.5 V", color=AMBER, fontsize=12, va="center", transform=a1.get_yaxis_transform())
    else:
        a1.text(1.01, 0, "0 V", color=MU, fontsize=12, va="center", transform=a1.get_yaxis_transform())
    a1.plot(T[:n], NOISY[:n], color=BLUE, lw=1.8); a1.set_ylabel("Vin", color=BLUE, fontsize=14)
    a2.plot(T[:n], out[:n], color=ORANGE, lw=2.2); a2.set_ylabel("Vout", color=ORANGE, fontsize=14)
    return a1, a2


def seesaw(fig, vin, vout, rect=(0.04, 0.2, 0.6, 0.68)):
    ax = fig.add_axes(rect); ax.set_facecolor(BG); ax.set_xlim(-0.2, 10.8); ax.set_ylim(-17.5, 17.5); ax.axis("off")
    ax.axhline(0, color=MU, lw=1)
    ax.text(10.05, 0.6, "0 V", color=MU, fontsize=12)
    for y in (RAIL, -RAIL):
        ax.axhline(y, color=RED, lw=1, ls="--", alpha=0.7)
        ax.text(5.0, y + (0.7 if y > 0 else -1.9), f"{y:+.0f} V rail", color=RED, fontsize=12, ha="center")
    vp = vplus(vin, vout)
    ax.plot([XIN, XOUT], [vin, vout], color=PURPLE, lw=5, solid_capstyle="round")
    ax.plot(XIN, vin, "o", ms=13, color=BLUE); ax.plot(XOUT, vout, "o", ms=13, color=ORANGE)
    col = GREEN if vp > 0 else RED
    ax.plot(XP, vp, "o", ms=14, color=col, mec=FG, mew=1.5, zorder=5)
    ax.text(XIN - 0.15, vin + (1.4 if vin >= 0 else -1.4), f"Vin\n{vin:+.2f} V", color=BLUE, fontsize=13, ha="center", va="bottom" if vin >= 0 else "top")
    ax.text(XP + 0.3, vp + (-1.6 if vout > 0 else 1.6), f"V+ {vp:+.2f} V", color=col, fontsize=13, ha="left", va="top" if vout > 0 else "bottom")
    ax.text(XOUT, vout + (1.2 if vout > 0 else -1.2), f"Vout {vout:+.0f} V", color=ORANGE, fontsize=13, ha="center", va="bottom" if vout > 0 else "top")
    return vp


# ---------- scenes ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.82, "Positive feedback", color=FG, fontsize=42, ha="center", weight="bold")
    fig.text(0.5, 0.75, "and the Schmitt trigger (section 8.5, Fig. 8.17)", color=MU, fontsize=21, ha="center")
    wave_axes(fig, (0.15, 0.2, 0.7, 0.45), ease(p), schmitt(NOISY), show_thr=True)


def ball(ax, x, y, col): ax.plot(x, y, "o", ms=26, color=col, zorder=5)

def s_neg_vs_pos(fig, p, t):
    title(fig, "Negative vs positive feedback")
    xs = np.linspace(-1, 1, 200)
    for i, (name, sign, col, sub) in enumerate((("Negative feedback", 1, GREEN, "output fed to the − input"),
                                                  ("Positive feedback", -1, RED, "output fed to the + input"))):
        ax = fig.add_axes([0.06 + i * 0.48, 0.22, 0.42, 0.6]); ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.4, 1.35); ax.axis("off")
        ys = 0.5 + sign * 0.45 * xs ** 2 if sign > 0 else 0.95 - 0.45 * xs ** 2
        ax.plot(xs, ys, color=MU, lw=3)
        ax.text(0, 1.28, name, color=col, fontsize=22, ha="center", weight="bold"); ax.text(0, 1.15, sub, color=MU, fontsize=15, ha="center")
        k = seg(p, 0.35, 0.9)
        if sign > 0:
            x = 0.6 * math.cos(t * 3) * (1 - 0.85 * k); ball(ax, x, 0.5 + 0.45 * x * x + 0.07, col)
            ax.text(0, 0.0, "a ball in a valley:\nnudge it and it rolls back", color=FG, fontsize=16, ha="center", va="top")
        else:
            x = 0.02 + 0.95 * k * k; ball(ax, min(x, 0.97), 0.95 - 0.45 * min(x, 0.97) ** 2 + 0.07, col)
            ax.text(0, 0.0, "a ball on a hilltop:\nnudge it and it runs away", color=FG, fontsize=16, ha="center", va="top")


def s_comparator(fig, p, t):
    title(fig, "Problem: a plain comparator chatters")
    wave_axes(fig, (0.08, 0.2, 0.62, 0.66), seg(p, 0.0, 0.85), plain_comparator(NOISY))
    side(fig, [("Vin > 0 → +15 V", FG, 16), ("Vin < 0 → −15 V", FG, 16),
               ("Noise crosses 0", BLUE, 16), ("many times...", BLUE, 16),
               ("so the output", RED, 16), ("chatters.", RED, 16)], x=0.765, p=p, step=0.12)


def s_thermostat(fig, p, t):
    title(fig, "The fix: two thresholds (hysteresis)")
    side(fig, [("A good thermostat doesn't switch at one temperature:", FG, 20),
               ("heater ON  when it drops below 20 °C", BLUE, 20),
               ("heater OFF when it rises above 22 °C", RED, 20),
               ("between 20 and 22 °C: it keeps doing what it was doing", GREEN, 20),
               ("Small wiggles near 21 °C can't make it flicker.", FG, 20),
               ("That gap between the two switch points is called hysteresis.", AMBER, 20)], x=0.08, y0=0.8, dy=0.09, p=p, step=0.14)


def s_circuit(fig, p, t):
    title(fig, "The circuit: the seesaw again, on the + input")
    seesaw(fig, 0.0, RAIL)
    side(fig, [("Vin → R1 (10 kΩ) → + input", BLUE, 17), ("R2 (100 kΩ) from Vout → + input", ORANGE, 17),
               ("− input wired to ground (0 V)", MU, 17), ("", FG, 10),
               ("No feedback to − , so the op amp", FG, 17), ("just compares: is V+ above 0?", FG, 17),
               ("   yes → Vout = +15 V", GREEN, 17), ("   no  → Vout = −15 V", RED, 17)], p=p, step=0.1)


def s_high(fig, p, t):
    title(fig, "Output high, Vin = 0 V")
    seesaw(fig, 0.0, RAIL)
    side(fig, [("I = 15 V ÷ 110 kΩ = 0.136 mA", FG, 16), ("R1 drops 0.136 mA × 10 kΩ", FG, 16),
               ("V+ = 1.36 V, above 0", GREEN, 18), ("→ output stays at +15 V", GREEN, 18), ("", FG, 10),
               ("The output holds the + input up.", ORANGE, 17), ("It helps itself stay high.", ORANGE, 17)], p=p, step=0.12)


def s_flip_down(fig, p, t):
    title(fig, "Lower Vin until V+ reaches 0")
    k = seg(p, 0.05, 0.6); vin = -VT * k
    vout = RAIL
    if p > 0.66: vin = -VT - 0.02; vout = RAIL - 2 * RAIL * seg(p, 0.66, 0.74)
    vp = seesaw(fig, vin, vout)
    side(fig, [(f"Vin = {vin:+.2f} V", BLUE, 18), (f"V+ = {vp:+.2f} V", GREEN if vp > 0 else RED, 18)], p=1)
    if p > 0.5:
        side(fig, [("At Vin = −1.5 V, V+ hits 0", AMBER, 18), ("→ output flips to −15 V", RED, 18),
                   ("...which drags V+ even lower:", RED, 17), ("the snap. That's positive feedback.", RED, 17)], y0=0.6, p=(p - 0.5) * 2, step=0.2)


def s_low(fig, p, t):
    title(fig, "Now the output is low. Bring Vin back up")
    k = seg(p, 0.05, 0.75); vin = -VT + 2 * VT * k
    vout = -RAIL
    if p > 0.8: vin = VT + 0.02; vout = -RAIL + 2 * RAIL * seg(p, 0.8, 0.88)
    vp = seesaw(fig, vin, vout)
    side(fig, [(f"Vin = {vin:+.2f} V", BLUE, 18), (f"V+ = {vp:+.2f} V", GREEN if vp > 0 else RED, 18)], p=1)
    if p > 0.3:
        side(fig, [("At Vin = 0, V+ is −1.36 V:", FG, 17), ("still low. It does NOT flip back!", AMBER, 17),
                   ("It only flips at Vin = +1.5 V.", GREEN, 18)], y0=0.6, p=(p - 0.3) * 2, step=0.3)


def s_noisy(fig, p, t):
    title(fig, "Same noisy input, now with hysteresis")
    wave_axes(fig, (0.08, 0.2, 0.62, 0.66), seg(p, 0.0, 0.85), schmitt(NOISY), show_thr=True)
    side(fig, [("Low only below", RED, 16), ("  −1.5 V", RED, 16), ("High only above", GREEN, 16), ("  +1.5 V", GREEN, 16),
               ("Wiggles between", FG, 16), ("are ignored.", FG, 16), ("Clean ✓", ORANGE, 18)], x=0.775, p=p, step=0.15)


def s_formula(fig, p, t):
    title(fig, "The numbers from the book")
    lines = [("Threshold:  VT = Vout × R1 / R2 = 15 × 10k / 100k = 1.5 V", FG, 22),
             ("Switch down at −VT = −1.5 V,   switch up at +VT = +1.5 V", FG, 22),
             ("Hysteresis:  Vh = (+1.5) − (−1.5) = 3 V", AMBER, 24),
             ("Want a wider gap?  Make R2 smaller (more feedback).", GREEN, 20),
             ("Want a narrower gap?  Make R2 bigger.", GREEN, 20)]
    side(fig, lines, x=0.08, y0=0.8, dy=0.1, p=p, step=0.17)


def s_uses(fig, p, t):
    title(fig, "Where you'll meet it")
    lines = [("Positive feedback = make a decision and stick to it.", FG, 22),
             ("• Turning a noisy signal into clean on/off", FG, 20),
             ("• Button debouncing, battery-low alarms", FG, 20),
             ("• Your ESP32's input pins have Schmitt triggers built in", FG, 20),
             ("Not in the EEG signal path: there we want negative feedback,", AMBER, 20),
             ("so the output follows the brain signal smoothly.", AMBER, 20)]
    side(fig, lines, x=0.08, y0=0.8, dy=0.09, p=p, step=0.15)


SCENES = [
 ("This video explains positive feedback, and the circuit it's most useful for: the Schmitt trigger.", s_title),
 ("With negative feedback, the output is sent back to the minus input, and it fights any change. It's like a ball in a valley: nudge it and it rolls back. With positive feedback, the output goes to the plus input, and it helps the change. Like a ball on a hilltop: nudge it, and it runs all the way down, to the supply rail.", s_neg_vs_pos),
 ("So why would anyone want that? Start with a plain comparator. If the input is above zero, the output is plus fifteen volts. If it's below zero, minus fifteen. But real signals are noisy. Every time the noise wiggles across zero, the output flips. It chatters back and forth.", s_comparator),
 ("The fix is two thresholds. A good thermostat turns the heater on below twenty degrees, and off above twenty two. In between, it keeps doing whatever it was doing. Small wiggles can't make it flicker. That gap is called hysteresis.", s_thermostat),
 ("Here's the book's circuit. The input goes through R one, ten kilo ohms, to the plus input. R two, a hundred kilo ohms, goes from the output back to the plus input. The minus input is grounded. Notice: it's the same seesaw as before, but now the middle point is the plus input. The op amp just asks: is the plus input above zero? If yes, the output is plus fifteen. If no, minus fifteen.", s_circuit),
 ("Say the output is high, and the input is zero. Fifteen volts across a hundred and ten kilo ohms gives zero point one three six milli amps. That puts the plus input at one point three six volts. Above zero, so the output stays high. The output is holding its own plus input up. It helps itself stay where it is.", s_high),
 ("Now lower the input. The plus input drops. At minus one point five volts, it reaches zero, and the output flips to minus fifteen. And the moment it flips, it drags the plus input even lower. That's the snap of positive feedback. There's no going halfway.", s_flip_down),
 ("Now bring the input back up. At zero volts, the plus input is minus one point three six volts. Still below zero, so the output stays low. It does not flip back at zero. It only flips back when the input passes plus one point five volts.", s_low),
 ("Here's the same noisy input as before, now through this circuit. The output only goes low when the input drops below minus one point five volts, and only goes high above plus one point five. All the small wiggles in between are ignored. Clean output.", s_noisy),
 ("The book's numbers. The threshold is the output voltage times R one over R two: fifteen times ten over a hundred, which is one point five volts. The hysteresis is the gap between the two thresholds: three volts. A smaller R two gives more feedback, and a wider gap.", s_formula),
 ("Positive feedback means: make a decision, and stick to it. It's used to clean up noisy on and off signals, debounce buttons, and raise battery alarms. Your E S P thirty two's input pins have Schmitt triggers built in. But it's not used in the E E G signal path. There, you want negative feedback, so the output follows the brain signal smoothly.", s_uses),
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
            for p in (0.45, 0.97):
                fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}_{int(p*100)}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
