"""Narrated video: the Cyton's microcontroller, U7 PIC32MX250F128B (chipKIT), redrawn from the schematic.
Power + Vcap, MCLR reset (R7, SW3), 8 MHz crystal (X1, C23, C20), BOOT_EN (SW1, R9), the SPI bus with CS1-CS4,
DRDY/INT1/RESET, the UART + programming link to the RFduino, the blue LED on PGD, spare pins D13/D18, and the ESP32-S3 mapping.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_pic32_video.py -> pic32_microcontroller.mp4
Preview frames: python make_pic32_video.py --stills DIR"""
import math, os, re, subprocess, sys, tempfile, textwrap, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon

FPS, W, H = 24, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic32_microcontroller.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM, PANEL = "#0b1730", "#eef2f7", "#8a97ab", "#33415c", "#0f1f3d"
C = {"pow": "#5aa9ff", "rst": "#ff8a5c", "clk": "#ffd166", "boot": "#a77bff", "spi": "#2ec4a0", "radio": "#f28fb0", "led": "#7fb2ff", "spare": "#c9d2dc"}

LEFT = [(1, "MCLR", "rst", None), (2, "D9", "spi", "DRDY"), (3, "D10", "spi", "MOSI"), (4, "D11", "radio", "PGD"), (5, "D12", "radio", "PGC"),
        (6, "D13", "spare", "D13"), (7, "D14", "radio", "TXD"), (9, "D15", "clk", None), (10, "D16", "clk", None), (11, "D17", "boot", "BOOT_EN"),
        (12, "D18", "spare", "D18")]
RIGHT = [(26, "D8", "spi", "CS1"), (25, "D7", "spi", "SCLK"), (24, "D6", "radio", "RXD"), (22, "D5", "spi", "MISO"), (21, "D4", "spi", "RESET"),
         (18, "D3", "spi", "CS2"), (17, "D2", "spi", "CS3"), (16, "D1", "spi", "CS4"), (14, "D0", "spi", "INT1")]
LY = lambda i: 6.72 - i * 0.38
RYp = lambda i: 6.45 - i * 0.4
GB = 1.95                                           # ground bus height


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
def cap_v(ax, x, y, c=FG):
    ax.plot([x - 0.06] * 2, [y - 0.17, y + 0.17], color=c, lw=2.4); ax.plot([x + 0.06] * 2, [y - 0.17, y + 0.17], color=c, lw=2.4)
def cap_h(ax, x, y, c=FG):
    ax.plot([x - 0.2, x + 0.2], [y + 0.06] * 2, color=c, lw=2.4); ax.plot([x - 0.2, x + 0.2], [y - 0.06] * 2, color=c, lw=2.4)
def res_v(ax, x, y0, y1, c=FG): ax.add_patch(Rectangle((x - 0.1, y0), 0.2, y1 - y0, fc=BG, ec=c, lw=1.6, zorder=3))
def button(ax, x0, x1, y, c=FG, pressed=False):
    ax.plot([x0, x0 + 0.15], [y, y], color=c, lw=1.6); ax.plot([x1 - 0.15, x1], [y, y], color=c, lw=1.6)
    for x in (x0 + 0.15, x1 - 0.15): ax.plot(x, y, "o", ms=4, color=c)
    yy = y + (0.02 if pressed else 0.2)
    ax.plot([x0 + 0.1, x1 - 0.1], [yy, yy], color=c, lw=2.2); ax.plot([(x0 + x1) / 2] * 2, [yy, yy + 0.18], color=c, lw=2.2)
def note(ax, lines, p=1.0, x=12.35, y=7.55, step=0.12, dy=0.46, w=3.55):
    ax.add_patch(FancyBboxPatch((x - 0.1, y - dy * len(lines) - 0.05), w, dy * len(lines) + 0.4, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1, zorder=5))
    for i, (s, c) in enumerate(lines):
        if p >= i * step: ax.text(x + 0.05, y - i * dy, s, color=c, fontsize=12, va="top", zorder=6)
def dots(ax, pts, prog, c, n=4):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; L = sum(seg)
    for k in range(n):
        d = ((k / n + prog) % 1) * L; acc = 0
        for (a, b), s in zip(zip(pts, pts[1:]), seg):
            if d <= acc + s:
                tt = (d - acc) / s if s else 0
                ax.plot(a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt, "o", ms=6, color=c, zorder=6); break
            acc += s


