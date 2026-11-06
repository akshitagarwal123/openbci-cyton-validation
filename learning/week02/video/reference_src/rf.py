"""ADS1299 internal reference (datasheet 9.3.1.3.4): animated explainer."""
import itertools, json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from narr import NARR, TITLES

FPS, W, H, S = 15, 1280, 720, 2
LEAD, TAIL = 0.4, 0.9
BG = (13, 19, 17); FG = (232, 239, 235); MUTED = (147, 165, 157); YEL = (240, 224, 74); CY = (79, 209, 255)
PUR = (167, 123, 255); COR = (255, 138, 92); GRN = (46, 196, 160); BLU = (122, 162, 255); GRY = (60, 74, 68)
TM = json.load(open(f'{D}/timing.json')) if os.path.exists(f'{D}/timing.json') else None
SENTS = [re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', t.strip()) for t in NARR]

_f = {}
def font(size, bold=False):
    if (size, bold) not in _f:
        _f[(size, bold)] = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf', int(size * S))
    return _f[(size, bold)]
al = lambda c, a: tuple(c) + (int(255 * max(0.0, min(1.0, a))),)
ramp = lambda t, t0, d=0.6: max(0.0, min(1.0, (t - t0) / d))
ease = lambda x: x * x * (3 - 2 * x)

class Cv:
    def __init__(self):
        self.im = Image.new('RGB', (W * S, H * S), BG); self.d = ImageDraw.Draw(self.im, 'RGBA')
    def line(self, pts, col, w=3): self.d.line([(x * S, y * S) for x, y in pts], fill=col, width=max(1, int(w * S)), joint='curve')
    def circ(self, x, y, r, fill=None, outline=None, w=2): self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill, outline=outline, width=int(w * S))
    def rect(self, box, fill=None, outline=None, r=10, w=2): self.d.rounded_rectangle([v * S for v in box], r * S, fill=fill, outline=outline, width=int(w * S))
    def poly(self, pts, fill=None, outline=None, w=3):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)
        if outline: self.d.line([(x * S, y * S) for x, y in pts + [pts[0]]], fill=outline, width=int(w * S), joint='curve')
    def text(self, xy, s, size=22, col=FG, bold=False, anchor='la'): self.d.text((xy[0] * S, xy[1] * S), s, font=font(size, bold), fill=col, anchor=anchor)
    def tw(self, s, size, bold=False): return self.d.textlength(s, font=font(size, bold)) / S
    def out(self): return self.im.resize((W, H), Image.LANCZOS)

def plen(p): return [0] + list(itertools.accumulate(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)))
def at(p, u):
    L = plen(p); s = (u % 1) * L[-1]
    for i in range(len(p) - 1):
        if s <= L[i + 1]:
            f = (s - L[i]) / max(1e-9, L[i + 1] - L[i]); return (p[i][0] + (p[i + 1][0] - p[i][0]) * f, p[i][1] + (p[i + 1][1] - p[i][1]) * f)
    return p[-1]
def dots(cv, p, t, col, a=1.0, n=4, speed=0.35, r=6):
    for k in range(n):
        x, y = at(p, t * speed + k / n); cv.circ(x, y, r, fill=al(col, a))
def arrow(cv, x0, y0, x1, y1, col, w=3):
    cv.line([(x0, y0), (x1, y1)], col, w); ang = math.atan2(y1 - y0, x1 - x0)
    for s in (-1, 1): cv.line([(x1, y1), (x1 - 14 * math.cos(ang + s * 0.45), y1 - 14 * math.sin(ang + s * 0.45))], col, w)
def zig(cv, x1, x2, y, col, a=1.0, label='R', lcol=None):
    n = 6; seg = (x2 - x1 - 40) / n
    pts = [(x1, y), (x1 + 20, y)] + [(x1 + 20 + seg * (k + 0.5), y + (12 if k % 2 else -12)) for k in range(n)] + [(x2 - 20, y), (x2, y)]
    cv.line(pts, al(col, a), 3); cv.text(((x1 + x2) / 2, y - 30), label, 20, al(lcol or MUTED, a), True, 'mm')
