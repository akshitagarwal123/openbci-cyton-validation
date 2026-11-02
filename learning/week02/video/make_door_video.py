"""Narrated explainer video (simple version): the 'door game' analogy for why the op-amp virtual short breaks at saturation.
Same circuit as make_saturation_video.py: inverting amplifier, R_in = 10k, R_F = 100k, gain -10, output limit about 14 V.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_door_video.py  ->  door_game_virtual_short.mp4
Preview frames: python make_door_video.py --stills DIR"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrow, FancyBboxPatch, Rectangle

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "door_game_virtual_short.mp4")
VOICE = "Samantha"
BG, FG, MU = "#0f1418", "#e8edf0", "#93a1aa"
FRIEND, YOU, DOOR, RED, GREEN, WOOD = "#5b9be0", "#f0a04b", "#c99a6b", "#ef6b5e", "#6cc48a", "#8a6440"
MAX = 14.0
RIN, RF = 10.0, 100.0


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


def person(ax, x, col, facing):
    ax.add_patch(Circle((x, 3.9), 0.32, fc=col, ec="none"))
    ax.plot([x, x], [3.55, 2.2], color=col, lw=5, solid_capstyle="round")
    ax.plot([x, x - 0.45], [2.2, 1.0], color=col, lw=5, solid_capstyle="round")
    ax.plot([x, x + 0.45], [2.2, 1.0], color=col, lw=5, solid_capstyle="round")
    ax.plot([x, x + 0.75 * facing], [3.2, 3.0], color=col, lw=5, solid_capstyle="round")


def door_scene(fig, push, names=("Friend", "You"), units="", show_meters=True, rect=(0.05, 0.36, 0.9, 0.52)):
    """push = how hard the left side pushes. The right side pushes back up to MAX. Extra force opens the door."""
    back = min(push, MAX); extra = push - back
    ang = math.radians(min(40, extra * 6.5))
    ax = fig.add_axes(rect); ax.set_xlim(0, 16); ax.set_ylim(0.4, 5.2); ax.axis("off"); ax.set_facecolor(BG)
    ax.plot([0.5, 15.5], [1.0, 1.0], color=MU, lw=1.5)
    ax.add_patch(Rectangle((7.75, 1.0), 0.5, 3.9, fc="none", ec=WOOD, lw=1, ls="--"))  # closed position
    hx, hy, L = 8.0, 1.0, 3.9
    tx, ty = hx + L * math.sin(ang), hy + L * math.cos(ang)
    ax.plot([hx, tx], [hy, ty], color=DOOR, lw=16, solid_capstyle="butt")
    ax.plot(hx, hy, "o", color=WOOD, ms=10)
    person(ax, 4.6, FRIEND, +1); person(ax, 11.4 + (tx - hx) * 0.9, YOU, -1)
    py = hy + 2.9 * math.cos(ang); pxd = hx + 2.9 * math.sin(ang)
    if push > 0.05:
        w = 0.12 + 0.03 * push
        ax.add_patch(FancyArrow(5.5, py, pxd - 5.5 - 0.25, 0, width=w, head_width=w * 2.4, head_length=0.35, fc=FRIEND, ec="none", length_includes_head=True))
    if back > 0.05:
        w = 0.12 + 0.03 * back; sx = 10.5 + (tx - hx) * 0.9
        ax.add_patch(FancyArrow(sx, py + 0.45, (pxd + 0.25) - sx, 0, width=w, head_width=w * 2.4, head_length=0.35, fc=YOU, ec="none", length_includes_head=True))
    ax.text(4.6, 0.55, names[0], color=FRIEND, fontsize=17, ha="center", weight="bold")
    ax.text(11.4 + (tx - hx) * 0.9, 0.55, names[1], color=YOU, fontsize=17, ha="center", weight="bold")
    shut = extra < 0.05
    ax.text(8.0, 5.0, "door closed ✓" if shut else "door opens ✗", color=GREEN if shut else RED, fontsize=19, ha="center", weight="bold")
    if show_meters:
        mx = fig.add_axes([0.12, 0.17, 0.76, 0.15]); mx.set_xlim(-4.5, 21); mx.set_ylim(0, 2.2); mx.axis("off"); mx.set_facecolor(BG)
        for y, val, col, lab in ((1.5, push, FRIEND, names[0]), (0.45, back, YOU, names[1])):
            mx.add_patch(Rectangle((0, y - 0.25), 20, 0.5, fc="#1b2329", ec="none"))
            mx.add_patch(Rectangle((0, y - 0.25), min(val, 20), 0.5, fc=RED if (col == YOU and val >= MAX - 1e-6 and extra > 0.05) else col, ec="none"))
            mx.text(-0.4, y, lab, color=col, fontsize=14, ha="right", va="center")
            mx.text(min(val, 20) + 0.3, y, f"{val:.1f}{units}", color=FG, fontsize=13, va="center")
        mx.plot([MAX, MAX], [0.05, 0.95], color=RED, ls="--", lw=1.5)
        mx.text(MAX, -0.05, f"max {MAX:.0f}{units}", color=RED, fontsize=12, ha="center", va="top")
    return extra


# ---------- scenes ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.86, "The door game", color=FG, fontsize=42, ha="center", weight="bold")
    fig.text(0.5, 0.79, "why the op amp's virtual short breaks", color=MU, fontsize=22, ha="center")
    door_scene(fig, 6 + 12 * ease(p), show_meters=False, rect=(0.15, 0.2, 0.7, 0.5))


def s_rules(fig, p, t):
    title(fig, "The rules")
    door_scene(fig, 0.0)
    if p > 0.3:
        fig.text(0.5, 0.33, "Your job: push back exactly as hard, so the door stays closed.", color=YOU, fontsize=19, ha="center")


def s_little(fig, p, t):
    title(fig, "Friend pushes a little")
    door_scene(fig, 5 * seg(p, 0.1, 0.6))


def s_harder(fig, p, t):
    title(fig, "Friend pushes harder")
    door_scene(fig, 5 + 9 * seg(p, 0.1, 0.7))


def s_too_hard(fig, p, t):
    title(fig, "Friend pushes harder than you possibly can")
    e = door_scene(fig, 14 + 6 * seg(p, 0.12, 0.65))
    if e > 0.05 and p > 0.6:
        fig.text(0.5, 0.33, "You're at your maximum. You didn't stop trying. You ran out of strength.", color=RED, fontsize=18, ha="center")


def s_map(fig, p, t):
    title(fig, "Now swap in the op amp")
    rows = [("Your friend pushing", "the input signal, Vin", FRIEND),
            ("You pushing back", "the op amp's output", YOU),
            ("Door stays closed", "V+ and V- stay equal: the virtual short", GREEN),
            ("Your maximum strength", "the power supply, about 14 V", RED),
            ("Door opens", "V+ and V- become different", RED)]
    fig.text(0.1, 0.80, "Door game", color=MU, fontsize=18, weight="bold"); fig.text(0.47, 0.80, "Op amp", color=MU, fontsize=18, weight="bold")
    for i, (a, b, c) in enumerate(rows):
        if p > 0.04 + i * 0.17:
            y = 0.70 - i * 0.095
            fig.text(0.1, y, a, color=FG, fontsize=21); fig.text(0.40, y, "→", color=MU, fontsize=21); fig.text(0.47, y, b, color=c, fontsize=21)


def solve(vin):
    vout = max(-MAX, min(MAX, -RF / RIN * vin)) + 0.0
    return vout, vin + (vout - vin) * RIN / (RIN + RF)


def s_opamp(fig, p, t):
    title(fig, "Same game, real volts (gain 10)")
    stops = [0.5, 1.0, 1.4, 2.0]
    k = min(3, int(p * 4)); q = p * 4 - k
    prev = stops[k - 1] if k > 0 else 0.0
    vin = prev + (stops[k] - prev) * seg(q, 0.0, 0.4)
    vout, vm = solve(vin)
    door_scene(fig, 10 * vin, names=("Vin side", "Op amp"), units=" V", rect=(0.05, 0.42, 0.9, 0.46))
    ok = abs(vm) < 0.01
    txt = f"Vin = {vin:.2f} V    needs output {-10 * vin:.1f} V    gets {vout:.1f} V    V- = {vm:+.2f} V"
    fig.text(0.5, 0.36, txt, color=FG, fontsize=18, ha="center")
    fig.text(0.96, 0.93, "virtual short holds ✓" if ok else "virtual short broken ✗", color=GREEN if ok else RED, fontsize=20, ha="right", weight="bold")


def s_end(fig, p, t):
    fig.text(0.5, 0.68, "V+ = V- is not automatic.", color=FG, fontsize=34, ha="center", weight="bold")
    fig.text(0.5, 0.58, "The op amp makes it true by pushing back with its output.", color=MU, fontsize=22, ha="center")
    if p > 0.35:
        fig.text(0.5, 0.45, "When the output hits the supply limit, it can't push any harder,", color=RED, fontsize=22, ha="center")
        fig.text(0.5, 0.39, "so the 'door' opens and V+ and V- separate.", color=RED, fontsize=22, ha="center")
    if p > 0.7:
        fig.text(0.5, 0.26, "That's saturation.", color=YOU, fontsize=26, ha="center", weight="bold")


SCENES = [
 ("Let's understand the virtual short with a simple game.", s_title),
 ("Here's the game. Your friend pushes a door from the left. You push from the right. Your job is to push back exactly as hard, so the door stays closed. The bars at the bottom show how hard each of you is pushing.", s_rules),
 ("Your friend pushes a little. You push back a little. The door stays closed.", s_little),
 ("Your friend pushes harder. You push back harder. The door is still closed. But look at your bar. You're getting close to your maximum strength.", s_harder),
 ("Now your friend pushes even harder. You're already pushing with everything you've got. You can't push any more, so the door opens. You didn't stop trying. You just ran out of strength.", s_too_hard),
 ("Now swap in the op amp. Your friend is the input signal. You are the op amp's output. The door staying closed means the two inputs stay equal. That's the virtual short. Your maximum strength is the power supply, about fourteen volts. And the door opening means the two inputs are no longer equal.", s_map),
 ("Here's the same game with real numbers, in an amplifier with a gain of ten. Half a volt in: the op amp pushes back with five volts. Door closed. One volt in: ten volts back. Still closed. One point four volts in: fourteen volts back. That's its maximum, but the door is still just closed. Two volts in: it would need twenty volts, but it can only give fourteen. The door opens, and the minus input moves away from zero.", s_opamp),
 ("So remember. Plus equals minus is not automatic. The op amp makes it true by pushing back with its output. When the output hits the supply limit, it can't push any harder, so the inputs separate. That's saturation.", s_end),
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
            for p in (0.3, 0.6, 0.97):
                fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}_{int(p*100)}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
