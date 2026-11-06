"""How ADS1299 lead-off (electrode-off) detection works: animated explainer (PIL frames + narration timing)."""
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
def sq(x): return 1.0 if x >= 0 else -1.0
def softsq(x, k=6): return math.tanh(k * x)
def box(cv, x0, y0, x1, y1, a, col=GRY, fill=None, r=12, w=2): cv.rect((x0, y0, x1, y1), fill=fill, outline=al(col, a), r=r, w=w)
def gauge(cv, x, y0, y1, level, col, a, thr=False):
    cv.rect((x - 32, y0, x + 32, y1), outline=al(GRY, a), r=8)
    h = (y1 - y0 - 8) * max(0.0, min(1.0, level))
    cv.d.rectangle([(x - 27) * S, (y1 - 4 - h) * S, (x + 27) * S, (y1 - 4) * S], fill=al(col, a))
    if thr:
        yt = y1 - 4 - (y1 - y0 - 8) * 0.95
        cv.line([(x - 55, yt), (x + 55, yt)], al(COR, a), 2); cv.text((x + 62, yt), '95%', 18, al(COR, a), True, 'lm')
    cv.text((x - 42, y0 + 6), '+ supply', 16, al(MUTED, a), False, 'rm'); cv.text((x - 42, y1 - 8), '− supply', 16, al(MUTED, a), False, 'rm')

def sc1(cv, t, T, R):
    a = R(0); cx, cy, r = 300, 340, 150; off = ease(ramp(t, T(0) + 1.2, 1.2))
    cv.circ(cx, cy, r, outline=al(MUTED, a), w=3); cv.text((cx, cy + 50), 'head', 22, al(MUTED, a), False, 'mm')
    pos = [(cx - 95, cy - 70), (cx, cy - 115), (cx + 95, cy - 70), (cx + 115, cy + 10)]
    for k, (x, y) in enumerate(pos):
        bad = k == 2; ex, ey = (x + off * 85, y - off * 70) if bad else (x, y); col = COR if (bad and off > 0.4) else GRN
        if bad and off > 0: cv.line([(x, y), (ex, ey)], al(COR, a * 0.6), 2)
        cv.circ(ex, ey, 17, fill=al(col, a)); cv.text((ex, ey), str(k + 1), 18, al(BG, a), True, 'mm')
    tau0 = t * 0.05
    for k in range(4):
        yc = 170 + k * 100; bad = k == 2; amp = (0.12 + 0.88 * off) if bad else 0.12; col = COR if (bad and off > 0.4) else GRN
        cv.text((600, yc), f'channel {k + 1}', 20, al(MUTED, a), False, 'lm')
        wave(cv, 730, 1200, yc, 34, lambda tau, amp=amp, k=k: amp * (math.sin(2 * math.pi * 50 * tau + k) + 0.6 * math.sin(2 * math.pi * 13 * tau + 2 * k)), col, tau0, a=a)
    if T(1) <= t < T(2):
        b = R(1); seg = (T(2) - T(1)) / 4; k = min(3, int((t - T(1)) / seg)); x, y = pos[k]
        if k == 2: x, y = x + off * 85, y - off * 70
        cv.circ(x, y, 30 + 4 * math.sin(t * 8), outline=al(YEL, b), w=3); cv.text((cx, cy + 110), f'testing electrode {k + 1}…', 22, al(YEL, b), True, 'mm')
    if t >= T(2):
        b = R(2); box(cv, 150, 520, 1130, 590, b, YEL, r=14, w=3)
        cv.text((640, 555), 'lead-off detection  =  electrode-off detection', 32, al(YEL, b), True, 'mm')