def source(cv, x, y, val, label, a=1.0, col=BLU):
    cv.circ(x, y, 40, outline=al(col, a), w=3); cv.text((x, y), val, 26, al(FG, a), True, 'mm'); cv.text((x, y + 62), label, 18, al(MUTED, a), False, 'mm')
def switch(cv, x, y, opened, a=1.0, col=FG):
    th = math.radians(34 * ease(opened)); L = 50
    cv.circ(x, y, 4, fill=al(col, a)); cv.circ(x + L, y, 4, fill=al(col, a)); cv.line([(x, y), (x + L * math.cos(th), y - L * math.sin(th))], al(col, a), 3)
def panel(cv, box, a=1.0): cv.rect(box, fill=al((10, 15, 13), 0.86 * a), outline=al(GRY, a), r=14)
def wave(cv, x0, x1, yc, amp, fn, col, tau0, span=0.1, w=3, a=1.0, n=240):
    pts = [(x0 + (x1 - x0) * k / n, yc - amp * fn(tau0 + span * k / n)) for k in range(n + 1)]; cv.line(pts, al(col, a), w)
HUM = lambda tau, ph=0.0, amp=1.0: amp * math.sin(2 * math.pi * 50 * tau + ph)
EEG = lambda tau: 1.0 * (0.8 * math.sin(2 * math.pi * 9 * tau + 0.5) + 0.5 * math.sin(2 * math.pi * 21 * tau + 2.0))

# ------------------------------------------------------------------ scenes (t = video seconds, T(i) = start of sentence i)
def box(cv, x0, y0, x1, y1, a, col=GRY, fill=None, r=12, w=2): cv.rect((x0, y0, x1, y1), fill=fill, outline=al(col, a), r=r, w=w)
def capsym(cv, x, y, a, col=FG, vertical=True, w=44):
    if vertical: cv.line([(x - w / 2, y - 6), (x + w / 2, y - 6)], al(col, a), 4); cv.line([(x - w / 2, y + 6), (x + w / 2, y + 6)], al(col, a), 4)
    else: cv.line([(x - 6, y - w / 2), (x - 6, y + w / 2)], al(col, a), 4); cv.line([(x + 6, y - w / 2), (x + 6, y + w / 2)], al(col, a), 4)

def sc1(cv, t, T, R):
    a = R(1); wob = ease(ramp(t, T(2), 0.8)); L = 620 * (1 + 0.05 * wob * math.sin(t * 5))
    cv.text((640, 120), 'Every sample is a comparison', 38, al(FG, R(0)), True, 'mm')
    if a > 0:
        cv.text((150, 190), 'the ruler = the reference voltage', 24, al(YEL, a), True, 'lm')
        cv.rect((150, 215, 150 + L, 265), fill=al(FG, a * 0.12), outline=al(FG, a), r=6)
        for k in range(21): cv.line([(150 + L * k / 20, 215), (150 + L * k / 20, 238 if k % 5 else 252)], al(FG, a), 2)
        cv.rect((150, 330, 460, 365), fill=al(CY, a * 0.7), r=6); cv.text((150, 392), 'your signal (perfectly steady)', 22, al(CY, a), True, 'lm')
        cv.line([(460, 330), (460, 265)], al(CY, a), 2)
        rd = 310 / L * 20; bad = wob > 0.1
        cv.text((840, 300), 'reads as', 22, al(MUTED, a), False, 'lm'); cv.text((840, 345), f'{rd:.1f} ticks', 44, al(COR if bad else GRN, a), True, 'lm')
        if bad: cv.text((840, 395), 'it should never change!', 22, al(COR, wob), True, 'lm')
    if t >= T(3): cv.text((640, 480), 'brain signal: only microvolts  →  the ruler must be extremely steady', 28, al(FG, R(3)), True, 'mm')
    if t >= T(4): b = R(4); box(cv, 150, 520, 1130, 585, b, YEL, r=14, w=3); cv.text((640, 553), 'datasheet 9.3.1.3.4: how the chip makes its ruler, and how to keep it steady', 24, al(YEL, b), True, 'mm')

