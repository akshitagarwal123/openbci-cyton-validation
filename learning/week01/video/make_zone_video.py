"""Narrated explainer video: what a copper zone (GND pour) is, drawn on our week 1 practice board.
Needs: matplotlib, numpy, ffmpeg, macOS `say`.  Usage: python make_zone_video.py  ->  copper_zone_explained.mp4"""
import math, os, re, subprocess, textwrap, tempfile, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon

FPS, W, H = 20, 1280, 720
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "copper_zone_explained.mp4")
VOICE = "Samantha"
BG, FG, MU = "#0f1418", "#e8edf0", "#93a1aa"
BOARD, EDGE = "#11222e", "#e3d26f"
FCU, BCU, GREEN, ORANGE, RED, AMBER = "#d24b4b", "#4f86d0", "#6cc48a", "#f0a04b", "#ef6b5e", "#d9a441"

# Our practice board in mm (origin = top-left of the 41 x 45 mm outline, y goes down).
BW, BH = 41.0, 45.0
PADS0 = {  # name: (x, y, radius, net)
    "D1-A": (9.4, 6.4, 0.9, "LED"), "D1-K": (9.4, 9.0, 0.9, "GND"),
    "R1-1": (30.1, 6.5, 0.8, "LED"), "R1-2": (30.1, 16.6, 0.8, "VCC"),
    "BT-": (9.6, 29.5, 1.1, "GND"), "BT+": (30.2, 29.5, 1.1, "VCC"),
}
TRACKS = [("D1-A", "R1-1", "LED"), ("R1-2", "BT+", "VCC"), ("D1-K", "BT-", "GND")]
NETC = {"VCC": ORANGE, "GND": GREEN, "LED": AMBER}
CLR, EDGE_CLR, SPOKE = 0.5, 0.5, 0.25

RES = 0.1
XS = np.arange(-1.0, BW + 1.0, RES); YS = np.arange(-1.0, BH + 1.0, RES)
GX, GY = np.meshgrid(XS, YS)

def zone_mask(pads, thermals=True, GX=GX, GY=GY):
    m = (GX > EDGE_CLR) & (GX < BW - EDGE_CLR) & (GY > EDGE_CLR) & (GY < BH - EDGE_CLR)
    for x, y, r, net in pads.values():
        dx, dy = GX - x, GY - y; d = np.hypot(dx, dy)
        if net != "GND":
            m &= d > r + CLR
        elif thermals:
            ring = (d > r) & (d <= r + CLR)
            spoke = (np.abs(dx) < SPOKE) | (np.abs(dy) < SPOKE)
            m &= ~(ring & ~spoke)
    return m

def moved(dx):
    p = dict(PADS0)
    for k in ("R1-1", "R1-2"):
        x, y, r, n = p[k]; p[k] = (x + dx, y, r, n)
    return p

MASK = zone_mask(PADS0)
MASK_SOLID = zone_mask(PADS0, thermals=False)
FLOOD = np.hypot(GX - PADS0["BT-"][0], GY - PADS0["BT-"][1])
MOVE_DX = -6.0
MASK_MOVED = zone_mask(moved(MOVE_DX))

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

def board_ax(fig, rect, lim=(-3, BW + 3, BH + 3, -3)):
    ax = fig.add_axes(rect); ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3])
    ax.set_aspect("equal"); ax.axis("off"); ax.set_facecolor(BG)
    return ax