def sc2(cv, t, T, R):
    a = R(0); cv.circ(150, 330, 42, outline=al(CY, a), w=3); arrow(cv, 168, 330, 132, 330, al(CY, a), 3)
    cv.text((150, 405), 'current source', 18, al(MUTED, a), False, 'mm'); cv.line([(192, 330), (300, 330)], al(FG, a), 3); cv.line([(470, 330), (570, 330)], al(FG, a), 3)
    cv.circ(620, 330, 50, outline=al(BLU, a), w=3); cv.text((620, 330), 'body', 22, al(FG, a), True, 'mm')
    z1, z2 = T(3), T(4); half = z2 + (T(5) - z2) * 0.5
    zl, vt, vc = ('Z', '', MUTED)
    if t >= z1: zl, vt, vc = '10 kΩ', '60 µV', GRN
    if t >= z2: zl, vt, vc = '100 kΩ', '600 µV', YEL
    if t >= half: zl, vt, vc = '1 MΩ', '6 mV', COR
    zig(cv, 300, 470, 330, FG, a, zl, YEL if zl != 'Z' else MUTED)
    cv.text((385, 252), 'electrode contact', 18, al(MUTED, a), False, 'mm')
    cv.line([(300, 330), (300, 450), (357, 450)], al(MUTED, a), 2); cv.line([(470, 330), (470, 450), (413, 450)], al(MUTED, a), 2)
    cv.circ(385, 450, 28, outline=al(MUTED, a), w=3); cv.text((385, 450), 'V', 26, al(FG, a), True, 'mm')
    if vt: cv.text((385, 508), vt, 34, al(vc, 1), True, 'mm')
    b = R(1)
    if b > 0:
        dots(cv, [(192, 330), (300, 330), (470, 330), (570, 330)], t, CY, b); cv.text((150, 430), '6 nA', 24, al(CY, b), True, 'mm')
    panel(cv, (830, 120, 1250, 560), R(2))
    if t >= T(2): cv.text((1040, 195), 'V = I × Z', 56, al(YEL, R(2)), True, 'mm')
    rows = [('10 kΩ  good', '60 µV', GRN, 40), ('100 kΩ  poor', '600 µV', YEL, 140), ('1 MΩ  bad', '6 mV', COR, 240)]
    for k, (lab, val, col, w) in enumerate(rows):
        at_ = [T(3), T(4), T(4) + (T(5) - T(4)) * 0.5][k]
        if t >= at_:
            ra = R(3) if k == 0 else ramp(t, at_); y = 285 + k * 85
            cv.text((855, y), lab, 24, al(FG, ra), True, 'lm'); cv.text((1230, y), val, 28, al(col, ra), True, 'rm'); cv.d.rectangle([855 * S, (y + 24) * S, (855 + w * ra) * S, (y + 38) * S], fill=al(col, ra))
    if t >= T(5): cv.text((1040, 535), 'bigger V = worse contact', 24, al(YEL, R(5)), True, 'mm')

def sc3(cv, t, T, R):
    a = R(0); cv.circ(110, 300, 28, outline=al(GRN, a), w=3); cv.text((110, 300), 'E', 22, al(GRN, a), True, 'mm'); cv.text((110, 345), 'electrode', 18, al(MUTED, a), False, 'mm')
    cv.line([(138, 300), (170, 300)], al(FG, a), 3); zig(cv, 170, 290, 300, FG, a, '2.2 kΩ', MUTED); cv.line([(290, 300), (640, 300)], al(FG, a), 3)
    cv.rect((330, 140, 900, 430), outline=al(GRY, a), r=16); cv.text((880, 164), 'ADS1299', 24, al(MUTED, a), True, 'rm'); cv.circ(330, 300, 5, fill=al(FG, a))
    cv.circ(400, 300, 6, fill=al(FG, a)); cv.line([(400, 300), (400, 205), (440, 205)], al(FG, a), 3)
    on = t >= T(1) + 0.8; opened = 1 - ease(ramp(t, T(1) + 0.8, 0.5)) if t >= T(1) else 1.0
    switch(cv, 440, 205, opened, a); cv.line([(490, 205), (532, 205)], al(FG, a), 3)
    cv.circ(560, 205, 28, outline=al(CY, a), w=3); arrow(cv, 572, 205, 548, 205, al(CY, a), 3); cv.text((560, 250), 'lead-off excitation source', 18, al(CY, a), False, 'mm')
    box(cv, 640, 265, 840, 335, a, r=10); cv.text((740, 300), 'PGA → ADC', 22, al(FG, a), True, 'mm')
    if on: dots(cv, [(532, 205), (490, 205), (440, 205), (400, 205), (400, 300), (330, 300), (290, 300), (170, 300)], t, CY, 1.0, n=5)
    b = R(1)
    if b > 0:
        cv.text((465, 172), 'one bit per input', 18, al(MUTED, b), False, 'mm')
        for row, (nm, y) in enumerate((('LOFF_SENSP', 482), ('LOFF_SENSN', 532))):
            cv.text((70, y), nm, 24, al(YEL, b), True, 'lm')
            for i in range(8):
                bit = 1 if (row == 0 and i == 2 and on) else 0; x0 = 330 + 54 * i
                cv.rect((x0, y - 18, x0 + 46, y + 18), fill=al(YEL, b * 0.9) if bit else None, outline=al(GRY, b), r=6); cv.text((x0 + 23, y), str(bit), 22, al(BG if bit else MUTED, b), True, 'mm')
                if row == 0: cv.text((x0 + 23, y - 32), f'ch{i + 1}', 14, al(MUTED, b), False, 'mm')
    c = R(2)
    if c > 0:
        box(cv, 930, 140, 1250, 380, c, GRY, fill=al((10, 15, 13), 0.86 * c)); cv.text((1090, 168), 'LOFF register: current size', 20, al(MUTED, c), True, 'mm')
        for k, (s, col) in enumerate((('6 nA   ← Cyton', YEL), ('24 nA', FG), ('6 µA', FG), ('24 µA', FG))): cv.text((960, 220 + k * 45), s, 28, al(col, c), col == YEL, 'lm')