def sc2(cv, t, T, R):
    a = R(0); cv.text((640, 255), 'the range the chip can measure', 24, al(MUTED, a), False, 'mm')
    cv.line([(120, 300), (1160, 300)], al(FG, a), 4)
    for k in range(21): cv.line([(120 + 52 * k, 300), (120 + 52 * k, 316 if k % 5 else 330)], al(FG, a), 2)
    cv.text((640, 352), '0', 22, al(MUTED, a), True, 'mm')
    if t >= T(1): cv.text((640, 130), 'full scale  =  ± VREF ÷ gain', 44, al(YEL, R(1)), True, 'mm')
    if t >= T(2):
        b = R(2); cv.text((640, 195), '= ± 4.5 V ÷ 24  =  ± 187.5 mV', 40, al(FG, b), True, 'mm'); cv.text((120, 352), '−187.5 mV', 24, al(COR, b), True, 'lm'); cv.text((1160, 352), '+187.5 mV', 24, al(COR, b), True, 'rm')
    if t >= T(3):
        c = R(3); box(cv, 430, 400, 850, 490, c, CY, r=12, w=2); pts = []
        for k in range(9): pts += [(445 + k * 45, 470 - k * 8), (445 + (k + 1) * 45, 470 - k * 8)]
        cv.line(pts, al(CY, c), 3); cv.text((640, 522), '2^24 = 16,777,216 steps', 28, al(FG, c), True, 'mm'); cv.text((640, 558), 'one step ≈ 0.022 µV', 28, al(YEL, c), True, 'mm')

def sc3(cv, t, T, R):
    a = R(0)
    cv.rect((240, 110, 900, 400), outline=al(GRY, a), r=16); cv.text((570, 135), 'inside the ADS1299', 20, al(MUTED, a), True, 'mm')
    box(cv, 275, 200, 405, 270, a, YEL, r=10, w=3); cv.text((340, 235), 'bandgap', 24, al(YEL, a), True, 'mm'); arrow(cv, 407, 235, 446, 235, al(FG, a), 3)
    cv.poly([(450, 195), (450, 275), (550, 235)], outline=al(CY, a)); cv.text((470, 235), 'buffer', 18, al(CY, a), False, 'lm')
    cv.line([(550, 235), (640, 235)], al(FG, a), 3); cv.line([(640, 235), (640, 400)], al(BLU, a), 3); cv.line([(640, 235), (700, 235)], al(FG, a), 3); arrow(cv, 700, 235, 880, 235, al(FG, a), 3)
    cv.text((790, 205), '4.5 V ruler', 22, al(YEL, a), True, 'mm'); cv.text((790, 265), 'to the ADC', 18, al(MUTED, a), False, 'mm')
    if t >= T(1):
        b = R(1)
        for k, s in enumerate(('R1 = 9.8 kΩ', 'R2 = 13.4 kΩ', 'R3 = 36.85 kΩ')): cv.text((420, 318 + k * 24), s, 20, al(FG, b), False, 'lm')
        cv.text((420, 292), 'trimmed at the factory', 18, al(MUTED, b), False, 'lm')
    for x, nm in ((320, 'VCAP1'), (640, 'VREFP'), (780, 'VREFN')): cv.rect((x - 6, 400, x + 6, 412), fill=al(FG, a), r=2); cv.text((x, 382), nm, 16, al(FG, a), True, 'mm')
    cv.line([(320, 412), (320, 445)], al(FG, a), 3)
    if t >= T(2):
        c = R(2); cv.line([(780, 412), (780, 520)], al(YEL, c), 4); cv.line([(300, 520), (780, 520)], al(YEL, c), 4); cv.text((290, 520), 'AVSS', 22, al(YEL, c), True, 'rm'); cv.text((800, 520), 'VREFN tied to AVSS', 22, al(YEL, c), True, 'lm')
    if t >= T(3):
        d = R(3); capsym(cv, 320, 460, d, FG); cv.line([(320, 466), (320, 520)], al(FG, d), 3); cv.text((290, 460), '100 µF', 22, al(YEL, d), True, 'rm')
        cv.line([(640, 412), (640, 468)], al(FG, d), 3); cv.line([(780, 468), (780, 520)], al(FG, d), 3) if False else None; cv.line([(640, 468), (704, 468)], al(FG, d), 3); capsym(cv, 710, 468, d, FG, vertical=False); cv.line([(716, 468), (780, 468)], al(FG, d), 3); cv.line([(780, 412), (780, 468)], al(FG, d), 3)
        cv.text((710, 440), '10 µF', 22, al(YEL, d), True, 'mm')
    if t >= T(4): e = R(4); box(cv, 940, 140, 1250, 290, e, GRY, fill=al((10, 15, 13), 0.86 * e)); cv.text((1095, 175), 'external option', 22, al(MUTED, e), True, 'mm'); cv.text((1095, 215), 'REF5025 chip', 24, al(FG, e), True, 'mm'); cv.text((1095, 255), 'not needed here', 20, al(MUTED, e), False, 'mm')