def pic(ax, hi=(), t=0.0, flow=(), sw3=False, sw1=False, led=False):
    col = lambda g: C[g] if g in hi else FG
    ax.add_patch(Rectangle((6.6, 2.35), 2.8, 4.85, fc=PANEL, ec=FG, lw=1.8, zorder=2))
    ax.text(9.5, 7.35, "U7  PIC32MX250F128B", color=MU, fontsize=10.5)
    # top: power
    cp = col("pow")
    for x, nm, num in ((6.9, "Vdd", 28), (7.55, "Vdd", 23), (8.2, "Vdd", 13), (8.85, "Vbus", 15)):
        ax.plot([x, x], [7.2, 7.75], color=cp, lw=1.6); ax.text(x, 6.95, nm, color=cp, fontsize=9.5, ha="center", rotation=90, va="center", zorder=3)
        ax.text(x + 0.06, 7.45, str(num), color=MU, fontsize=8.5)
    ax.plot([4.9, 8.85], [7.75, 7.75], color=cp, lw=1.6); ax.plot([5.6, 5.6], [7.75, 8.05], color=cp, lw=1.6)
    ax.plot([5.4, 5.8], [8.05, 8.05], color=cp, lw=2.2); ax.text(5.95, 8.05, "DVDD 3.3 V", color=cp, fontsize=10.5, va="center")
    # bottom: Vcap + grounds
    ax.plot([6.9, 6.9], [2.35, 2.25], color=cp, lw=1.6); ax.text(6.9, 2.58, "Vcap", color=cp, fontsize=8.5, ha="center", rotation=90, va="center", zorder=3)
    ax.plot([6.9, 6.9], [2.25, 2.17], color=cp, lw=1.6); cap_h(ax, 6.9, 2.1, cp); ax.plot([6.9, 6.9], [2.04, GB], color=cp, lw=1.6)
    ax.text(6.55, 2.12, "C25 10 µF", color=cp, fontsize=9.5, ha="right", va="center")
    for x, num in ((7.55, 19), (8.2, 8), (8.85, 27)):
        ax.plot([x, x], [2.35, GB], color=cp, lw=1.6); ax.text(x, 2.58, "GND", color=cp, fontsize=8.5, ha="center", rotation=90, va="center", zorder=3)
    ax.plot([0.7, 8.85], [GB, GB], color=FG, lw=1.6); ground(ax, 8.2, GB - 0.02)
    # left pins
    for i, (num, nm, g, net) in enumerate(LEFT):
        y = LY(i); c = col(g)
        ax.text(6.7, y, nm, color=c, fontsize=10, va="center", zorder=3); ax.text(6.45, y + 0.11, str(num), color=MU, fontsize=8.5, ha="right")
        if net in ("DRDY", "MOSI", "PGC", "D13", "TXD", "D18"):
            ax.plot([6.6, 5.0], [y, y], color=c, lw=1.6); ax.annotate("", xy=(4.85, y), xytext=(5.1, y), arrowprops=dict(arrowstyle="->", color=c, lw=1.4))
            ax.text(4.75, y, net, color=c, fontsize=10.5, ha="right", va="center")
            if net in flow: dots(ax, [(6.6, y), (5.0, y)] if net not in ("DRDY",) else [(5.0, y), (6.6, y)], t * 0.6, c)
    # MCLR: R7 pull-up, SW3 to ground
    y = LY(0); c = col("rst")
    ax.plot([6.6, 3.85], [y, y], color=c, lw=1.6); ax.plot(4.9, y, "o", color=c, ms=4)
    ax.plot([4.9, 4.9], [y, 6.95], color=c, lw=1.6); res_v(ax, 4.9, 6.95, 7.45, c); ax.plot([4.9, 4.9], [7.45, 7.75], color=c, lw=1.6)
    ax.text(4.65, 7.2, "R7 470k", color=c, fontsize=9.5, ha="right", va="center"); ax.text(5.6, y + 0.15, "MCLR", color=c, fontsize=9.5)
    button(ax, 2.85, 3.85, y, c, pressed=sw3); ax.text(3.35, y - 0.35, "SW3 (RST)", color=c, fontsize=9.5, ha="center")
    ax.plot([2.85, 0.7, 0.7], [y, y, GB], color=c, lw=1.6)
    # D11 = PGD with LED + R8
    y = LY(3); c = col("radio") if "radio" in hi else (col("led") if "led" in hi else FG)
    ax.plot([6.6, 5.0], [y, y], color=c, lw=1.6); ax.annotate("", xy=(4.85, y), xytext=(5.1, y), arrowprops=dict(arrowstyle="->", color=c, lw=1.4))
    ax.text(4.75, y + 0.02, "PGD", color=c, fontsize=10.5, ha="right", va="center")
    cl = C["led"] if ("led" in hi or led) else FG
    ax.plot([5.6, 5.6, 3.5], [y, y - 0.001, y], color=cl, lw=0)
    ax.plot([4.0, 2.9], [y + 0.3, y + 0.3], color=cl, lw=1.6); ax.plot([4.0, 4.0], [y, y + 0.3], color=cl, lw=1.6)
    ax.add_patch(Polygon([[3.55, y + 0.15], [3.55, y + 0.45], [3.25, y + 0.3]], closed=True, fc=cl if led else BG, ec=cl, lw=1.6, zorder=3))
    ax.plot([3.22, 3.22], [y + 0.15, y + 0.45], color=cl, lw=1.8); ax.text(3.4, y + 0.6, "BLUE LED D1", color=cl, fontsize=9.5, ha="center")
    ax.plot([2.9, 1.6, 1.6], [y + 0.3, y + 0.3, y - 0.2], color=cl, lw=1.6); res_v(ax, 1.6, y - 0.75, y - 0.2, cl)
    ax.plot([1.6, 1.6], [y - 0.75, y - 1.0], color=cl, lw=1.6); ax.text(1.35, y - 0.48, "R8 1k", color=cl, fontsize=9.5, ha="right", va="center")
    ax.plot([1.6, 0.7], [y - 1.0, y - 1.0], color=cl, lw=1.6)
    if led:
        for k in range(3):
            a = math.radians(60 + k * 30); ax.plot([3.4, 3.4 + 0.35 * math.cos(a)], [y + 0.5, y + 0.5 + 0.35 * math.sin(a)], color=C["led"], lw=1.5)
    # crystal on D15 / D16
    cc = col("clk"); y1, y2 = LY(7), LY(8)
    for yy, nm in ((y1, "C23 18pF"), (y2, "C20 18pF")):
        ax.plot([6.6, 4.3], [yy, yy], color=cc, lw=1.6); ax.plot([4.3, 2.3], [yy, yy], color=cc, lw=1.6); cap_v(ax, 2.2, yy, cc)
        ax.plot([2.1, 0.7], [yy, yy], color=cc, lw=1.6); ax.text(2.2, yy + (0.25 if yy == y1 else -0.3), nm, color=cc, fontsize=9, ha="center", va="center")
    ax.add_patch(Rectangle((4.15, y2 + 0.08), 0.3, y1 - y2 - 0.16, fc=BG, ec=cc, lw=1.6, zorder=3))
    ax.text(4.75, (y1 + y2) / 2, "X1 8 MHz", color=cc, fontsize=10, va="center")
    # BOOT_EN on D17: SW1 to DVDD, R9 to ground
    y = LY(9); cb = col("boot")
    ax.plot([6.6, 4.0], [y, y], color=cb, lw=1.6); ax.text(5.6, y + 0.13, "BOOT_EN", color=cb, fontsize=9.5)
    ax.plot(4.0, y, "o", color=cb, ms=4); ax.plot([4.0, 4.0], [y, 2.62], color=cb, lw=1.6); res_v(ax, 4.0, 2.12, 2.62, cb); ax.plot([4.0, 4.0], [2.12, GB], color=cb, lw=1.6)
    ax.text(4.25, 2.37, "R9 470k", color=cb, fontsize=9.5, va="center")
    button(ax, 2.9, 3.9, y, cb, pressed=sw1); ax.plot([3.9, 4.0], [y, y], color=cb, lw=1.6)
    ax.plot([2.9, 2.6], [y, y], color=cb, lw=1.6); ax.plot([2.6, 2.6], [y - 0.15, y + 0.15], color=cb, lw=2.2)
    ax.text(2.5, y, "DVDD", color=cb, fontsize=9.5, ha="right", va="center"); ax.text(3.4, y - 0.35, "SW1 (PROG)", color=cb, fontsize=9.5, ha="center")
    # right pins
    for i, (num, nm, g, net) in enumerate(RIGHT):
        y = RYp(i); c = col(g)
        ax.text(9.3, y, nm, color=c, fontsize=10, va="center", ha="right", zorder=3); ax.text(9.55, y + 0.11, str(num), color=MU, fontsize=8.5)
        ax.plot([9.4, 11.1], [y, y], color=c, lw=1.6); ax.annotate("", xy=(11.25, y), xytext=(11.0, y), arrowprops=dict(arrowstyle="->", color=c, lw=1.4))
        ax.text(11.35, y, net, color=c, fontsize=10.5, va="center")
        if net in flow: dots(ax, [(9.4, y), (11.1, y)] if net not in ("MISO", "INT1", "RXD") else [(11.1, y), (9.4, y)], t * 0.6, c)