def sc4(cv, t, T, R):
    a = R(0)
    for x0, lab, hi in ((80, 'DC', t >= T(1)), (260, 'AC', False)): box(cv, x0, 85, x0 + 150, 125, a, YEL if hi else GRY, r=10, w=3 if hi else 2); cv.text((x0 + 75, 105), lab, 26, al(YEL if hi else MUTED, a), True, 'mm')
    b = R(2)
    if b > 0:
        lvA = 0.5 + 0.012 * math.sin(t * 3); lvB = 0.5 + 0.5 * ease(ramp(t, T(4), 3.2)) if t >= T(4) else 0.5; thr = t >= T(5)
        gauge(cv, 330, 170, 500, lvA, GRN, b, thr); gauge(cv, 640, 170, 500, lvB, COR if lvB > 0.8 else YEL, b, thr)
        cv.text((330, 525), 'electrode on', 22, al(FG, b), True, 'mm'); cv.text((640, 525), 'electrode off', 22, al(FG, b), True, 'mm')
        for x in (330, 640): arrow(cv, x, 168, x, 140, al(CY, b), 3)
        cv.text((485, 150), 'tiny current pulls up', 18, al(CY, b), False, 'mm'); cv.text((520, 112), '(the other side is pulled down)', 15, al(MUTED, b), False, 'mm')
    if t >= T(3): cv.text((330, 560), 'barely moves', 22, al(GRN, R(3)), True, 'mm')
    if t >= T(4): cv.text((620, 560), 'pushed to the supply: saturated', 20, al(COR, R(4)), True, 'mm')
    panel(cv, (810, 130, 1250, 560), R(5))
    if t >= T(5):
        c = R(5); cv.text((1030, 165), 'comparators → flags', 24, al(MUTED, c), True, 'mm'); cv.text((1030, 215), 'LOFF_STATP', 26, al(YEL, c), True, 'mm')
        flagged = t >= T(4) + 2.4
        for i in range(8):
            x0 = 840 + 50 * i; bit = 1 if (i == 2 and flagged) else 0
            cv.rect((x0, 240, x0 + 42, 280), fill=al(COR, c) if bit else None, outline=al(GRY, c), r=6); cv.text((x0 + 21, 260), str(bit), 22, al(BG if bit else MUTED, c), True, 'mm')
        cv.text((1030, 310), '1 = this input is off', 20, al(COR if flagged else MUTED, c), False, 'mm')
    if t >= T(6): d = R(6); box(cv, 840, 400, 1220, 500, d, YEL, r=12, w=3); cv.text((1030, 435), 'sent with every sample', 24, al(YEL, d), True, 'mm'); cv.text((1030, 470), 'status bits + 8 channels', 20, al(FG, d), False, 'mm')