def draw_board(ax, pads=PADS0, zone=None, zone_alpha=0.8, tracks=True, labels=True, top_alpha=1.0, battery=True):
    ax.add_patch(Rectangle((0, 0), BW, BH, fc=BOARD, ec=EDGE, lw=2.5, zorder=1))
    if zone is not None:
        rgba = np.zeros(zone.shape + (4,)); rgba[zone] = matplotlib.colors.to_rgba(BCU, zone_alpha)
        ax.imshow(rgba, extent=(XS[0], XS[-1] + RES, YS[-1] + RES, YS[0]), interpolation="nearest", zorder=2)
    if battery:
        ax.add_patch(Circle((19.9, 29.5), 10.3, fc="none", ec="#cfd6db", lw=1.5, zorder=3, alpha=0.7))
        ax.text(19.9, 29.5, "BT1\n(coin cell)", color=MU, ha="center", va="center", fontsize=11, zorder=3)
    r1x = pads["R1-1"][0]
    ax.add_patch(Rectangle((r1x - 1.2, 8.5), 2.4, 6.0, fc="none", ec="#cfd6db", lw=1.5, zorder=3, alpha=0.7))
    ax.add_patch(Circle((9.4, 7.7), 3.0, fc="none", ec="#cfd6db", lw=1.5, zorder=3, alpha=0.7))
    if labels:
        ax.text(r1x + 2.0, 11.5, "R1", color=FG, fontsize=12, zorder=6); ax.text(13.0, 4.0, "D1 (LED)", color=FG, fontsize=12, zorder=6)
    if tracks:
        for a, b, net in TRACKS:
            (x0, y0, *_), (x1, y1, *_) = pads[a], pads[b]
            pts = [(x0, y0), (x1, y1)] if (x0 == x1 or y0 == y1) else [(x0, y0), (x0, y1), (x1, y1)]
            if a == "D1-A": pts = [(x0, y0), (x0, y1 - 0.0), (x1, y1)] if y0 != y1 else pts
            ax.plot(*zip(*pts), color=FCU, lw=3.2, alpha=top_alpha, zorder=4, solid_capstyle="round")
    for k, (x, y, r, net) in pads.items():
        ax.add_patch(Circle((x, y), r, fc="#c9a24a", ec="none", zorder=5))
        ax.add_patch(Circle((x, y), r * 0.45, fc="#0b0f12", ec="none", zorder=5))

def net_legend(fig):
    for i, (n, c) in enumerate([("GND", GREEN), ("VCC", ORANGE), ("LED (R1 → LED)", AMBER)]):
        fig.text(0.70, 0.74 - i * 0.06, "●  " + n, color=c, fontsize=17, weight="bold")

# ---------- scenes ----------
def s_title(fig, p, t):
    fig.text(0.5, 0.6, "Copper zones", color=FG, fontsize=44, ha="center", weight="bold")
    fig.text(0.5, 0.5, "a sheet of copper instead of a wire", color=MU, fontsize=24, ha="center")
    ax = board_ax(fig, [0.38, 0.17, 0.24, 0.28]); draw_board(ax, zone=MASK if p > 0.3 else None, labels=False)

def s_board(fig, p, t):
    title(fig, "Your practice board: 3 tracks on the top copper (F.Cu, red)")
    ax = board_ax(fig, [0.05, 0.14, 0.55, 0.74]); draw_board(ax)
    for k, (x, y, r, net) in PADS0.items():
        ax.add_patch(Circle((x, y), r + 0.9, fc="none", ec=NETC[net], lw=2.5, zorder=6))
    net_legend(fig)
    fig.text(0.70, 0.45, "Each colour is one net:\na group of pads that must\nbe connected together.", color=MU, fontsize=16)

def s_track_vs_zone(fig, p, t):
    title(fig, "A track is a road.  A zone is a whole car park.")
    ax1 = board_ax(fig, [0.03, 0.16, 0.45, 0.68]); draw_board(ax1, labels=False)
    for x, y in [(9.4, 9.0), (9.6, 29.5)]: ax1.add_patch(Circle((x, y), 2.2, fc="none", ec=GREEN, lw=2.5, zorder=6))
    fig.text(0.255, 0.86, "GND as one thin track", color=FG, fontsize=17, ha="center")
    ax2 = board_ax(fig, [0.52, 0.16, 0.45, 0.68])
    show = MASK & (FLOOD < ease(p * 1.4) * 60)
    draw_board(ax2, zone=show, labels=False, top_alpha=0.35)
    fig.text(0.745, 0.86, "GND as a copper zone (blue)", color=BCU, fontsize=17, ha="center", weight="bold")