def sc4(cv, t, T, R):
    Y = lambda v: 330 - v * 76; a = R(0)
    cv.text((640, 100), 'your board: ±2.5 V analog supplies', 26, al(MUTED, a), True, 'mm')
    cv.line([(250, Y(0)), (470, Y(0))], al(MUTED, 1), 2) if t >= T(0) else None
    cv.text((490, Y(0)), '0 V (ground)', 22, al(MUTED, a), False, 'lm')
    cv.line([(250, Y(-2.5)), (470, Y(-2.5))], al(BLU, a), 5); cv.text((490, Y(-2.5)), 'AVSS  =  −2.5 V', 26, al(BLU, a), True, 'lm')
    if t >= T(1):
        b = R(1); cv.line([(250, Y(2.0)), (470, Y(2.0))], al(YEL, b), 5); cv.text((490, Y(2.0)), 'VREFP  =  +2.0 V', 26, al(YEL, b), True, 'lm'); cv.text((490, Y(-2.5) + 30), 'VREFN  =  AVSS', 22, al(BLU, b), False, 'lm')
        arrow(cv, 200, Y(2.0), 200, Y(-2.5), al(YEL, b), 4); arrow(cv, 200, Y(-2.5), 200, Y(2.0), al(YEL, b), 4); cv.text((178, 350), '4.5 V', 34, al(YEL, b), True, 'rm')
    if t >= T(2): c = R(2); cv.line([(250, Y(2.5)), (470, Y(2.5))], al(GRN, c), 5); cv.text((490, Y(2.5)), 'AVDD  =  +2.5 V', 26, al(GRN, c), True, 'lm')
    panel(cv, (830, 120, 1250, 540), R(1))
    if t >= T(1): b = R(1); cv.text((850, 190), 'VREFP = AVSS + 4.5 V', 26, al(FG, b), True, 'lm'); cv.text((850, 235), '= −2.5 + 4.5 = +2.0 V', 28, al(YEL, b), True, 'lm')
    if t >= T(2): cv.text((850, 290), 'VREFP +2.0 V  <  AVDD +2.5 V  ✓', 22, al(GRN, R(2)), True, 'lm')
    if t >= T(3): d = R(3); cv.text((850, 330), 'single supply instead:', 22, al(MUTED, d), True, 'lm'); cv.text((850, 375), 'AVSS = 0 V', 26, al(FG, d), True, 'lm'); cv.text((850, 420), '→ VREFP = 4.5 V', 30, al(YEL, d), True, 'lm')