# ---- scenes ----
def s_title(ax, p, t):
    title(ax, "The Cyton's brain: U7, a PIC32")
    pic(ax)
    note(ax, [("runs the firmware", FG), ("talks to: ADS1299, SD card,", FG), ("   accelerometer", FG), ("hands data to the radio", FG)], p)

def s_power(ax, p, t):
    title(ax, "Power and Vcap")
    pic(ax, hi=("pow",))
    note(ax, [("3 × Vdd + Vbus → DVDD", C["pow"]), ("3 × GND → ground", C["pow"]), ("Vcap → C25 10 µF:", C["pow"]), ("   internal regulator for", FG),
              ("   the processor core", FG), ("   (like the ADS1299 VCAPs)", MU)], p, step=0.1)

def s_reset(ax, p, t):
    title(ax, "MCLR: the reset pin")
    pressed = 0.4 < p < 0.7
    pic(ax, hi=("rst",), sw3=pressed)
    note(ax, [("R7 pulls MCLR up → runs", C["rst"]), ("press SW3 (RST):", C["rst"]), ("   MCLR → ground → restart", FG), ("release: R7 pulls it", FG),
              ("   back up", FG), ("MCLR: " + ("LOW · resetting" if pressed else "HIGH · running"), "#ef5b5b" if pressed else C["spi"])], p, step=0.1)