def s_layers(fig, p, t):
    title(fig, "Side view: tracks on top, the GND zone on the bottom")
    ax = fig.add_axes([0.05, 0.16, 0.9, 0.7]); ax.set_xlim(0, 52); ax.set_ylim(-4, 9); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 41, 1.6, fc="#3c5a3a", ec="none")); ax.text(20.5, 0.8, "FR4 fibreglass (the board)", color=FG, ha="center", va="center", fontsize=14)
    pads = [(7.0, "GND"), (20.5, "LED"), (34.0, "VCC")]
    for x0, x1 in [(0.8, 6.5), (7.5, 13.5), (15.5, 20.0), (21.0, 27.0), (29.0, 33.5), (34.5, 40.2)]:
        ax.add_patch(Rectangle((x0, 1.6), x1 - x0, 0.35, fc=FCU, ec="none"))
    ax.text(41.3, 1.8, "F.Cu  (top, red)", color=FCU, fontsize=14, va="center")
    k = ease(p * 1.5)
    xs = [0.6]
    for x, net in pads:
        if net == "GND": continue
        xs += [x - 1.7, x + 1.7]
    xs.append(40.4)
    for i in range(0, len(xs), 2):
        a, b = xs[i], xs[i + 1]; b = a + (b - a) * k
        ax.add_patch(Rectangle((a, -0.35), max(0, b - a), 0.35, fc=BCU, ec="none"))
    ax.text(41.3, -0.2, "B.Cu  (bottom, blue)", color=BCU, fontsize=14, va="center")
    for x, net in pads:
        ax.add_patch(Rectangle((x - 0.5, -0.35), 1.0, 2.3, fc="#c9a24a", ec="none"))
        ax.add_patch(Rectangle((x - 0.15, -1.6), 0.3, 6.5, fc="#b8c2c8", ec="none"))
        c = NETC[net]; ax.text(x, 5.6, f"{net} leg", color=c, ha="center", fontsize=15, weight="bold")
        if p > 0.55:
            msg = "touches the zone ✓" if net == "GND" else "gap: zone\nkeeps away"
            ax.text(x, -2.0, msg, color=GREEN if net == "GND" else ORANGE, ha="center", va="top", fontsize=14, weight="bold")

def s_draw(fig, p, t):
    title(fig, "Drawing it: B.Cu layer → Add Filled Zone → click 4 corners")
    ax = board_ax(fig, [0.05, 0.14, 0.55, 0.74]); draw_board(ax, top_alpha=0.35)
    corners = [(-1.5, -1.5), (BW + 1.5, -1.5), (BW + 1.5, BH + 1.5), (-1.5, BH + 1.5)]
    n = min(4, int(p / 0.15) + 1) if p < 0.62 else 5
    pts = corners[:min(n, 4)] + ([corners[0]] if n == 5 else [])
    if len(pts) > 1: ax.plot(*zip(*pts), color=BCU, lw=2.5, ls="--", zorder=7)
    for c in corners[:min(n, 4)]: ax.plot(*c, "s", color=BCU, ms=10, zorder=7)
    box = FancyBboxPatch((0.66, 0.42), 0.29, 0.34, boxstyle="round,pad=0.01", transform=fig.transFigure, fc="#1b2329", ec=MU)
    fig.patches.append(box)
    fig.text(0.68, 0.72, "Copper Zone Properties", color=FG, fontsize=15, weight="bold")
    fig.text(0.68, 0.64, "Layer:   B.Cu", color=BCU, fontsize=15)
    fig.text(0.68, 0.57, "Net:      GND", color=GREEN, fontsize=15, weight="bold")
    fig.text(0.68, 0.48, "It's OK to draw past the edge:\nKiCad trims it to the outline.", color=MU, fontsize=12.5)
    if n == 5: fig.text(0.33, 0.9, "only an outline: no copper yet!", color=ORANGE, fontsize=16, ha="center", weight="bold")

def s_fill(fig, p, t):
    title(fig, "Press B (Fill All Zones): copper flows in and fills the outline")
    ax = board_ax(fig, [0.05, 0.14, 0.55, 0.74])
    show = MASK & (FLOOD < ease(p * 1.3) * 60)
    draw_board(ax, zone=show, top_alpha=0.45)
    rules = ["1. Joins pads on its own net (GND)", "2. Keeps a gap around other nets", "3. Stays inside the board edge",
             "4. Ignores the top tracks: different layer"]
    for i, r in enumerate(rules):
        if p > 0.35 + i * 0.13: fig.text(0.63, 0.72 - i * 0.08, r, color=FG, fontsize=16.5)

