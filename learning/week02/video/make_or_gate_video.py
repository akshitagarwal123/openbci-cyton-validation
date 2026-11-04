"""Narrated video: why the Cyton puts an OR gate (U2) in front of the LIS3DH accelerometer's data pin.
Shared SPI bus -> I2C and its START signal -> the accelerometer's SPI/I2C dual mode -> the false-START problem
-> what an OR gate does -> the fix (CS4 high: pin held high; CS4 low: pin copies MOSI) -> tip for BrainTech-8.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_or_gate_video.py -> accelerometer_or_gate.mp4
Preview frames: python make_or_gate_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, PathPatch
from matplotlib.path import Path

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accelerometer_or_gate.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
CLK, DAT, CSC, OK, BAD, YEL, PUR = "#5aa9ff", "#c7cdd6", "#ff8a5c", "#2ec4a0", "#ef5b5b", "#ffd166", "#a77bff"

# one shared SPI conversation (16 clock periods); MOSI deliberately changes while SCLK is high at a few points
SCLK = [v for _ in range(16) for v in (0, 1)]
BITS = "1011001110100110"
MOSI = [int(b) for b in BITS for _ in range(2)]
for i in (3, 9, 13): MOSI[2 * i], MOSI[2 * i + 1] = 1, 0          # falls during the high half of the clock
FAKE = [k for k in range(1, 32) if SCLK[k] == 1 and MOSI[k - 1] == 1 and MOSI[k] == 0]


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
def box(ax, x, y, w, h, t1, t2="", ec=FG, fc=PANEL, c1=FG):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec=ec, lw=2, zorder=3))
    ax.text(x + w / 2, y + h / 2 + (0.18 if t2 else 0), t1, color=c1, fontsize=15, ha="center", va="center", weight="bold", zorder=4)
    if t2: ax.text(x + w / 2, y + h / 2 - 0.25, t2, color=MU, fontsize=12, ha="center", va="center", zorder=4)
def wave(ax, vals, y, x0, x1, c, upto=1.0, lw=2.2, amp=0.55, label=None, sub=None):
    n = len(vals); xs, ys = [], []
    for i, v in enumerate(vals):
        a, b = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
        if a > x0 + (x1 - x0) * upto: break
        b = min(b, x0 + (x1 - x0) * upto)
        xs += [a, b]; ys += [y + v * amp, y + v * amp]
    if xs: ax.plot(xs, ys, color=c, lw=lw, zorder=3)
    if label: ax.text(x0 - 0.25, y + amp / 2 + 0.08, label, color=c, fontsize=13, ha="right", va="center", weight="bold")
    if sub: ax.text(x0 - 0.25, y + amp / 2 - 0.3, sub, color=MU, fontsize=10.5, ha="right", va="center")
def xk(k, x0=3.2, x1=15.4): return x0 + (x1 - x0) * k / 32


# ---- bus picture (scene 1) ----
def bus(ax, sel="ads", t=0.0):
    box(ax, 0.4, 3.6, 2.2, 2.8, "PIC32", "the boss")
    for y, nm, c in ((6.0, "SCLK", CLK), (5.3, "MOSI", DAT), (4.6, "MISO", DAT)):
        ax.plot([2.6, 15.2], [y, y], color=c, lw=2.4, zorder=2); ax.text(15.3, y, nm, color=c, fontsize=12, va="center")
    chips = [("ads", 3.6, "ADS1299"), ("acc", 7.9, "Accelerometer"), ("sd", 12.0, "SD card")]
    for key, x, name in chips:
        on = key == sel
        for i, y in enumerate((6.0, 5.3, 4.6)):
            xx = x + 0.6 + i * 0.5; ax.plot([xx, xx], [y, 3.3], color=CLK if i == 0 else DAT, lw=1.6, alpha=1 if on else 0.45, zorder=2)
            ax.plot(xx, y, "o", color=CLK if i == 0 else DAT, ms=5)
        box(ax, x, 1.75, 2.6, 1.55, name, ec=OK if on else DIM, c1=FG if on else MU)
        ax.text(x + 1.3, 2.05, f"CS {'LOW: selected' if on else 'high: ignore'}", color=OK if on else MU, fontsize=11.5, ha="center", zorder=4)


# ---- scenes ----
def s_title(ax, p, t):
    ax.text(8, 6.7, "Why is there an OR gate", color=FG, fontsize=34, ha="center", weight="bold")
    ax.text(8, 5.9, "in front of the accelerometer?", color=FG, fontsize=34, ha="center", weight="bold")
    ax.text(8, 4.8, "U2 · SN74LVC1G32  +  U1 · LIS3DH  on the OpenBCI Cyton", color=MU, fontsize=17, ha="center")
    if p > 0.5: ax.text(8, 3.6, "two ideas:  I²C   and   the OR gate", color=YEL, fontsize=20, ha="center")

def s_bus(ax, p, t):
    title(ax, "Recap: the shared SPI bus")
    bus(ax, sel=["ads", "acc", "sd"][int(ramp(p, 0.35, 0.95) * 2.99)])

def s_i2c(ax, p, t):
    title(ax, "I²C: two wires, no chip select")
    x0, x1 = 3.0, 13.0
    scl = [1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1]
    sda = [1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
    up = ramp(p, 0.15, 0.85)
    wave(ax, scl, 6.3, x0, x1, CLK, up, label="SCL", sub="clock")
    wave(ax, sda, 4.9, x0, x1, OK, up, label="SDA", sub="data, both ways")
    if up > 0.12:
        xs = x0 + (x1 - x0) * 2 / 20
        ax.add_patch(Rectangle((xs - 0.35, 4.6), 0.7, 2.5, fc=BAD, alpha=0.18, zorder=1))
        ax.text(xs, 7.35, "START", color=BAD, fontsize=16, ha="center", weight="bold")
        ax.text(xs + 0.5, 4.35, "data falls while the clock is HIGH  =  \"attention, everyone!\"", color=BAD, fontsize=13)
    if p > 0.6:
        ax.text(x0 + 3.0, 3.65, "then an address: \"chip 0x19, this is for you\"", color=YEL, fontsize=14)
    for i, (nm, adr) in enumerate((("accel", "0x19"), ("chip", "0x48"), ("chip", "0x50"))):
        lit = p > 0.75 and i == 0
        box(ax, 3.0 + i * 3.6, 1.65, 2.6, 1.15, f"{nm} {adr}", ec=OK if lit else DIM, c1=OK if lit else MU)

def s_dual(ax, p, t):
    title(ax, "The accelerometer speaks both")
    i2c = p > 0.5
    box(ax, 5.5, 2.4, 5.0, 4.4, "LIS3DH", "accelerometer", ec=YEL if i2c else OK)
    for y, nm in ((6.0, "SCK / SCL"), (5.0, "SDI / SDA"), (4.0, "SDO"), (3.0, "CS")):
        ax.plot([4.2, 5.45], [y, y], color=FG, lw=2); ax.text(4.1, y, nm, color=FG, fontsize=14, ha="right", va="center")
    ax.text(12.6, 6.2, "CS = " + ("HIGH" if i2c else "LOW"), color=CSC, fontsize=22, ha="center", weight="bold")
    ax.text(12.6, 5.3, "I²C mode" if i2c else "SPI mode", color=YEL if i2c else OK, fontsize=22, ha="center", weight="bold")
    ax.text(12.6, 4.5, "listening for a START…" if i2c else "selected: talks SPI", color=FG, fontsize=15, ha="center")
    ax.text(8.0, 7.3, "same pins, two languages", color=MU, fontsize=15, ha="center")

def waves_scene(ax, p, t, gate, cs4, corrupt):
    up = ramp(p, 0.05, 0.92); cur = xk(32 * up)
    mos = list(MOSI)
    hits = [k for k in FAKE if k <= 32 * up] if (cs4 and not gate) else []
    if corrupt and hits:
        k0 = hits[0] + 2
        for k in range(k0, min(32, k0 + 4)): mos[k] = 0
    y = [(1 if cs4 else m) if gate else m for m in mos]
    wave(ax, SCLK, 6.6, 3.2, 15.4, CLK, up, label="SCLK", sub="shared clock")
    wave(ax, mos, 5.4, 3.2, 15.4, DAT, up, label="MOSI", sub="shared data")
    wave(ax, [cs4] * 32, 4.2, 3.2, 15.4, CSC, up, label="CS4", sub="accel select")
    wave(ax, y, 3.0, 3.2, 15.4, OK if gate else PUR, up, label="accel pin", sub="what it hears")
    ax.plot([cur, cur], [2.8, 7.4], color=YEL, lw=1, alpha=0.6)
    for k in hits:
        ax.plot([xk(k)] * 2, [2.85, 7.3], color=BAD, lw=1.5, ls="--")
        ax.text(xk(k), 7.55, "START?!", color=BAD, fontsize=12, ha="center", weight="bold")
    if corrupt and hits:
        k0 = hits[0] + 2
        if 32 * up > k0:
            ax.add_patch(Rectangle((xk(k0), 5.3), xk(min(32, k0 + 4)) - xk(k0), 0.75, fc=BAD, alpha=0.25))
            ax.text(xk(k0 + 2), 4.95, "accel pulls MOSI low: ADS1299 gets a wrong bit", color=BAD, fontsize=12, ha="center")
    return hits

def s_problem(ax, p, t):
    title(ax, "The problem: talking to the ADS1299")
    hits = waves_scene(ax, p, t, gate=False, cs4=1, corrupt=True)
    ax.text(0.4, 7.75, "accelerometer:  " + ("woke up!" if hits else "not selected, listening for I²C"), color=BAD if hits else MU, fontsize=15)

def or_gate(ax, x, y, s=1.0, ec=PUR):
    verts = [(x, y + 0.9 * s), (x + 0.9 * s, y + 0.9 * s), (x + 1.7 * s, y + 0.45 * s), (x + 1.7 * s, y + 0.45 * s), (x + 0.9 * s, y), (x, y),
             (x + 0.35 * s, y + 0.45 * s), (x, y + 0.9 * s)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CURVE3, Path.CURVE3]
    verts = [(x, y + 0.9 * s), (x + 0.8 * s, y + 0.9 * s), (x + 1.4 * s, y + 0.85 * s), (x + 1.8 * s, y + 0.45 * s),
             (x + 1.4 * s, y + 0.05 * s), (x + 0.8 * s, y), (x, y), (x + 0.35 * s, y + 0.45 * s), (x, y + 0.9 * s)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CURVE3, Path.CURVE3]
    ax.add_patch(PathPatch(Path(verts, codes), fc=PANEL, ec=ec, lw=2.5, zorder=3))

def s_orgate(ax, p, t):
    title(ax, "The OR gate")
    combos = [(0, 0), (0, 1), (1, 0), (1, 1)]
    k = min(3, int(ramp(p, 0.1, 0.9) * 3.99)); a, b = combos[k]; yv = a | b
    or_gate(ax, 3.0, 3.6, s=2.2)
    for yy, v, nm in ((5.1, a, "A"), (4.2, b, "B")):
        ax.plot([1.6, 3.6], [yy, yy], color=OK if v else DIM, lw=3); ax.text(1.4, yy, f"{nm} = {v}", color=OK if v else MU, fontsize=18, ha="right", va="center", weight="bold")
    ax.plot([6.95, 8.2], [4.6, 4.6], color=OK if yv else DIM, lw=3)
    ax.add_patch(Circle((8.7, 4.6), 0.45, fc=YEL if yv else PANEL, ec=FG, lw=2, zorder=3))
    ax.text(8.7, 3.8, f"Y = {yv}", color=OK if yv else MU, fontsize=18, ha="center", weight="bold")
    ax.text(4.8, 4.6, "OR", color=FG, fontsize=18, ha="center", va="center", weight="bold", zorder=4)
    for i, (ca, cb) in enumerate(combos):
        row = i == k; yy = 6.2 - i * 0.6
        ax.text(11.2, yy, f"{ca}", color=YEL if row else FG, fontsize=18, ha="center"); ax.text(12.4, yy, f"{cb}", color=YEL if row else FG, fontsize=18, ha="center")
        ax.text(13.8, yy, f"{ca | cb}", color=YEL if row else FG, fontsize=18, ha="center", weight="bold")
    ax.text(11.2, 6.85, "A", color=MU, fontsize=15, ha="center"); ax.text(12.4, 6.85, "B", color=MU, fontsize=15, ha="center"); ax.text(13.8, 6.85, "Y", color=MU, fontsize=15, ha="center")
    ax.text(12.5, 3.1, "high if EITHER input is high", color=FG, fontsize=15, ha="center")
    ax.text(12.5, 2.55, "(two switches side by side → one lamp)", color=MU, fontsize=13, ha="center")

def gate_mini(ax, cs4):
    x, y, sc = 7.0, 1.75, 0.8
    or_gate(ax, x, y, s=sc); ax.text(x + 0.62, y + 0.36, "OR", color=FG, fontsize=11, ha="center", va="center", zorder=4)
    ya, yb, yo = y + sc * 0.68, y + sc * 0.22, y + sc * 0.45
    ax.plot([5.6, x + 0.25], [ya, ya], color=DAT, lw=2); ax.text(5.5, ya, "MOSI (A)", color=DAT, fontsize=12, ha="right", va="center")
    ax.plot([5.6, x + 0.25], [yb, yb], color=CSC, lw=2); ax.text(5.5, yb, f"CS4 (B) = {cs4}", color=CSC, fontsize=12, ha="right", va="center")
    ax.plot([x + sc * 1.8, 10.2], [yo, yo], color=OK, lw=2); ax.text(10.3, yo, "accel pin (Y)", color=OK, fontsize=12, va="center")


def s_fix_off(ax, p, t):
    title(ax, "The fix: accelerometer NOT selected")
    gate_mini(ax, cs4=1)
    waves_scene(ax, p, t, gate=True, cs4=1, corrupt=False)
    ax.text(0.4, 7.75, "CS4 high  →  accel pin stuck HIGH  →  no START possible", color=OK, fontsize=15)

def s_fix_on(ax, p, t):
    title(ax, "Accelerometer selected")
    gate_mini(ax, cs4=0)
    waves_scene(ax, p, t, gate=True, cs4=0, corrupt=False)
    ax.text(0.4, 7.75, "CS4 low  →  accel pin copies MOSI  →  normal SPI", color=OK, fontsize=15)

def s_end(ax, p, t):
    ax.text(8, 7.3, "The OR gate = an earplug", color=FG, fontsize=32, ha="center", weight="bold")
    pts = [("Not selected (CS4 high): data pin held high, hears nothing", OK), ("Selected (CS4 low): data pin copies MOSI", OK),
           ("One-way gate: the accelerometer can never pull MOSI", OK), ("BrainTech-8: put it on the ESP32-S3's own I²C pins, no gate needed", YEL)]
    for i, (s, c) in enumerate(pts):
        if p > 0.1 + i * 0.15: ax.text(2.0, 6.0 - i * 0.8, "•  " + s, color=c, fontsize=18)


SCENES = [
 ("Why does the Cyton put a tiny OR gate in front of its accelerometer? To understand it, we need two ideas: the I squared C protocol, and the OR gate.", s_title),
 ("First, a quick recap of the shared S P I bus. The PIC thirty two is the boss. The clock, MOSI and MISO wires are shared by the A D S twelve ninety nine, the accelerometer, and the SD card. Each chip has its own chip select wire. Only the chip whose chip select is low takes part. The others should ignore the bus.", s_bus),
 ("Now, I squared C. It's another way chips talk, using just two wires: a clock called S C L, and a data wire called S D A. There's no chip select. Instead, every chip listens all the time. To begin a message, the boss sends a special start signal: the data wire falls while the clock is high. It means: attention, everyone. Then the boss sends an address, and only the chip with that address answers.", s_i2c),
 ("The accelerometer can speak both languages, using the same pins. It decides by looking at its chip select pin. When chip select is low, it speaks S P I. When chip select is high, it switches to I squared C, and listens for a start signal.", s_dual),
 ("Here's the problem. The PIC thirty two is talking to the A D S twelve ninety nine, so the accelerometer's chip select is high, and it's listening for I squared C on the shared wires. S P I has no rule about when data may change, so sometimes MOSI falls while the clock is high. The accelerometer hears a start signal. If the next bits look like its address, it answers by pulling the data wire low, and that wire is the shared MOSI. The A D S twelve ninety nine receives a wrong bit.", s_problem),
 ("The fix uses an OR gate. It has two inputs and one output. The output is high if either input is high, and low only when both inputs are low. It's like two light switches wired side by side to one lamp.", s_orgate),
 ("On the Cyton, input A is the shared MOSI, input B is the accelerometer's chip select, C S four, and the output goes to the accelerometer's data pin. When the accelerometer isn't selected, C S four is high, so the output is stuck high. Its data pin can never fall, so it can never hear a fake start signal. And because a gate only passes signals one way, the accelerometer can never touch MOSI.", s_fix_off),
 ("When the PIC thirty two selects the accelerometer, C S four goes low. Now the output simply copies MOSI, and normal S P I works.", s_fix_on),
 ("So the OR gate is an earplug that the accelerometer wears whenever it isn't being spoken to. On your own board, you can avoid the problem completely by connecting the accelerometer to the E S P thirty two's separate I squared C pins.", s_end),
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
            fig.savefig(os.path.join(d, f"og{i}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