NOISE = [(2, 0.30, 0.0), (4, 0.22, 1.0), (15, 0.45, 2.0), (33, 0.40, 0.5), (61, 0.35, 1.7), (110, 0.30, 2.6), (170, 0.28, 0.9)]
def noisy(tau): return sum(a * math.sin(2 * math.pi * f * tau + p) for f, a, p in NOISE)
def clean(tau, fc=5.0): return sum(a / math.sqrt(1 + (f / fc) ** 2) * math.sin(2 * math.pi * f * tau + p - math.atan(f / fc)) for f, a, p in NOISE)
def sc5(cv, t, T, R):
    a = R(0); tau0 = t * 0.04
    box(cv, 70, 150, 410, 380, a, GRY, r=14); cv.text((240, 178), 'reference (noisy)', 20, al(COR, a), True, 'mm'); cv.line([(85, 275), (395, 275)], al(MUTED, a * 0.6), 1)
    wave(cv, 85, 395, 275, 40, noisy, COR, tau0, span=0.3, a=a, w=2, n=900)
    if t >= T(1):
        b = R(1); cv.line([(412, 262), (470, 262)], al(FG, b), 3); zig(cv, 470, 600, 262, FG, b, 'R inside the chip', MUTED); cv.line([(600, 262), (680, 262)], al(FG, b), 3)
        cv.circ(640, 262, 4, fill=al(FG, b)) if False else None
        cv.line([(640, 262), (640, 314)], al(FG, b), 3); capsym(cv, 640, 320, b, FG); cv.line([(640, 326), (640, 370)], al(FG, b), 3); cv.line([(620, 370), (660, 370)], al(FG, b), 3); cv.line([(628, 378), (652, 378)], al(FG, b), 3)
        cv.text((672, 320), 'C: yours', 20, al(YEL, b), True, 'lm'); arrow(cv, 680, 262, 790, 262, al(FG, b), 3)
        box(cv, 800, 150, 1140, 380, b, GRY, r=14); cv.text((970, 178), 'reference (clean)', 20, al(GRN, b), True, 'mm'); cv.line([(815, 275), (1125, 275)], al(MUTED, b * 0.6), 1)
        wave(cv, 815, 1125, 275, 40, clean, GRN, tau0, span=0.3, a=b, w=4, n=900)
        cv.text((640, 420), 'a slow low-pass filter', 24, al(CY, b), True, 'mm')
    if t >= T(2): c = R(2); cv.text((640, 450), 'bandwidth under 10 Hz', 40, al(YEL, c), True, 'mm'); cv.text((640, 495), 'datasheet: for high-end EEG, so the reference noise does not dominate', 20, al(MUTED, c), False, 'mm')
    if t >= T(3): cv.text((640, 548), 'big capacitors  =  a slow filter', 28, al(FG, R(3)), True, 'mm')

def sc6(cv, t, T, R):
    a = R(0); tau0 = t * 0.03; cv.text((640, 120), 'VCAP1  ·  datasheet page 70', 30, al(YEL, a), True, 'mm')
    b = R(1)
    if b > 0:
        dx = 3 * math.sin(t * 40) if t < T(3) else 0
        cv.line([(300, 250), (300, 290)], al(FG, b), 3); cv.line([(300 + dx - 50, 296), (300 + dx + 50, 296)], al(FG, b), 6); cv.line([(300 + dx - 50, 316), (300 + dx + 50, 316)], al(FG, b), 6); cv.line([(300, 322), (300, 362)], al(FG, b), 3)
        cv.text((300, 405), 'X7R / X5R ceramic', 22, al(COR, b), True, 'mm'); cv.text((300, 435), '(piezoelectric)', 18, al(MUTED, b), False, 'mm')
        for k in range(3): cv.line([(215 - k * 10, 290 + k * 14), (215 - k * 10, 330 - k * 8)], al(MUTED, b * (0.4 + 0.2 * math.sin(t * 20 + k))), 3)
        cv.text((140, 250), 'tap / shake', 20, al(MUTED, b), False, 'mm')
        wave(cv, 400, 760, 306, 38, lambda tau: noisy(tau * 4) * 0.6, COR, tau0, span=0.3, a=b, w=3, n=500); cv.text((580, 250), 'noise voltage', 20, al(COR, b), True, 'mm')
    if t >= T(2):
        c = R(2); arrow(cv, 770, 306, 830, 306, al(COR, c), 3); box(cv, 840, 250, 1230, 360, c, COR, r=12, w=3); cv.text((1035, 285), 'into VCAP1', 24, al(COR, c), True, 'mm'); cv.text((1035, 325), 'then into every sample', 22, al(FG, c), False, 'mm')
    if t >= T(3):
        d = R(3); box(cv, 330, 480, 650, 545, d, GRN, r=12, w=3); cv.text((490, 512), 'C0G or tantalum: quiet', 24, al(GRN, d), True, 'mm'); box(cv, 690, 480, 1070, 545, d, COR, r=12, w=2); cv.text((880, 512), 'X7R / X5R: noisy when shaken', 22, al(COR, d), True, 'mm')
    if t >= T(4): e = R(4); cv.text((640, 585), 'Cyton: X5R ceramic   ·   your board: your choice', 24, al(YEL, e), True, 'mm')