def zoom_pad(fig, rect, pad, mask, label, lab_col, heat=None):
    x, y, r, net = PADS0[pad]
    ax = board_ax(fig, rect, lim=(x - 4, x + 4, y + 4, y - 4))
    fx = np.arange(x - 4, x + 4, 0.02); fy = np.arange(y - 4, y + 4, 0.02); FX, FY = np.meshgrid(fx, fy)
    fine = zone_mask(PADS0, thermals=mask, GX=FX, GY=FY)
    rgba = np.zeros(fine.shape + (4,)); rgba[fine] = matplotlib.colors.to_rgba(BCU, 0.85)
    ax.imshow(rgba, extent=(fx[0], fx[-1] + 0.02, fy[-1] + 0.02, fy[0]), interpolation="nearest")
    col = "#c9a24a" if heat is None else matplotlib.colors.to_hex(np.array(matplotlib.colors.to_rgb("#c9a24a")) * (1 - heat) + np.array(matplotlib.colors.to_rgb("#ff5a1f")) * heat)
    ax.add_patch(Circle((x, y), r, fc=col, ec="none", zorder=5)); ax.add_patch(Circle((x, y), r * 0.45, fc="#0b0f12", zorder=5))
    ax.text(x, y - 4.6, label, color=lab_col, ha="center", fontsize=16, weight="bold")
    return ax

def s_clearance(fig, p, t):
    title(fig, "Up close: a gap around other nets, spokes to its own net")
    zoom_pad(fig, [0.05, 0.14, 0.42, 0.7], "BT+", True, "VCC pad: ring of empty board", ORANGE)
    zoom_pad(fig, [0.53, 0.14, 0.42, 0.7], "BT-", True, "GND pad: joined by 4 spokes", GREEN)
    if p > 0.5: fig.text(0.26, 0.17, "0.5 mm clearance → no short", color=FG, fontsize=15, ha="center")

def s_thermal(fig, p, t):
    title(fig, "Why spokes? Thermal relief: lets the pad get hot enough")
    heat_solid = min(1, p * 0.35); heat_spoke = min(1, p * 1.6)
    zoom_pad(fig, [0.05, 0.16, 0.42, 0.66], "BT-", False, "solid: heat drains away", RED, heat=heat_solid)
    zoom_pad(fig, [0.53, 0.16, 0.42, 0.66], "BT-", True, "spokes: pad heats up fast", GREEN, heat=heat_spoke)
    fig.text(0.26, 0.17, f"solder melts? {'yes' if heat_solid > 0.9 else 'not yet...'}", color=FG, fontsize=15, ha="center")
    fig.text(0.74, 0.17, f"solder melts? {'yes ✓' if heat_spoke > 0.9 else 'not yet...'}", color=FG, fontsize=15, ha="center")

def s_refill(fig, p, t):
    k = ease(p / 0.3)
    pads = moved(MOVE_DX * k)
    refilled = p > 0.68
    title(fig, "Press B to refill" if refilled else ("Moving R1... the zone does NOT move with it" if p < 0.35 else "DRC: short circuit!"))
    ax = board_ax(fig, [0.05, 0.14, 0.55, 0.74])
    draw_board(ax, pads=pads, zone=MASK_MOVED if refilled else MASK, top_alpha=0.5)
    if 0.35 < p <= 0.68:
        for kk in ("R1-1", "R1-2"):
            x, y, r, _ = pads[kk]; ax.plot(x, y, "x", color=RED, ms=26, mew=4, zorder=8)
        fig.text(0.63, 0.6, "R1's pads now sit on\nold GND copper\n→ VCC shorted to GND", color=RED, fontsize=18, weight="bold")
    if refilled:
        fig.text(0.63, 0.6, "The zone flows around\nthe new position.\nShort gone ✓", color=GREEN, fontsize=18, weight="bold")
        fig.text(0.63, 0.4, "DRC refills zones for you\n(the 'Refill all zones' box).", color=MU, fontsize=15)