def sc5(cv, t, T, R):
    tau0 = t * 0.03; f = 40; a = R(0)
    cv.text((110, 100), 'AC  (the Cyton uses this)', 30, al(YEL, a), True, 'lm')
    cur = lambda tau: sq(math.sin(2 * math.pi * f * tau)); good = lambda tau: 0.2 * softsq(math.sin(2 * math.pi * f * tau)); poor = lambda tau: softsq(math.sin(2 * math.pi * f * tau))
    if t >= T(1): b = R(1); cv.text((120, 152), 'current: flips direction, 7.8 or 31.2 times a second', 20, al(MUTED, b), False, 'lm'); wave(cv, 120, 780, 205, 34, cur, CY, tau0, a=b, w=4)
    if t >= T(3): b = R(3); cv.text((120, 292), 'good contact: tiny tone', 20, al(GRN, b), True, 'lm'); wave(cv, 120, 780, 345, 34, good, GRN, tau0, a=b, w=4)
    if t >= T(4): b = R(4); cv.text((120, 432), 'poor contact: big tone', 20, al(COR, b), True, 'lm'); wave(cv, 120, 780, 485, 34, poor, COR, tau0, a=b, w=4)
    panel(cv, (830, 120, 1250, 560), R(1))
    if t >= T(2):
        b = R(2)
        for k, nm in enumerate(('electrode', 'amplifier', 'converter', 'your data')):
            x0 = 845 + k * 100; box(cv, x0, 160, x0 + 90, 215, b, FG if k == 3 else GRY, r=8); cv.text((x0 + 45, 188), nm, 15, al(FG, b), True, 'mm')
            if k < 3: arrow(cv, x0 + 91, 188, x0 + 100, 188, al(MUTED, b), 2)
        cv.text((1040, 245), 'the tone arrives in your recording', 18, al(MUTED, b), False, 'mm')
    if t >= T(3): b = R(3); cv.text((855, 310), 'good', 22, al(GRN, b), True, 'lm'); cv.d.rectangle([950 * S, 298 * S, (950 + 40 * b) * S, 322 * S], fill=al(GRN, b))
    if t >= T(4): b = R(4); cv.text((855, 365), 'poor', 22, al(COR, b), True, 'lm'); cv.d.rectangle([950 * S, 353 * S, (950 + 270 * b) * S, 377 * S], fill=al(COR, b))
    if t >= T(5): b = R(5); box(cv, 850, 430, 1230, 520, b, YEL, r=12, w=3); cv.text((1040, 460), 'size of the tone', 22, al(FG, b), False, 'mm'); cv.text((1040, 495), 'Z = V ÷ I', 36, al(YEL, b), True, 'mm')

def sc6(cv, t, T, R):
    a = R(0); cv.text((640, 150), '31.2 Hz' + ('' if t >= T(1) else ' ?'), 70, al(YEL, a), True, 'mm')
    if t >= T(1):
        b = R(1); cv.text((640, 240), '2,048,000 Hz  ÷  65,536  =  31.25 Hz', 38, al(FG, b), True, 'mm'); cv.text((640, 285), '(the datasheet rounds it to 31.2 Hz)', 20, al(MUTED, b), False, 'mm'); cv.text((640, 325), '7.8 Hz  =  the same clock  ÷  262,144', 22, al(MUTED, b), False, 'mm')
    X = lambda fq: 120 + fq * 17.33
    if t >= T(2):
        c = R(2); cv.line([(X(0), 470), (X(60), 470)], al(FG, c), 3)
        for fq in range(0, 61, 10): cv.line([(X(fq), 470), (X(fq), 478)], al(FG, c), 2); cv.text((X(fq), 498), f'{fq} Hz', 18, al(MUTED, c), False, 'mm')
        cv.rect((X(1), 400, X(40), 470), fill=al(GRN, c * 0.25), outline=al(GRN, c), r=6); cv.text((X(20.5), 428), 'the band the chip records', 22, al(GRN, c), True, 'mm')
        cv.line([(X(31.25), 470), (X(31.25), 380)], al(YEL, c), 4); cv.text((X(31.25) - 10, 392), '31.2 Hz tone', 20, al(YEL, c), True, 'rm')
        cv.line([(X(7.8), 470), (X(7.8), 420)], al(MUTED, c), 3); cv.text((X(7.8), 408), '7.8', 18, al(MUTED, c), True, 'mm')
    if t >= T(3): d = R(3); cv.rect((X(29.8), 372, X(32.7), 470), outline=al(YEL, d), r=6, w=3); cv.text((X(31.25), 350), 'software looks only here', 22, al(YEL, d), True, 'mm')