def sc7(cv, t, T, R):
    names = ['PD_REFBUF', '1', '1', 'BIAS_MEAS', 'BIASREF_INT', 'PD_BIAS', 'LOFF_SENS', 'STAT']
    def row(y, bits, a, hi):
        for i, b in enumerate(bits):
            x0 = 150 + 100 * i; col = hi.get(i, GRY)
            cv.rect((x0, y - 28, x0 + 92, y + 28), fill=al(col, a * 0.35) if (b == '1' and i in hi) else None, outline=al(col, a), r=8, w=3 if i in hi else 2)
            cv.text((x0 + 46, y), b, 32, al(col if i in hi else FG, a), True, 'mm'); cv.text((x0 + 46, y - 46), str(7 - i), 16, al(MUTED, a), False, 'mm'); cv.text((x0 + 46, y + 44), names[i], 13, al(MUTED, a), False, 'mm')
    cv.text((640, 110), 'CONFIG3 register', 34, al(FG, R(0)), True, 'mm')
    if t >= T(1):
        a = R(1); cv.text((150, 158), 'after power-up: 60h', 22, al(MUTED, a), True, 'lm'); row(250, '01100000', a, {0: COR} if t >= T(2) else {})
    if t >= T(2): b = R(2); cv.text((960, 235), 'PD_REFBUF = 0', 26, al(COR, b), True, 'lm'); cv.text((960, 270), 'internal reference OFF', 22, al(COR, b), False, 'lm')
    if t >= T(3):
        c = R(3); cv.text((150, 345), 'the Cyton writes EC', 22, al(YEL, c), True, 'lm'); hi = {0: GRN}
        if t >= T(5): hi = {0: GRN, 4: YEL, 5: YEL}
        row(440, '11101100', c, hi)
    if t >= T(4): d = R(4); cv.text((960, 425), 'PD_REFBUF = 1', 26, al(GRN, d), True, 'lm'); cv.text((960, 460), 'internal reference ON', 22, al(GRN, d), False, 'lm'); cv.text((960, 495), 'both chips (with a Daisy)', 18, al(MUTED, d), False, 'lm')
    if t >= T(5): cv.text((150, 540), 'bit 3: bias reference = (AVDD + AVSS) ÷ 2    ·    bit 2: bias buffer on', 22, al(YEL, R(5)), True, 'lm')

def sc8(cv, t, T, R):
    a = R(0); X0, X1, Y0, Y1 = 120, 1160, 170, 360
    cv.line([(X0, Y1), (X1, Y1)], al(FG, a), 3); cv.line([(X0, Y0), (X0, Y1)], al(FG, a), 3); cv.text((X0 - 10, Y0), 'VCAP1', 20, al(MUTED, a), True, 'rm'); cv.text((X1, Y1 + 28), 'time →', 20, al(MUTED, a), False, 'rm')
    for x, s in ((200, 'supplies stable'), (330, 'clock starts')): cv.line([(x, Y0 + 40), (x, Y1)], al(MUTED, a), 2); cv.text((x, Y0 + 25), s, 18, al(FG, a), True, 'mm')
    if t >= T(1):
        p = ease(ramp(t, T(1), 3.5)); xr = 330 + p * 810; pts = []
        for x in range(330, int(xr) + 1, 6): pts.append((x, Y1 - (Y1 - Y0 - 60) * (1 - math.exp(-(x - 330) / 130))))
        if len(pts) > 1: cv.line(pts, al(CY, 1), 4)
        cv.text((800, 305), 'charges slowly (big capacitor)', 20, al(CY, ramp(t, T(1), 0.8)), False, 'lm')
    if t >= T(2):
        b = R(2); yth = Y1 - (Y1 - Y0 - 60) * 0.8; cv.line([(X0, yth), (X1, yth)], al(COR, b * 0.8), 2); cv.text((X0 + 8, yth - 14), '1.1 V', 20, al(COR, b), True, 'lm')
        cv.rect((605, 400, 645, 440), fill=al(COR, b), r=6); cv.text((625, 465), 'RESET', 20, al(COR, b), True, 'mm')
        cv.text((640, 520), 'wait: the power-up delay, or until VCAP1 > 1.1 V,', 24, al(FG, b), True, 'mm'); cv.text((640, 552), 'whichever is longer', 24, al(YEL, b), True, 'mm')
    if t >= T(3): c = R(3); cv.rect((690, 400, 1110, 440), fill=al(GRN, c * 0.35), outline=al(GRN, c), r=8, w=2); cv.text((900, 420), 'program the registers (CONFIG3 …)', 20, al(GRN, c), True, 'mm')