def s_why(fig, p, t):
    title(fig, "Why bother? A wide road has less resistance")
    lines = [("Thin track: one narrow path back to the battery", FG),
             ("Zone: a huge, wide path, so lower resistance and inductance", FG),
             ("Every part gets a short way back to ground", FG),
             ("On BrainTech-8, a whole layer is GND: the ground plane", GREEN),
             ("Brain signals are microvolts: a solid ground keeps noise out", GREEN)]
    for i, (l, c) in enumerate(lines):
        if p > i * 0.17: fig.text(0.08, 0.76 - i * 0.1, "•  " + l, color=c, fontsize=21)

def s_end(fig, p, t):
    fig.text(0.5, 0.64, "Copper zone = a sheet of copper owned by one net", color=FG, fontsize=30, ha="center", weight="bold")
    fig.text(0.5, 0.53, "It joins its own net, avoids the others, and needs B to (re)fill.", color=MU, fontsize=21, ha="center")
    fig.text(0.5, 0.42, "Try it: B.Cu → Add Filled Zone → Net GND → B → Run DRC", color=BCU, fontsize=21, ha="center", weight="bold")

SCENES = [
 ("In this video: what a copper zone is, and why the KiCad tutorial adds one to the board.", s_title),
 ("Here is your practice board. Three red tracks on the top copper layer join the pads. Pads that must connect form a net. You have three nets: ground, V C C, and the wire from the resistor to the LED.", s_board),
 ("A track is like a narrow road between two pads. A copper zone is like a huge car park: a whole area of copper that belongs to one net. Here, the ground net becomes one big blue sheet that covers almost the whole board.", s_track_vs_zone),
 ("The tutorial puts this ground zone on the bottom copper layer. Your parts are through-hole, so each leg passes through both layers. The ground legs touch the zone. The other legs get a small empty ring, so they don't touch it.", s_layers),
 ("To draw it, choose the B dot C U layer, click Add Filled Zone, and click the first corner. In the dialog, pick the net G N D. Then click the other three corners, and double-click to finish. You can draw past the board edge. But notice: at this point it's only an outline. There is no copper yet.", s_draw),
 ("Now press B, for Fill All Zones. Copper flows into the outline. It follows four rules. It joins pads on its own net. It keeps a gap around every other net. It stays inside the board edge. And it ignores the red tracks, because they are on a different layer.", s_fill),
 ("Zoom in. Around the V C C pad there is a ring of empty board, half a millimetre wide, so there is no short circuit. The ground pad is connected, but only by four thin spokes.", s_clearance),
 ("Why spokes? Copper spreads heat very well. With a solid connection, the whole sheet pulls heat away from your soldering iron, and the solder struggles to melt. With four thin spokes, the heat stays in the pad, so it heats up fast and solders easily. This is called a thermal relief.", s_thermal),
 ("One catch: zones don't update by themselves. If you move the resistor, the old copper stays where it was, and now the resistor's pads sit on ground copper. That's a short circuit, and D R C flags it. Press B to refill, and the zone flows around the new position. D R C also refills zones for you before it checks.", s_refill),
 ("Why bother? A wide sheet of copper has much lower resistance than a thin track, and every part gets a short path back to ground. On your EEG board, a whole layer will be ground: the ground plane. Brain signals are only microvolts, so a solid ground is one of the best ways to keep noise out.", s_why),
 ("To sum up: a copper zone is a sheet of copper owned by one net. It joins its own net, avoids the others, and needs B to fill and refill. Try it on your practice board, then run D R C.", s_end),
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
    if len(sys.argv) > 1 and sys.argv[1] == "--stills":   # quick preview: one frame per scene
        d = sys.argv[2] if len(sys.argv) > 2 else "."
        for i, (text, draw) in enumerate(SCENES):
            for p in (0.5, 0.95):
                fig = new_fig(); draw(fig, p, p * 10); caption(fig, text, p); fig.savefig(os.path.join(d, f"scene{i:02d}_{int(p*100)}.png"), facecolor=BG); plt.close(fig)
    else:
        main()