def sc7(cv, t, T, R):
    items = [(80, 400, 'when the board starts', '6 nA · 31.2 Hz', 'firmware setting'), (440, 760, 'a software command', 'channel · P · N', 'switches on a LOFF_SENS bit'), (800, 1200, 'OpenBCI GUI', 'measures the 31.2 Hz tone', 'shows the impedance')]
    for k, (x0, x1, t1, t2, t3) in enumerate(items):
        b = R(k)
        if b > 0:
            box(cv, x0, 160, x1, 330, b, YEL if k == 0 else GRY, r=14, w=3 if k == 0 else 2); cv.text(((x0 + x1) / 2, 205), t1, 22, al(MUTED, b), True, 'mm'); cv.text(((x0 + x1) / 2, 255), t2, 28, al(FG, b), True, 'mm'); cv.text(((x0 + x1) / 2, 300), t3, 20, al(MUTED, b), False, 'mm')
            if k > 0: arrow(cv, x0 - 38, 245, x0 - 6, 245, al(FG, b), 3)
    if t >= T(3):
        b = R(3); cv.text((640, 392), 'what you read (example)', 22, al(MUTED, b), True, 'mm')
        for x0, x1, t1, t2, col in ((200, 440, '2.2 kΩ', 'protection resistor', MUTED), (540, 780, '10 kΩ', 'electrode contact', GRN), (880, 1080, '12.2 kΩ', 'reading', YEL)):
            box(cv, x0, 420, x1, 510, b, col, r=12, w=3 if col == YEL else 2); cv.text(((x0 + x1) / 2, 452), t1, 32, al(col if col != MUTED else FG, b), True, 'mm'); cv.text(((x0 + x1) / 2, 490), t2, 18, al(MUTED, b), False, 'mm')
        cv.text((490, 465), '+', 46, al(FG, b), True, 'mm'); cv.text((830, 465), '=', 46, al(FG, b), True, 'mm')

def sc8(cv, t, T, R):
    a = R(0)
    box(cv, 150, 190, 470, 250, a, YEL, r=12, w=3); cv.text((310, 220), 'power-up', 26, al(YEL, a), True, 'mm')
    if t >= T(1):
        b = R(1)
        for x0, x1, tx in ((150, 330, 'current source'), (370, 540, 'bias electrode'), (580, 760, 'comparator')): box(cv, x0, 330, x1, 400, b, GRY, r=10); cv.text(((x0 + x1) / 2, 365), tx, 20, al(FG, b), True, 'mm')
        arrow(cv, 332, 365, 366, 365, al(FG, b), 3); arrow(cv, 542, 365, 576, 365, al(FG, b), 3); cv.text((460, 440), 'is the bias electrode connected?', 24, al(YEL, b), True, 'mm')
    if t >= T(2):
        c = R(2); box(cv, 500, 190, 1130, 250, c, COR, r=12, w=3); cv.text((815, 220), 'normal recording: bias amplifier ON', 26, al(COR, c), True, 'mm')
        cv.line([(800, 330), (1010, 410)], al(COR, c), 6); cv.line([(1010, 330), (800, 410)], al(COR, c), 6); cv.text((905, 450), 'this check can\'t run now', 24, al(COR, c), True, 'mm')

def sc9(cv, t, T, R):
    cv.text((640, 120), 'To sum up', 50, al(FG, R(0)), True, 'mm')
    items = [('1', 'A tiny known current through each electrode, then measure the voltage'), ('2', 'DC mode: quickly flags an electrode that is off'), ('3', 'AC mode: a real impedance number; the Cyton uses 6 nA at 31.2 Hz'), ('4', 'Built into the ADS1299: no extra parts, only a few register settings')]
    for k, (n, s) in enumerate(items):
        a = R(k + 1); y = 230 + k * 95; cv.circ(160, y, 28, outline=al(YEL, a), w=3); cv.text((160, y), n, 30, al(YEL, a), True, 'mm'); cv.text((220, y), s, 31, al(FG, a), False, 'lm')

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
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/out/v.mp4', '-i', f'{D}/out/a.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{D}/out/lead_off_detection.mp4'], check=True)
        print('DONE')
