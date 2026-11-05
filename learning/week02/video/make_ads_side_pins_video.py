"""Narrated video: the ADS1299's right-hand and bottom pins on the Cyton schematic.
Digital power + grounds, CLKSEL/CLK, the SPI pins and DRDY, the control pins (RESET, PWDN, START, DAISY_IN, GPIOs),
the 4.5 V reference (VREFP/VREFN with C1 + C5), and the VCAP1/2/4 capacitors (C2, C7, C6).
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_ads_side_pins_video.py -> ads1299_side_pins.mp4
Preview frames: python make_ads_side_pins_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ads1299_side_pins.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
C = {"pow": "#5aa9ff", "clk": "#ffd166", "spi": "#2ec4a0", "ctrl": "#ff8a5c", "ref": "#a77bff", "vcap": "#ffb347", "srb": "#f28fb0", "unused": "#8a97ab"}
RNG = np.random.default_rng(11); NOISE = RNG.normal(0, 1, 6000)

# right-hand pins, top to bottom: (number, name, group, destination)
RIGHT = [(52, "CLKSEL", "clk", "dvdd"), (49, "DGND", "pow", "gnd"), (50, "DVDD", "pow", "dvdd"), (32, "AVSS", "pow", "avss"),
         (51, "DGND", "pow", "gnd"), (48, "DVDD", "pow", "dvdd"), (47, "/DRDY", "spi", "DRDY"), (46, "GPIO_4", "unused", "x"),
         (43, "DOUT", "spi", "MISO"), (44, "GPIO_2", "unused", "x"), (45, "GPIO_3", "unused", "x"), (40, "SCLK", "spi", "SCLK"),
         (39, "/CS", "spi", "CS1"), (37, "CLK", "clk", "CLK"), (38, "START", "ctrl", "x"), (34, "D_IN", "spi", "MOSI"), (33, "DGND", "pow", "gnd")]
RY = lambda i: 7.85 - i * 0.355
# bottom pins, left to right
BOTTOM = [(18, "SRB2", "srb"), (17, "SRB1", "srb"), (26, "VCAP4", "vcap"), (24, "VREFP", "ref"), (29, "NC", "unused"), (25, "VREFN", "ref"),
          (27, "NC", "unused"), (35, "/PWDN", "ctrl"), (28, "VCAP1", "vcap"), (42, "GPIO_1", "unused"), (41, "DAISY_IN", "ctrl"),
          (30, "VCAP2", "vcap"), (36, "/RESET", "ctrl")]
BX = lambda i: 1.0 + i * 0.9


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
def title(ax, s): ax.text(0.4, 8.5, s, color=FG, fontsize=24, weight="bold", va="center")
def ground(ax, x, y, c=FG):
    for i, w in enumerate((0.22, 0.14, 0.06)): ax.plot([x - w, x + w], [y - i * 0.08] * 2, color=c, lw=1.7)
def xmark(ax, x, y, c=MU):
    ax.plot([x - 0.08, x + 0.08], [y - 0.08, y + 0.08], color=c, lw=1.6); ax.plot([x - 0.08, x + 0.08], [y + 0.08, y - 0.08], color=c, lw=1.6)
def cap_h(ax, x, y, c=FG):
    ax.plot([x - 0.2, x + 0.2], [y + 0.06] * 2, color=c, lw=2.6); ax.plot([x - 0.2, x + 0.2], [y - 0.06] * 2, color=c, lw=2.6)
def cap_v(ax, x, y, c=FG):
    ax.plot([x - 0.06] * 2, [y - 0.18, y + 0.18], color=c, lw=2.6); ax.plot([x + 0.06] * 2, [y - 0.18, y + 0.18], color=c, lw=2.6)
def note(ax, lines, p=1.0, x=0.35, y=7.6, step=0.12, dy=0.5, w=3.75):
    ax.add_patch(FancyBboxPatch((x - 0.1, y - dy * len(lines) - 0.05), w, dy * len(lines) + 0.4, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
    for i, (s, c) in enumerate(lines):
        if p >= i * step: ax.text(x + 0.05, y - i * dy, s, color=c, fontsize=12.5, va="top")
def dots(ax, pts, prog, c, n=5):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; L = sum(seg)
    for k in range(n):
        d = ((k / n + prog) % 1) * L; acc = 0
        for (a, b), s in zip(zip(pts, pts[1:]), seg):
            if d <= acc + s:
                tt = (d - acc) / s if s else 0
                ax.plot(a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt, "o", ms=6, color=c, zorder=6); break
            acc += s


def right_view(ax, hi=(), t=0.0, flowing=()):
    col = lambda g: C[g] if g in hi else FG
    ax.add_patch(Rectangle((4.3, 1.75), 2.2, 6.4, fc=PANEL, ec=FG, lw=1.8, zorder=2))
    ax.text(5.0, 1.95, "U6", color=MU, fontsize=11)
    ys = {}
    for i, (num, name, g, dest) in enumerate(RIGHT):
        y = RY(i); ys[name + str(num)] = y; c = col(g)
        ax.text(6.4, y, name, color=c, fontsize=10.5, ha="right", va="center", zorder=3)
        ax.text(6.6, y + 0.12, str(num), color=MU, fontsize=9)
        if dest == "x": ax.plot([6.5, 7.1], [y, y], color=c, lw=1.6); xmark(ax, 7.15, y, c)
        elif dest in ("dvdd", "gnd", "avss"):
            xr = {"dvdd": 9.6, "gnd": 9.0, "avss": 8.4}[dest]
            ax.plot([6.5, xr], [y, y], color=c, lw=1.6); ax.plot(xr, y, "o", color=c, ms=4)
        else:
            ax.plot([6.5, 10.6], [y, y], color=c, lw=1.6)
            ax.annotate("", xy=(10.75, y), xytext=(10.5, y), arrowprops=dict(arrowstyle="->", color=c, lw=1.6))
            ax.text(10.85, y, dest, color=c, fontsize=11.5, va="center")
            if dest in flowing: dots(ax, [(6.5, y), (10.6, y)] if dest != "CS1" and dest != "SCLK" and dest != "MOSI" else [(10.6, y), (6.5, y)], t * 0.6, c)
    # rails
    cd = C["pow"] if "pow" in hi or "clk" in hi else FG
    ax.plot([9.6, 9.6], [ys["DVDD48"], 8.25], color=cd, lw=1.8); ax.plot([9.4, 9.8], [8.25, 8.25], color=cd, lw=2.2); ax.text(9.6, 8.38, "DVDD 3.3 V", color=cd, fontsize=11, ha="center")
    cg = C["pow"] if "pow" in hi else FG
    ax.plot([9.0, 9.0], [ys["DGND49"], 1.75], color=cg, lw=1.8); ground(ax, 9.0, 1.75, cg); ax.text(9.0, 1.42, "AGND", color=cg, fontsize=10.5, ha="center")
    ax.plot([8.4, 8.4], [ys["AVSS32"], 8.25], color=cg, lw=1.8); ax.text(8.4, 8.38, "AVSS", color=cg, fontsize=11, ha="center")


def bottom_view(ax, hi=(), t=0.0, ref_glow=False):
    col = lambda g: C[g] if g in hi else FG
    ax.add_patch(Rectangle((0.6, 7.0), 11.8, 0.95, fc=PANEL, ec=FG, lw=1.8, zorder=2)); ax.text(0.75, 7.75, "U6 · ADS1299", color=MU, fontsize=11)
    for i, (num, name, g) in enumerate(BOTTOM):
        x = BX(i); c = col(g)
        ax.text(x, 7.42, name, color=c, fontsize=9.5, ha="center", va="center", rotation=90, zorder=3)
        ax.text(x + 0.1, 6.7, str(num), color=MU, fontsize=9)
        ax.plot([x, x], [7.0, 6.6], color=c, lw=1.6)
    cs = col("srb")
    ax.plot([BX(0), BX(0), 0.3], [6.6, 6.25, 6.25], color=cs, lw=1.6); ax.plot([BX(1), BX(1), 0.3], [6.6, 5.85, 5.85], color=cs, lw=1.6)
    ax.text(0.3, 5.55, "SRB2, SRB1\n→ protection\n→ header", color=cs, fontsize=10, va="top")
    cr = col("ref")
    ax.plot([BX(3), BX(3)], [6.6, 4.5], color=cr, lw=1.6); ax.plot([BX(5), BX(5)], [6.6, 2.4], color=cr, lw=1.6)
    for y, nm in ((5.3, "C1 10 µF"), (4.5, "C5 0.1 µF")):
        ax.plot([BX(3), 4.48], [y, y], color=cr, lw=1.6); cap_v(ax, 4.6, y, cr); ax.plot([4.72, BX(5)], [y, y], color=cr, lw=1.6)
        ax.text(4.6, y - 0.42, nm, color=cr, fontsize=10, ha="center")
    for i in (4, 6): ax.text(BX(i), 6.35, "NC", color=MU, fontsize=9.5, ha="center")
    cc = col("ctrl")
    ax.plot([BX(7), BX(7), 12.3, 12.3], [6.6, 2.95, 2.95, 3.55], color=cc, lw=1.6); ax.plot([12.1, 12.5], [3.55, 3.55], color=cc, lw=2.2)
    ax.text(12.3, 3.7, "DVDD", color=cc, fontsize=10.5, ha="center"); ax.text(9.55, 3.08, "POWER DOWN", color=cc, fontsize=9.5, ha="center")
    ax.plot([BX(10), BX(10)], [6.6, 4.4], color=cc, lw=1.6); ground(ax, BX(10), 4.4, cc); ax.text(BX(10), 3.95, "AGND", color=cc, fontsize=9.5, ha="center")
    ax.plot([BX(12), BX(12), 12.4], [6.6, 5.8, 5.8], color=cc, lw=1.6)
    ax.annotate("", xy=(12.55, 5.8), xytext=(12.3, 5.8), arrowprops=dict(arrowstyle="->", color=cc, lw=1.6)); ax.text(12.1, 6.0, "RESET", color=cc, fontsize=9.5)
    xmark(ax, BX(9), 6.55, col("unused"))
    cv = col("vcap")
    for i, nm in ((2, "C6 1 µF"), (8, "C2 100 µF"), (11, "C7 1 µF")):
        x = BX(i); ax.plot([x, x], [6.6, 3.62], color=cv, lw=1.6); cap_h(ax, x, 3.55, cv); ax.plot([x, x], [3.48, 2.4], color=cv, lw=1.6)
        ax.text(x + 0.22, 3.85, nm, color=cv, fontsize=10)
    ca = col("vcap") if "vcap" in hi else (col("ref") if "ref" in hi else FG)
    ax.plot([BX(2), BX(11)], [2.4, 2.4], color=ca, lw=1.8); ax.plot([6.85, 6.85], [2.4, 2.15], color=ca, lw=1.8)
    ax.plot([6.65, 7.05], [2.15, 2.15], color=ca, lw=2.2); ax.text(6.85, 1.85, "AVSS", color=ca, fontsize=10.5, ha="center")


# ---- scenes ----
def s_title(ax, p, t):
    ax.text(0.4, 8.5, "ADS1299: side and bottom pins", color=FG, fontsize=24, weight="bold", va="center")
    right_view(ax)
    note(ax, [("power and grounds", C["pow"]), ("clock", C["clk"]), ("SPI and DRDY", C["spi"]), ("control pins", C["ctrl"]),
              ("reference", C["ref"]), ("VCAP capacitors", C["vcap"])], p, x=11.9, y=7.3, w=3.8)

def s_power(ax, p, t):
    title(ax, "Digital power and grounds")
    right_view(ax, hi=("pow",))
    note(ax, [("2 × DVDD → 3.3 V digital", C["pow"]), ("3 × DGND → AGND", C["pow"]), ("one ground for the chip", FG), ("pin 32: one more AVSS", C["pow"])], p)

def s_clock(ax, p, t):
    title(ax, "CLKSEL and CLK")
    right_view(ax, hi=("clk",), t=t, flowing=("CLK",))
    note(ax, [("CLKSEL = DVDD (high)", C["clk"]), ("→ use the internal", FG), ("   2.048 MHz oscillator", FG), ("CLK pin outputs that beat", C["clk"]),
              ("→ Daisy board's 2nd chip", FG), ("   stays in step", FG)], p, step=0.1)

def s_spi(ax, p, t):
    title(ax, "The SPI pins and the doorbell")
    right_view(ax, hi=("spi",), t=t, flowing=("CS1", "SCLK", "MOSI", "MISO", "DRDY"))
    note(ax, [("/CS ← CS1: \"talk to me\"", C["spi"]), ("SCLK ← the clapping", C["spi"]), ("D_IN ← MOSI: commands", C["spi"]),
              ("DOUT → MISO: data", C["spi"]), ("/DRDY → \"sample ready\"", C["spi"])], p, step=0.13)

def s_ctrl(ax, p, t):
    title(ax, "Control and spare pins")
    if p < 0.55:
        right_view(ax, hi=("ctrl", "unused"))
        note(ax, [("\"/\" = acts when LOW", FG), ("START: not connected,", C["ctrl"]), ("   PIC32 sends the START", FG),
                  ("   command over SPI", FG), ("GPIO 2–4: unused (X)", C["unused"])], p / 0.55, step=0.15)
    else:
        bottom_view(ax, hi=("ctrl", "unused"))
        q = (p - 0.55) / 0.45
        note(ax, [("/RESET ← MCU: restart", C["ctrl"]), ("/PWDN → DVDD: always on", C["ctrl"]), ("DAISY_IN → ground:", C["ctrl"]),
                  ("   no chip feeds this one", FG), ("GPIO_1, NC: unused", C["unused"])], q, x=12.75, y=6.6, step=0.15, w=3.15)

def s_ref(ax, p, t):
    title(ax, "The reference: the 4.5 V ruler")
    bottom_view(ax, hi=("ref",))
    note(ax, [("VREFN = AVSS = −2.5 V", C["ref"]), ("VREFP = −2.5 + 4.5", C["ref"]), ("      = +2.0 V", C["ref"]),
              ("C1 10 µF + C5 0.1 µF", FG), ("keep the ruler steady", FG)], p, x=12.75, y=6.6, step=0.12, w=3.15)
    ax.add_patch(FancyBboxPatch((12.65, 1.75), 3.25, 1.5, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1))
    ax.text(12.75, 3.05, "ruler voltage", color=MU, fontsize=10.5, va="center")
    k = int(t * 30) % 5000; n = NOISE[k:k + 200]; xs = np.linspace(0, 1, 200)
    smooth = p > 0.55
    v = np.convolve(n, np.ones(30) / 30, mode="same") * 0.15 if smooth else n * 0.25
    ax.plot(12.8 + xs * 3.0, 2.35 + v, color=C["spi"] if smooth else "#ef5b5b", lw=1.4)
    ax.text(14.3, 1.85, "steady: with C1, C5" if smooth else "wobbles: no capacitors", color=C["spi"] if smooth else "#ef5b5b", fontsize=10.5, ha="center")

def s_vcap(ax, p, t):
    title(ax, "VCAP1, VCAP2, VCAP4")
    bottom_view(ax, hi=("vcap",))
    note(ax, [("internal circuits that need", FG), ("an outside reservoir", FG), ("VCAP1 → C2 100 µF", C["vcap"]), ("VCAP2 → C7 1 µF", C["vcap"]),
              ("VCAP4 → C6 1 µF", C["vcap"]), ("all to AVSS", C["vcap"]), ("(VCAP3: C19 + C15)", MU)], p, x=12.75, y=6.6, step=0.1, w=3.15)

def s_srb(ax, p, t):
    title(ax, "SRB1 and SRB2")
    bottom_view(ax, hi=("srb",))
    note(ax, [("the shared reference pins", C["srb"]), ("→ protection block", FG), ("→ header (ear clip)", FG), ("joined to channels inside", FG),
              ("the chip by software", FG)], p, x=12.75, y=6.6, step=0.13, w=3.15)

def s_end(ax, p, t):
    ax.text(8, 7.7, "For your BrainTech-8 schematic", color=FG, fontsize=28, ha="center", weight="bold")
    rows = [("ESP32 ↔ ADS1299:", "CS · SCLK · MOSI → D_IN · DOUT → MISO · DRDY · RESET", C["spi"]),
            ("Clock:", "CLKSEL high → internal oscillator", C["clk"]),
            ("Tie off:", "PWDN high (or to a GPIO to save power), DAISY_IN low, unused GPIOs", C["ctrl"]),
            ("Reference:", "VREFP–VREFN 10 µF ‖ 0.1 µF, VREFN to AVSS", C["ref"]),
            ("VCAPs:", "VCAP1 100 µF · VCAP2 1 µF · VCAP3 1 µF ‖ 0.1 µF · VCAP4 1 µF → AVSS", C["vcap"])]
    for i, (a, b, c) in enumerate(rows):
        if p > 0.06 + i * 0.13:
            y = 6.5 - i * 0.95
            ax.text(1.0, y, a, color=c, fontsize=17, weight="bold", va="center"); ax.text(4.6, y, b, color=FG, fontsize=15, va="center")


SCENES = [
 ("This part of the Cyton schematic shows the rest of the A D S twelve ninety nine's pins: its digital power, its clock, the S P I and control pins, its reference, and its V CAP capacitors.", s_title),
 ("Two D V D D pins take the three point three volt digital supply. Three D G N D pins, the digital grounds, all join analog ground: the Cyton uses one ground for the whole chip. Pin thirty two is one more A V S S pin.", s_power),
 ("Clock select is tied to D V D D. High means: use the internal oscillator, the two megahertz metronome inside the chip. The clock pin then outputs that beat on the net called clock, so a second A D S twelve ninety nine, on the Daisy board, can share it and stay in step.", s_clock),
 ("These are the S P I pins you know. Chip select comes from the PIC thirty two's C S one. S clock is the clapping. D in receives commands on MOSI. D out sends data back on MISO. And data ready is the doorbell that rings for every new sample.", s_spi),
 ("A slash in a pin name means it acts when pulled low. Start isn't connected: the PIC thirty two sends the start command over S P I instead. G P I O two, three and four are unused. On the bottom row, reset comes from the microcontroller, so it can restart the chip. Power down is tied to D V D D, so the chip never sleeps. Daisy in is tied to ground, because no other chip feeds data into this one. G P I O one and the N C pins are unused.", s_ctrl),
 ("V REF P and V REF N are the two ends of the four point five volt ruler that every measurement is compared against. V REF N is tied to A V S S, minus two point five volts, so V REF P sits at plus two volts. C one, ten microfarads, and C five, point one microfarads, keep the ruler perfectly steady.", s_ref),
 ("V CAP one, two and four, like V CAP three, connect to circuits inside the chip that need an outside reservoir. V CAP one gets the big one: C two, one hundred microfarads. V CAP two and V CAP four each get one microfarad. All of them go to A V S S, exactly as the datasheet asks.", s_vcap),
 ("Finally, S R B one and S R B two, the shared reference pins, head out through the protection block to the header, where the ear clip connects. The chip joins them to the channels inside, by software.", s_srb),
 ("For your own board: wire chip select, S clock, MOSI, MISO, data ready and reset to the E S P thirty two. Tie clock select high for the internal clock. Tie off power down, daisy in and the unused pins. And copy every reference and V CAP capacitor.", s_end),
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
            for q in ((0.3, 0.85) if i == 4 else (0.85,)):
                fig, ax = new_fig(); draw(ax, q, 3.3); caption(ax, text, q)
                fig.savefig(os.path.join(d, f"sp{i}_{int(q * 100)}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
