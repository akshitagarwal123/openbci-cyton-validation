"""Narrated explainer video: the ADS1299 functional block diagram (datasheet section 9.2, page 19), block by block.
A simplified redrawing of TI's diagram; one channel's signal is animated from electrode pin to SPI.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_ads1299_block_video.py  ->  ads1299_block_diagram.mp4
Preview frames: python make_ads1299_block_video.py --stills DIR"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ads1299_block_diagram.mp4")
VOICE = "Samantha"
BG, FG, MU, DIM = "#0f1418", "#e8edf0", "#93a1aa", "#3a454d"
C = dict(pins="#ef6b5e", mux="#9a92ec", srb="#f0a04b", pga="#6cc48a", adc="#5b9be0", ref="#d9a441",
         bias="#f0a04b", ctrl="#93a1aa", spi="#4fd1c5", osc="#93a1aa", pwr="#e3d26f")
ROWS = [(7.2, "CH1"), (6.0, "CH2"), (4.8, "CH3"), (3.0, "CH8")]


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
def side(fig, lines, p=1.0, step=0.0, x=0.685, y0=0.80, dy=0.066):
    for i, (s, c, f) in enumerate(lines):
        if p >= i * step: fig.text(x, y0 - i * dy, s, color=c, fontsize=min(f, 15.5), va="top")


def chip(fig, hi=(), rect=(0.02, 0.15, 0.66, 0.73), dot=None, mux_pos=0):
    ax = fig.add_axes(rect); ax.set_xlim(-0.2, 13.4); ax.set_ylim(-0.2, 9.4); ax.axis("off"); ax.set_facecolor(BG)
    def col(k): return C[k] if (not hi or k in hi) else DIM
    def lw(k): return 2.4 if k in hi else 1.2
    ax.add_patch(Rectangle((0.5, 0.6), 11.9, 8.4, fc="none", ec=MU, lw=1.2))
    ax.text(0.6, 9.1, "ADS1299", color=FG, fontsize=13, weight="bold")
    ax.plot([7.75, 7.75], [0.7, 8.9], color=MU if "pwr" in hi else DIM, ls=":", lw=1)
    ax.text(4.0, 9.1, "analog side", color=col("pwr"), fontsize=10, ha="center")
    ax.text(10.1, 9.1, "digital side", color=col("pwr"), fontsize=10, ha="center")
    # pins
    for y, lab in ROWS:
        for dy, s in ((0.25, "P"), (-0.25, "N")):
            ax.plot(0.5, y + dy, "o", ms=5, color=col("pins"))
            ax.plot([0.5, 2.0], [y + dy, y + dy], color=col("pins"), lw=lw("pins"))
        ax.text(0.3, y, lab, color=col("pins"), fontsize=10, ha="right", va="center")
    ax.text(0.3, 3.9, "⋮", color=col("pins"), fontsize=14, ha="right", va="center")
    # MUX
    ax.add_patch(Rectangle((2.0, 2.4), 0.9, 5.5, fc=BG, ec=col("mux"), lw=lw("mux")))
    ax.text(2.45, 5.1, "MUX", color=col("mux"), fontsize=11, ha="center", va="center", rotation=90)
    # SRB / BIASIN pins
    for x, lab in ((2.15, "SRB1"), (2.45, "SRB2"), (2.75, "BIASIN")):
        ax.annotate("", xy=(x, 2.4), xytext=(x, 0.6), arrowprops=dict(arrowstyle="->", color=col("srb"), lw=lw("srb")))
        ax.text(x, 0.2, lab, color=col("srb"), fontsize=8, ha="center", rotation=90, va="top")
    # PGA + ADC per row
    for y, lab in ROWS:
        ax.plot([2.9, 4.0], [y + 0.25, y + 0.25], color=col("pga"), lw=1); ax.plot([2.9, 4.0], [y - 0.25, y - 0.25], color=col("pga"), lw=1)
        ax.add_patch(Polygon([[4.0, y + 0.45], [4.0, y - 0.45], [4.9, y]], closed=True, fc=BG, ec=col("pga"), lw=lw("pga")))
        ax.text(4.3, y, "PGA", color=col("pga"), fontsize=7, va="center")
        ax.plot([4.9, 5.6], [y, y], color=col("adc"), lw=1)
        ax.add_patch(Rectangle((5.6, y - 0.4), 1.4, 0.8, fc=BG, ec=col("adc"), lw=lw("adc")))
        ax.text(6.3, y, "ΔΣ ADC", color=col("adc"), fontsize=8, ha="center", va="center")
        ax.plot([7.0, 8.0], [y, y], color=col("ctrl"), lw=1)
    ax.text(6.3, 3.9, "⋮", color=col("adc"), fontsize=14, ha="center", va="center")
    # reference
    ax.add_patch(Rectangle((5.6, 8.05), 1.4, 0.6, fc=BG, ec=col("ref"), lw=lw("ref")))
    ax.text(6.3, 8.35, "Reference", color=col("ref"), fontsize=8, ha="center", va="center")
    ax.annotate("", xy=(6.3, 7.62), xytext=(6.3, 8.05), arrowprops=dict(arrowstyle="->", color=col("ref"), lw=lw("ref")))
    # BIAS amp
    for y, _ in ROWS: ax.plot([4.6, 4.6], [y - 0.35, 1.75], color=col("bias"), lw=0.8, ls="--")
    ax.add_patch(Polygon([[3.9, 1.85], [3.9, 0.95], [4.9, 1.4]], closed=True, fc=BG, ec=col("bias"), lw=lw("bias")))
    ax.text(4.15, 1.4, "BIAS", color=col("bias"), fontsize=7, va="center")
    ax.annotate("", xy=(4.9, 0.0), xytext=(4.9, 1.4), arrowprops=dict(arrowstyle="->", color=col("bias"), lw=lw("bias")))
    ax.text(5.05, 0.15, "BIAS OUT", color=col("bias"), fontsize=8, va="center")
    # control
    ax.add_patch(Rectangle((8.0, 2.4), 1.4, 5.5, fc=BG, ec=col("ctrl"), lw=lw("ctrl")))
    ax.text(8.7, 5.1, "Control", color=col("ctrl"), fontsize=11, ha="center", va="center", rotation=90)
    # SPI and pins
    ax.add_patch(Rectangle((10.0, 6.1), 1.4, 1.5, fc=BG, ec=col("spi"), lw=lw("spi")))
    ax.text(10.7, 6.85, "SPI", color=col("spi"), fontsize=11, ha="center", va="center")
    ax.plot([9.4, 10.0], [6.85, 6.85], color=col("spi"), lw=1)
    for i, s in enumerate(("DRDY", "CS", "SCLK", "DIN", "DOUT")):
        y = 8.2 - i * 0.45
        ax.plot([11.4 if s != "DRDY" else 9.4, 12.4], [y, y], color=col("spi"), lw=lw("spi") * 0.6)
        ax.plot(12.4, y, "o", ms=4, color=col("spi")); ax.text(12.55, y, s, color=col("spi"), fontsize=9, va="center")
    # oscillator + control pins
    ax.add_patch(Rectangle((10.0, 4.3), 1.4, 0.8, fc=BG, ec=col("osc"), lw=lw("osc")))
    ax.text(10.7, 4.7, "Clock", color=col("osc"), fontsize=9, ha="center", va="center")
    ax.plot([9.4, 10.0], [4.7, 4.7], color=col("osc"), lw=1)
    for i, s in enumerate(("START", "RESET", "PWDN")):
        y = 3.3 - i * 0.45; ax.plot([9.4, 12.4], [y, y], color=col("ctrl"), lw=0.8)
        ax.plot(12.4, y, "o", ms=4, color=col("ctrl")); ax.text(12.55, y, s, color=col("ctrl"), fontsize=9, va="center")
    # power
    for x, s in ((1.2, "AVDD"), (2.6, "AVSS")): ax.text(x, 8.6, s, color=col("pwr"), fontsize=9, ha="center")
    for x, s in ((9.0, "DVDD"), (11.6, "DGND")): ax.text(x, 8.6, s, color=col("pwr"), fontsize=9, ha="center")
    if dot is not None:
        path = [(0.5, 7.45), (2.0, 7.45), (2.9, 7.45), (4.0, 7.45), (4.9, 7.2), (5.6, 7.2), (7.0, 7.2), (8.0, 7.2), (8.7, 7.2), (8.7, 6.85), (10.0, 6.85), (11.4, 6.85), (11.4, 6.4), (12.4, 6.4)]
        L = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]; d = dot * sum(L); acc = 0
        for (a, b), l in zip(zip(path, path[1:]), L):
            if d <= acc + l:
                t = (d - acc) / l; ax.plot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, "o", ms=12, color="#ffd166", zorder=9); break
            acc += l
    return ax


# ---------- scenes ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.9, "Inside the ADS1299", color=FG, fontsize=40, ha="center", weight="bold")
    fig.text(0.5, 0.84, "the functional block diagram (datasheet section 9.2, page 19)", color=MU, fontsize=19, ha="center")
    chip(fig, rect=(0.18, 0.15, 0.64, 0.66), dot=(t * 0.25) % 1)

def s_big(fig, p, t):
    title(fig, "The big picture")
    chip(fig, hi=("pwr",) if p > 0.5 else ())
    side(fig, [("Electrodes in on the left,", FG, 17), ("numbers out on the right.", FG, 17), ("", FG, 8),
               ("Left of the dotted line:", C["pwr"], 17), ("analog (tiny voltages)", C["pwr"], 17),
               ("Right of it:", C["pwr"], 17), ("digital (ones and zeros)", C["pwr"], 17)], p=p, step=0.1)

def s_pins(fig, p, t):
    title(fig, "1. Input pins")
    chip(fig, hi=("pins",))
    side(fig, [("8 channels, each with", FG, 17), ("a P and an N pin.", C["pins"], 17), ("", FG, 8),
               ("Each channel measures", FG, 17), ("P minus N:", FG, 17), ("electrode minus reference.", C["pins"], 17)], p=p, step=0.12)

def s_mux(fig, p, t):
    title(fig, "2. The MUX: a selector switch")
    chip(fig, hi=("mux",))
    opts = ["the electrodes (normal)", "inputs shorted (noise test)", "test signal (self-check)", "temperature sensor", "supply voltage"]
    k = min(4, int(p * 5.5))
    side(fig, [("Each channel can read:", FG, 17)] + [(("▶ " if i == k else "   ") + o, C["mux"] if i == k else MU, 16) for i, o in enumerate(opts)])

def s_srb(fig, p, t):
    title(fig, "3. SRB1 and SRB2: shared references")
    chip(fig, hi=("srb", "mux"))
    side(fig, [("One pin shared by all channels:", FG, 17), ("SRB1 can join all N inputs,", C["srb"], 17),
               ("SRB2 can join all P inputs.", C["srb"], 17), ("", FG, 8), ("Your ear clip goes here, so", FG, 17),
               ("channel = electrode − ear.", FG, 17), ("The Cyton uses SRB2.", MU, 16)], p=p, step=0.1)

def s_pga(fig, p, t):
    title(fig, "4. PGA: the amplifier")
    chip(fig, hi=("pga",))
    side(fig, [("Low-noise in-amp,", FG, 17), ("per channel.", FG, 17), ("Gain set in software:", C["pga"], 17),
               ("1, 2, 4, 6, 8, 12 or 24.", C["pga"], 17), ("", FG, 8), ("Amplifies P − N;", FG, 17), ("the 50 Hz on both cancels.", FG, 17)], p=p, step=0.1)

def s_adc(fig, p, t):
    title(fig, "5. ADC: voltage → number")
    chip(fig, hi=("adc", "ref"))
    side(fig, [("One 24-bit ADC per channel,", FG, 17), ("so all 8 sample at the", FG, 17), ("same instant.", C["adc"], 17), ("", FG, 8),
               ("The Reference (4.5 V) is the", C["ref"], 17), ("ruler it measures against.", C["ref"], 17), ("At gain 24: range ±187 mV.", MU, 16)], p=p, step=0.1)

def s_bias(fig, p, t):
    title(fig, "6. BIAS amplifier: noise-cancelling for the body")
    chip(fig, hi=("bias", "pga"))
    side(fig, [("Listens to the channels", FG, 17), ("(dashed lines from the PGAs),", C["bias"], 17), ("works out the shared hum,", FG, 17),
               ("and pushes the opposite back", FG, 17), ("into the body via BIAS OUT.", C["bias"], 17), ("", FG, 8), ("That's your BIAS electrode.", MU, 16)], p=p, step=0.1)

def s_ctrl(fig, p, t):
    title(fig, "7. Control and clock: the conductor")
    chip(fig, hi=("ctrl", "osc"))
    side(fig, [("Control: keeps all 8 ADCs", FG, 17), ("in step, holds settings.", FG, 17), ("Clock: 2.048 MHz heartbeat.", FG, 17), ("", FG, 8),
               ("START: begin measuring", MU, 16), ("RESET: back to defaults", MU, 16), ("PWDN: power down", MU, 16)], p=p, step=0.1)

def s_spi(fig, p, t):
    title(fig, "8. SPI and DRDY: talking to the ESP32")
    chip(fig, hi=("spi",))
    side(fig, [("DRDY low = 'data ready'.", C["spi"], 17), ("The ESP32 pulls CS low, then", FG, 17), ("ticks SCLK and reads DOUT:", FG, 17),
               ("8 channels × 24 bits + status.", FG, 17), ("DIN: commands, settings.", FG, 17), ("", FG, 8), ("250 times a second (250 SPS).", MU, 16)], p=p, step=0.1)

def s_power(fig, p, t):
    title(fig, "9. Two power supplies, two grounds")
    chip(fig, hi=("pwr",))
    side(fig, [("AVDD / AVSS: analog, ±2.5 V", C["pwr"], 17), ("DVDD / DGND: digital, 3.3 V", C["pwr"], 17), ("", FG, 8),
               ("Digital parts switch fast and", FG, 17), ("make noise. Apart, they", FG, 17), ("can't spoil the µV signals.", FG, 17)], p=p, step=0.12)

def s_journey(fig, p, t):
    title(fig, "One sample, start to finish")
    chip(fig, dot=min(1, p * 1.25))
    steps = [("10 µV alpha arrives at IN1P", C["pins"]), ("MUX: passes it through", C["mux"]), ("PGA ×24 → 240 µV", C["pga"]),
             ("ADC: 240 µV ÷ 0.54 µV step", C["adc"]), ("   = about 447 counts", C["adc"]), ("ESP32 reads it on DOUT", C["spi"])]
    side(fig, [(s, c, 16) for s, c in steps], p=p, step=0.14)

def s_end(fig, p, t):
    fig.text(0.5, 0.82, "The path to remember", color=FG, fontsize=32, ha="center", weight="bold")
    fig.text(0.5, 0.72, "pin → MUX → PGA → ADC → Control → SPI → ESP32", color="#ffd166", fontsize=24, ha="center")
    qs = ["1. Which 4 blocks does a signal pass from IN1P to DOUT?", "2. What else can the MUX connect a channel to, and why?",
          "3. Where does the BIAS amp get its input, and where does its output go?", "4. Why are there two grounds?", "5. What does DRDY tell the ESP32?"]
    for i, q in enumerate(qs):
        if p > 0.15 + i * 0.13: fig.text(0.2, 0.58 - i * 0.065, q, color=FG, fontsize=18)


SCENES = [
 ("This video walks through the A D S twelve ninety nine's block diagram, from section nine point two of the datasheet, one block at a time.", s_title),
 ("Here's the big picture. Electrode signals come in on the left, and digital numbers go out on the right. Everything left of the dotted line is analog, handling tiny voltages. Everything right of it is digital: ones and zeros.", s_big),
 ("First, the input pins. There are eight channels, and each has two pins: P and N. Each channel measures the difference, P minus N. In E E G, that's the electrode minus the reference.", s_pins),
 ("Next, the mux, a selector switch. Normally it connects each channel to its electrodes. But it can also short the inputs together to measure the chip's own noise, connect a built-in test signal to check everything works, or read the temperature sensor and the supply voltage.", s_mux),
 ("The S R B pins are shared references. S R B one can be joined to the N input of every channel, and S R B two to every P input. Your ear clip connects here, so every channel becomes electrode minus ear. The Cyton uses S R B two.", s_srb),
 ("Then the P G A, the programmable gain amplifier. It's a low-noise instrumentation amplifier, one per channel, with a gain you set in software, from one up to twenty four. It amplifies P minus N, and the fifty hertz hum that's on both inputs cancels here.", s_pga),
 ("Next, the A D C turns the amplified voltage into a number. There's one twenty four bit A D C per channel, so all eight channels are measured at exactly the same instant. The reference block supplies four point five volts, the ruler the A D C measures against. At gain twenty four, the input range is about plus or minus one hundred eighty seven millivolts.", s_adc),
 ("At the bottom is the bias amplifier: noise-cancelling headphones for your body. The dashed lines show it listening to the channels. It works out the hum they share, and pushes the opposite back into the body through bias out. That's your bias electrode.", s_bias),
 ("On the digital side, the control block keeps all eight A D Cs in step and holds the settings. The clock is the chip's heartbeat, at two point zero four eight megahertz. The start pin begins measuring, reset returns to defaults, and power down turns it off.", s_ctrl),
 ("Finally, S P I, how it talks to the E S P thirty two. When a new sample is ready, D R D Y goes low. The E S P thirty two pulls chip select low, ticks the clock, and reads all eight channels from D out. D in is used to send commands and settings. At the default rate this happens two hundred and fifty times a second.", s_spi),
 ("Notice the separate power pins. A V D D and A V S S power the analog side at plus and minus two point five volts. D V D D and D ground power the digital side at three point three volts. Digital parts switch fast and make noise, so keeping them apart protects the microvolt signals.", s_power),
 ("Let's follow one sample. A ten microvolt alpha wave arrives at I N one P. The mux passes it through. The P G A multiplies it by twenty four, giving two hundred and forty microvolts. The A D C divides that by its step size, giving about four hundred and forty seven counts. D R D Y goes low, and the E S P thirty two reads the number.", s_journey),
 ("So the path to remember is: pin, mux, P G A, A D C, control, S P I, E S P thirty two. Try answering these five questions, and then we'll review them together.", s_end),
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
            p = 0.97
            fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
