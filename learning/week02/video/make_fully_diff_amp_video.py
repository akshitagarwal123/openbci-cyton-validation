"""45 s silent animation: how a fully differential amplifier works inside an EEG chip (ADS1299-style).
Scene 1: ±2.5 V rails, two inputs (+0.5 V / -0.5 V). Scene 2: ×4 amplifier, outputs ±2.0 V inside the rails.
Scene 3: bracket OUTP - OUTN = 4.0 V, ADC meter at 89% of 4.5 V. Scene 4: sine input, mirror-image outputs.
Needs: matplotlib, numpy, ffmpeg.  Usage: python make_fully_diff_amp_video.py  ->  fully_differential_amp.mp4
Preview frames: python make_fully_diff_amp_video.py --stills DIR"""
import math, os, subprocess, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

FPS, W, H, DUR = 30, 1280, 720, 45.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fully_differential_amp.mp4")
BG, FG, MU = "#0b1730", "#eef2f7", "#8a97ab"
RED, BLUE, GREEN, PURPLE, CHECK = "#ef5b5b", "#4ea3ff", "#3ddc84", "#a77bff", "#3ddc84"
GAIN, FS = 4.0, 4.5


def Y(v): return 4.5 + 1.2 * v                      # volts -> drawing height
def ease(x): x = min(1, max(0, x)); return 0.5 - 0.5 * math.cos(math.pi * x)
def ramp(t, a, b): return ease((t - a) / (b - a))


def diff_in(t):
    """Input difference P - N in volts at time t."""
    if t < 32: return 1.0
    amp = 1.0 + 0.125 * ramp(t, 32, 36)               # grows to 1.125 V so outputs reach ±2.25 V
    return amp * math.cos(2 * math.pi * 0.4 * (t - 32))


def wire(ax, xs, ys, c, a=1.0):
    ax.plot(xs, ys, color=c, lw=9, alpha=0.18 * a, solid_capstyle="round")   # glow
    ax.plot(xs, ys, color=c, lw=3, alpha=a, solid_capstyle="round")