def sc9(cv, t, T, R):
    cv.text((640, 110), 'To sum up', 50, al(FG, R(0)), True, 'mm')
    items = [('1', '4.5 V above AVSS: the ruler for every sample'), ('2', 'VREFN → AVSS  ·  VREFP–VREFN ≥ 10 µF  ·  VCAP1 → AVSS 100 µF'), ('3', 'Choose the VCAP1 capacitor with vibration in mind'), ('4', 'Firmware: wait for VCAP1, reset, then set PD_REFBUF = 1')]
    for k, (n, s) in enumerate(items):
        a = R(k + 1); y = 220 + k * 95; cv.circ(160, y, 28, outline=al(YEL, a), w=3); cv.text((160, y), n, 30, al(YEL, a), True, 'mm'); cv.text((220, y), s, 30, al(FG, a), False, 'lm')

SC = [sc1, sc2, sc3, sc4, sc5, sc6, sc7, sc8, sc9]

def info(i):
    tm = TM[i]; dur = LEAD + tm['audio'] + TAIL
    return dur, [LEAD + s for s in tm['starts']]
def wrap(cv, text, size, maxw):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        tr = (cur + ' ' + w_).strip()
        if cv.tw(tr, size) <= maxw: cur = tr
        else: lines.append(cur); cur = w_
    lines.append(cur); return lines
def frame(i, f):
    dur, starts = info(i); t = f / FPS
    T = lambda k: starts[k] if k < len(starts) else 1e9
    R = lambda k, d=0.6: ramp(t, T(k), d)
    cv = Cv(); title = f'{i + 1}/9  {TITLES[i]}'
    cv.rect((18, 14, 18 + cv.tw(title, 24, True) + 36, 58), fill=(13, 19, 17, 225), r=10); cv.text((36, 36), title, 24, FG, True, 'lm'); cv.text((36, 36), f'{i + 1}/9', 24, YEL, True, 'lm')
    SC[i](cv, t, T, R)
    j = max([k for k in range(len(starts)) if starts[k] <= t + 0.02] or [-1])
    if j >= 0:
        lines = wrap(cv, SENTS[i][j], 27, 1080); h = 22 + 36 * len(lines)
        cv.rect((90, 705 - h, W - 90, 702), fill=(8, 12, 11, 225), r=12)
        for k, ln in enumerate(lines): cv.text((W / 2, 705 - h + 18 + k * 36 + 14), ln, 27, FG, False, 'mm')
    return cv.out()

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'still':
        i, fr = int(sys.argv[2]), [float(x) for x in sys.argv[3:]]
        ims = [frame(i, int(x * FPS)).resize((640, 360)) for x in fr]
        sheet = Image.new('RGB', (1280, 360 * ((len(ims) + 1) // 2)))
        for k, im in enumerate(ims): sheet.paste(im, ((k % 2) * 640, (k // 2) * 360))
        sheet.save(f'{D}/still_{i + 1}.jpg')
    elif cmd == 'render':
        os.makedirs(f'{D}/out', exist_ok=True)
        enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', f'{D}/out/v.mp4'], stdin=subprocess.PIPE)
        parts = []
        for i in range(9):
            dur, _ = info(i); n = round(dur * FPS)
            for f in range(n): frame(i, f).save(enc.stdin, 'JPEG', quality=92)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/audio/s{i}.mp3', '-af', f'adelay={int(LEAD * 1000)}:all=1,apad=whole_dur={n / FPS}', '-t', str(n / FPS), '-ar', '44100', '-ac', '2', f'{D}/out/a{i}.wav'], check=True)
            parts.append(f"file '{D}/out/a{i}.wav'"); print('scene', i + 1, 'done', flush=True)
        enc.stdin.close(); enc.wait(); open(f'{D}/out/a.txt', 'w').write('\n'.join(parts))
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{D}/out/a.txt', '-c', 'pcm_s16le', f'{D}/out/a.wav'], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/out/v.mp4', '-i', f'{D}/out/a.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{D}/out/reference_explained.mp4'], check=True)
        print('DONE')