def s_clock(ax, p, t):
    title(ax, "The crystal: an exact heartbeat")
    pic(ax, hi=("clk",))
    note(ax, [("X1 = 8 MHz crystal", C["clk"]), ("C23, C20 = 18 pF", C["clk"]), ("   help it start and settle", FG), ("multiplied up inside", FG),
              ("   to run the processor", FG), ("exact timing for serial", FG), ("   links (radio, USB)", FG)], p, step=0.1)
    ax.add_patch(FancyBboxPatch((12.25, 2.15), 3.55, 1.0, boxstyle="round,pad=0.05", fc=PANEL, ec=DIM, lw=1, zorder=5))
    xs = np.linspace(0, 1, 300); ax.plot(12.4 + xs * 3.3, 2.65 + 0.3 * np.sin(2 * np.pi * (16 * xs + t * 2)), color=C["clk"], lw=1.5, zorder=6)

def s_boot(ax, p, t):
    title(ax, "BOOT_EN: run, or load new firmware")
    pressed = 0.4 < p < 0.75
    pic(ax, hi=("boot",), sw1=pressed)
    note(ax, [("R9 pulls BOOT_EN low", C["boot"]), ("   → run the program", FG), ("hold SW1 (PROG) + reset:", C["boot"]), ("   BOOT_EN high", FG),
              ("   → bootloader waits for", FG), ("      new firmware", FG), ("BOOT_EN: " + ("HIGH" if pressed else "LOW"), C["boot"])], p, step=0.1)

def s_spi(ax, p, t):
    title(ax, "The SPI bus and the doorbells")
    pic(ax, hi=("spi",), t=t, flow=("SCLK", "MOSI", "MISO", "CS1", "DRDY", "INT1"))
    note(ax, [("SCLK, MOSI, MISO: shared", C["spi"]), ("CS1 → ADS1299", C["spi"]), ("CS2 → Daisy ADS1299", C["spi"]), ("CS3 → SD card", C["spi"]),
              ("CS4 → accelerometer", C["spi"]), ("DRDY, INT1: doorbells", FG), ("RESET → ADS1299", FG)], p, step=0.1)