def frame(t):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off"); ax.set_facecolor(BG)

    # --- Scene 1: rails and inputs ---
    a = ramp(t, 0, 1.5)
    for v, lab in ((2.5, "+2.5 V"), (-2.5, "−2.5 V")):
        ax.plot([0.8, 12.2], [Y(v)] * 2, color=RED, ls="--", lw=2, alpha=a)
        ax.text(0.8, Y(v) + (0.18 if v > 0 else -0.45), lab, color=RED, fontsize=17, alpha=a)
    ax.plot([0.8, 12.2], [Y(0)] * 2, color=MU, ls=":", lw=1.5, alpha=a)
    ax.text(0.8, Y(0) + 0.15, "0 V", color=MU, fontsize=15, alpha=a)

    d = diff_in(t); inp, inn = d / 2, -d / 2
    wa = ramp(t, 2, 3.5)
    x_end = 4.0 + 0.9 * ramp(t, 8, 10)               # wires extend into the amplifier in scene 2
    wire(ax, [1.6, x_end], [Y(inp)] * 2, BLUE, wa); wire(ax, [1.6, x_end], [Y(inn)] * 2, GREEN, wa)
    m = lambda v: f"{v:+.2f}".replace("-", "−")
    for v, name, c, other in ((inp, "INP", BLUE, inn), (inn, "INN", GREEN, inp)):
        up = v >= other                                      # higher wire gets its label above, lower one below
        ax.text(1.6, Y(v) + (0.3 if up else -0.55), f"{name} {m(v)} V" if t >= 32 else f"{name} {'+0.5' if name == 'INP' else '−0.5'} V",
                color=c, fontsize=17, alpha=wa)

    # --- Scene 2: amplifier and outputs ---
    ta = ramp(t, 8, 9.2)
    if ta > 0:
        ax.add_patch(Polygon([[4.9, 6.6], [4.9, 2.4], [7.3, 4.5]], closed=True, fc=BG, ec=FG, lw=2.5, alpha=ta, zorder=3))
        ax.text(5.75, 4.5, "×4", color=FG, fontsize=24, ha="center", va="center", weight="bold", alpha=ta, zorder=4)
    g = ramp(t, 10, 15)                              # output grows from 0 to its value
    outp, outn = GAIN * inp * (g if t < 32 else 1), GAIN * inn * (g if t < 32 else 1)
    if g > 0:
        for v, c in ((outp, BLUE), (outn, GREEN)):
            xs = np.linspace(7.3, 11.0, 80); s = np.clip((xs - 7.3) / 1.6, 0, 1); s = 0.5 - 0.5 * np.cos(np.pi * s)
            wire(ax, xs, Y(0) + (Y(v) - Y(0)) * s, c, min(1, g * 3))
        ck = ramp(t, 15, 16.2)
        ax.text(11.15, Y(outp) - 0.05, f"{outp:+.2f} V".replace("-", "−"), color=BLUE, fontsize=16, va="center", alpha=min(1, g * 3))
        ax.text(11.15, Y(outn) - 0.05, f"{outn:+.2f} V".replace("-", "−"), color=GREEN, fontsize=16, va="center", alpha=min(1, g * 3))
        if ck > 0 and t < 20:
            for v in (outp, outn): ax.text(12.45, Y(v) - 0.05, "✓", color=CHECK, fontsize=24, va="center", alpha=ck)

    # --- Scene 3: bracket and ADC meter ---
    ba = ramp(t, 20, 23)
    if ba > 0:
        xb = 12.5; top, bot = Y(outp), Y(outn); mid = (top + bot) / 2; half = (top - bot) / 2 * ba
        ax.plot([xb, xb], [mid - half, mid + half], color=FG, lw=2, alpha=ba)
        for yy in (mid - half, mid + half): ax.plot([xb - 0.15, xb + 0.15], [yy, yy], color=FG, lw=2, alpha=ba)
        ax.text(10.8, 8.35, f"OUTP − OUTN = {outp - outn:.1f} V".replace("= -", "= −"), color=FG, fontsize=17, ha="center", alpha=ramp(t, 22, 23.5))
    ma = ramp(t, 23.5, 24.5)
    if ma > 0:
        mx, mw = 14.4, 0.8
        ax.add_patch(Rectangle((mx, Y(-2.5)), mw, Y(2.5) - Y(-2.5), fc="none", ec=FG, lw=2, alpha=ma))
        ax.plot([mx - 0.1, mx + mw + 0.1], [Y(0)] * 2, color=MU, lw=1, alpha=ma)
        frac = (outp - outn) / FS * (ramp(t, 24.5, 29) if t < 32 else 1)
        hgt = frac * (Y(2.5) - Y(0))
        ax.add_patch(Rectangle((mx + 0.05, Y(0) if hgt >= 0 else Y(0) + hgt), mw - 0.1, abs(hgt), fc=PURPLE, alpha=0.9 * ma))
        ax.text(mx + mw / 2, Y(2.5) + 0.25, "+4.5 V", color=MU, fontsize=12, ha="center", alpha=ma)
        ax.text(mx + mw / 2, Y(-2.5) - 0.45, "−4.5 V", color=MU, fontsize=12, ha="center", alpha=ma)
        ax.text(mx + mw / 2, 8.45, "ADC", color=PURPLE, fontsize=15, ha="center", alpha=ma)
        ax.text(mx + mw / 2, 8.05, "full scale 4.5 V", color=PURPLE, fontsize=12, ha="center", alpha=ma)
        ax.text(mx - 0.15, Y(0) + hgt, f"{abs(frac) * 100:.0f}%", color=PURPLE, fontsize=15, ha="right", va="center", alpha=ma)

    # --- captions ---
    caps = [(4, 8, "Input difference = 1 V"), (15.5, 20, "Each wire stays inside ±2.5 V"),
            (24.5, 32, "The ADC measures the difference between the two wires"), (35, 45.1, "Two wires × ±2.25 V = ±4.5 V for the ADC")]
    for a0, a1, s in caps:
        ca = min(ramp(t, a0, a0 + 0.8), 1 - ramp(t, a1 - 0.6, a1))
        if ca > 0: ax.text(8, 0.35, s, color=FG, fontsize=22, ha="center", alpha=ca,
                           bbox=dict(boxstyle="round,pad=0.45", fc="#14254a", ec="none", alpha=ca))
    return fig


def main():
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", OUT], stdin=subprocess.PIPE)
    for k in range(int(DUR * FPS)):
        fig = frame(k / FPS); fig.canvas.draw(); ff.stdin.write(fig.canvas.buffer_rgba().tobytes()); plt.close(fig)
    ff.stdin.close(); ff.wait(); print("saved", OUT)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stills":
        d = sys.argv[2] if len(sys.argv) > 2 else "."
        for t in (6, 17, 30, 38, 41):
            fig = frame(t); fig.savefig(os.path.join(d, f"fda_{t:02d}s.png"), facecolor=BG); plt.close(fig)
    else:
        main()