def s_radio(ax, p, t):
    title(ax, "The link to the radio, and the LED")
    pic(ax, hi=("radio", "led"), t=t, flow=("TXD", "RXD", "PGC"), led=(int(t * 2) % 2 == 0))
    note(ax, [("TXD → radio: the data", C["radio"]), ("RXD ← radio: commands", C["radio"]), ("PGC, PGD: programming", C["radio"]), ("   → firmware updates", FG),
              ("      over the air", FG), ("blue LED + R8 1 kΩ", C["led"]), ("   shares PGD: status light", FG)], p, step=0.1)

def s_spare(ax, p, t):
    title(ax, "Spare pins and \"D\" numbers")
    pic(ax, hi=("spare",))
    note(ax, [("D13, D18 → side headers", C["spare"]), ("   for your experiments", FG), ("D0 … D18 = chipKIT pin", FG), ("   numbers, used in code:", FG),
              ("   digitalWrite(13, HIGH)", C["clk"])], p, step=0.13)

def s_end(ax, p, t):
    ax.text(8, 7.7, "On BrainTech-8: one ESP32-S3", color=FG, fontsize=28, ha="center", weight="bold")
    rows = [("PIC32 + RFduino", "→ one ESP32-S3 (processor + Wi-Fi + Bluetooth)", C["spi"]),
            ("Power", "3.3 V + decoupling at every supply pin", C["pow"]),
            ("Reset / boot", "EN button (reset) + GPIO0 button (boot)", C["rst"]),
            ("ADS1299 link", "SPI + CS + DRDY + RESET", C["spi"]),
            ("Clock, programming", "crystal inside the module · program over USB", C["clk"])]
    for i, (a, b, c) in enumerate(rows):
        if p > 0.06 + i * 0.14:
            y = 6.5 - i * 0.95
            ax.text(1.0, y, a, color=c, fontsize=17, weight="bold", va="center"); ax.text(5.0, y, b, color=FG, fontsize=15.5, va="center")


SCENES = [
 ("This is the brain of the Cyton: U seven, a PIC thirty two microcontroller. It runs the firmware, talks to the A D S twelve ninety nine, the SD card and the accelerometer, and hands the data to the radio.", s_title),
 ("Power first. Three V D D pins and the V bus pin connect to D V D D, three point three volts, and three ground pins go to ground. V cap gets C twenty five, ten microfarads. Like the A D S twelve ninety nine's V CAP pins, it connects to a regulator inside the chip, which makes the lower voltage the processor core runs on. It needs this capacitor to stay stable.", s_power),
 ("Pin one, M C L R, is the reset pin. R seven, four hundred seventy kilo-ohms, pulls it up to D V D D, so the chip runs. Pressing S W three, the reset button, connects it to ground and restarts the chip. When you let go, R seven pulls it back up.", s_reset),
 ("Pins nine and ten hold the crystal, X one, eight megahertz, with two eighteen picofarad capacitors to ground. The crystal vibrates at a very exact rate. The chip multiplies it up to run its processor, and uses it to time its serial links accurately.", s_clock),
 ("Pin eleven is boot enable. R nine pulls it to ground, so normally the chip just runs its program. S W one, the PROG button, connects it to D V D D. If you hold it while resetting, the chip starts its boot loader instead, and waits for new firmware.", s_boot),
 ("The right side is the S P I bus you know. S clock, MOSI and MISO are shared. Each chip gets its own select line: C S one for the A D S twelve ninety nine, C S two for a second one on the Daisy board, C S three for the SD card, and C S four for the accelerometer. Data ready and int one are the doorbells, and reset lets the PIC restart the A D S twelve ninety nine.", s_spi),
 ("T X D and R X D are a serial link to the RFduino radio: data goes out on T X D, and commands come back on R X D. P G C and P G D are the programming lines, which the radio uses to load new firmware into the PIC, over the air. The blue LED, with R eight, one kilo-ohm, shares the P G D pin, as a status light.", s_radio),
 ("D thirteen and D eighteen are spare pins, brought out to the side headers for your own experiments. The D numbers are chip KIT pin numbers: the Arduino style names you use in code.", s_spare),
 ("On your board, one E S P thirty two S three replaces both the PIC thirty two and the RFduino. It needs the same things: power with decoupling, a reset button and a boot button, and S P I with chip select, data ready and reset for the A D S twelve ninety nine. Its crystal is inside the module, and you program it over U S B.", s_end),
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
            fig, ax = new_fig(); draw(ax, 0.55, 3.3); caption(ax, text, 0.55)
            fig.savefig(os.path.join(d, f"pc{i}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
