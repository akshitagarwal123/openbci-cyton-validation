"""How the ADS1299 bias input becomes an average: animated explainer (PIL frames + narration timing)."""
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

# ------------------------------------------------------------------ scenes (t = seconds on the video clock, T(i) = start of sentence i)
def sc1(cv, t, T, R):
    a = R(0)
    cv.rect((120, 250, 400, 410), outline=al(BLU, a), w=3, r=14)
    cv.text((260, 308), 'PGA outputs', 28, al(FG, a), True, 'mm'); cv.text((260, 352), '8 channels, P and N', 20, al(MUTED, a), False, 'mm')
    arrow(cv, 405, 330, 560, 330, al(FG, a)); pulse = 1 + (0.06 * math.sin(t * 5) if t >= T(1) else 0)
    cv.circ(640, 330, 70 * pulse, outline=al(YEL, a), w=4); cv.text((640, 322), '?', 96, al(YEL, a), True, 'mm')
    arrow(cv, 715, 330, 820, 330, al(FG, a)); cv.poly([(830, 260), (830, 400), (970, 330)], outline=al(COR, a))
    cv.text((848, 292), '−', 28, al(COR, a), True, 'mm'); cv.text((848, 368), '+', 28, al(COR, a), True, 'mm'); cv.text((905, 430), 'bias amplifier', 20, al(MUTED, a), False, 'mm')
    cv.text((640, 470), 'no adder  ·  no divider  ·  just wires', 26, al(MUTED, a), False, 'mm')
    cv.text((640, 560), "we'll build it from simple numbers", 34, al(FG, R(2)), True, 'mm')

def branches(cv, ys, vals, labels, a, rlabels=None, rcols=None, bus=(700, None), sw=None):
    for k, (y, v, lab) in enumerate(zip(ys, vals, labels)):
        source(cv, 190, y, v, lab, a); cv.line([(232, y), (300, y)], al(FG, a), 3)
        rl = (rlabels or ['R'] * 9)[k]; rc = (rcols or [None] * 9)[k]
        rx2 = 420 if sw else 440
        zig(cv, 300, rx2, y, FG, a, rl, rc)
        if sw:
            cv.line([(rx2, y), (440, y)], al(FG, a), 3); switch(cv, 440, y, sw[k], a); cv.line([(490, y), (700, y)], al(FG, a), 3)
        else: cv.line([(rx2, y), (700, y)], al(FG, a), 3)
    cv.line([(700, min(ys)), (700, max(ys))], al(FG, a), 3)

def eqline(cv, y, txt, a, size=26, col=FG, bold=False): cv.text((855, y), txt, size, al(col, a), bold, 'lm')

def sc2(cv, t, T, R):
    a = R(0); branches(cv, [250, 430], ['10 V', '20 V'], ['source A', 'source B'], a)
    cv.circ(700, 340, 10, fill=al(YEL, a)); done = t >= T(7)
    cv.text((730, 340), '15 V' if done else '?', 40 if done else 56, al(YEL, R(7) if done else R(1)), True, 'lm')
    if t >= T(2): cv.circ(700, 340, 22 + 3 * math.sin(t * 4), outline=al(YEL, R(2) * 0.8), w=2)
    b = R(3)
    if b > 0:
        dots(cv, [(232, 430), (300, 430), (440, 430), (700, 430), (700, 340)], t, CY, b); dots(cv, [(700, 340), (700, 250), (440, 250), (300, 250), (232, 250)], t, CY, b)
        cv.text((570, 462), '5 / R in' if done else 'current in', 20, al(CY, b), True, 'mm'); cv.text((570, 222), '5 / R out' if done else 'current out', 20, al(CY, b), True, 'mm')
    panel(cv, (830, 120, 1250, 540), R(4))
    if t >= T(4): eqline(cv, 160, 'current = voltage difference ÷ R', R(4), 22, MUTED)
    if t >= T(5): eqline(cv, 240, '(20 − V) / R  =  (V − 10) / R', R(5), 28)
    if t >= T(6): eqline(cv, 310, '20 − V  =  V − 10', R(6), 28)
    if t >= T(7): eqline(cv, 395, 'V = 15 V', R(7), 48, YEL, True)
    if t >= T(8): eqline(cv, 470, '= (10 + 20) ÷ 2', R(8), 32, YEL)

def sc3(cv, t, T, R, resl=None, rescol=None, sw=None, vals=('10 V', '12 V', '8 V'), nodetxt=None):
    a = R(0); branches(cv, [190, 340, 490], list(vals), ['source 1', 'source 2', 'source 3'], a, resl, rescol, sw=sw)
    cv.circ(700, 340, 10, fill=al(YEL, a))
    return a

def sc3_scene(cv, t, T, R):
    a = sc3(cv, t, T, R); done = t >= T(3)
    cv.text((730, 340), '10 V' if done else 'V = ?', 36, al(YEL, R(3) if done else a), True, 'lm')
    b = R(1)
    if b > 0:
        dots(cv, [(232, 340), (300, 340), (700, 340)], t, CY, b, n=3); dots(cv, [(700, 340), (700, 490), (440, 490), (300, 490), (232, 490)], t, CY, b, n=4)
        cv.text((520, 372), '+2 / R in' if done else 'in', 20, al(CY, b), True, 'mm'); cv.text((520, 522), '−2 / R out' if done else 'out', 20, al(CY, b), True, 'mm'); cv.text((520, 222), '0' if done else '', 20, al(MUTED, b), True, 'mm')
    panel(cv, (830, 120, 1250, 560), R(2))
    if t >= T(2): eqline(cv, 170, '(10 − V)/R + (12 − V)/R', R(2), 24); eqline(cv, 208, '+ (8 − V)/R = 0', R(2), 24)
    if t >= T(3): eqline(cv, 275, '30 − 3V = 0', R(3), 28); eqline(cv, 340, 'V = 30 ÷ 3 = 10 V', R(3), 34, YEL, True)
    if t >= T(4):
        r4 = R(4); cv.rect((850, 400, 1230, 480), outline=al(YEL, r4), r=10); cv.text((1040, 440), 'V = (V1 + V2 + … + Vn) ÷ n', 25, al(YEL, r4), True, 'mm')
    if t >= T(5): cv.text((1040, 520), 'resistors add  ·  branches divide', 22, al(MUTED, R(5)), False, 'mm')

def numline(cv, a, t, T, marks):
    x = lambda v: 870 + (v - 8) / 4 * 340
    cv.line([(870, 380), (1210, 380)], al(FG, a), 3)
    for v, col, lab in ((8, COR, '8'), (10, BLU, '10'), (12, BLU, '12')):
        cv.circ(x(v), 380, 9, fill=al(col, a)); cv.text((x(v), 408), lab, 20, al(MUTED, a), True, 'mm')
    for v, col, lab, at_ in marks:
        if t >= at_:
            ra = ramp(t, at_); below = col == COR
            cv.line([(x(v), 380), (x(v), 430 if below else 330)], al(col, ra), 3); cv.circ(x(v), 380, 6, fill=al(col, ra))
            cv.text((x(v), 452 if below else 305), lab, 22, al(col, ra), True, 'mm')

def sc4(cv, t, T, R):
    half = ease(ramp(t, T(1), 0.8)); a = R(0)
    rl = ['R', 'R', 'R/2' if half > 0.5 else 'R']; rc = [None, None, COR if half > 0.5 else None]
    branches(cv, [190, 340, 490], ['10 V', '12 V', '8 V'], ['source 1', 'source 2', 'source 3'], a, rl, rc)
    cv.circ(700, 340, 10, fill=al(YEL, a))
    cv.text((730, 340), '9.5 V' if t >= T(2) else '10 V', 36, al(YEL, a), True, 'lm')
    if t >= T(1): cv.text((520, 545), 'source 3 pulls twice as hard', 22, al(COR, R(1)), True, 'mm')
    panel(cv, (830, 120, 1250, 560), a); cv.text((1040, 165), 'where does the wire settle?', 24, al(MUTED, a), True, 'mm')
    numline(cv, a, t, T, [(10, YEL, 'equal: 10 V', 0), (9.5, COR, '9.5 V', T(2))])
    if t >= T(3): cv.text((1040, 510), 'equal resistors →', 26, al(FG, R(3)), True, 'mm'); cv.text((1040, 543), 'every source counts equally', 26, al(YEL, R(3)), True, 'mm')
    if t >= T(4): cv.text((1040, 262), 'matched on one chip', 20, al(MUTED, R(4)), False, 'mm')

def sc5(cv, t, T, R):
    a = R(0); op = ease(ramp(t, T(2), 0.7)); opened = [0, 0, op]
    branches(cv, [190, 340, 490], ['10 V', '12 V', '8 V'], ['source 1', 'source 2', 'source 3'], a, sw=opened)
    cv.text((465, 152), 'switches', 20, al(MUTED, a), False, 'mm'); cv.circ(700, 340, 10, fill=al(YEL, a)); done = t >= T(2) + 0.7
    cv.text((730, 340), '11 V' if done else '10 V', 36, al(YEL, a), True, 'lm')
    if t >= T(1): cv.text((465, 540), 'open switch = no current = left out', 20, al(COR, R(1)), True, 'mm')
    if done:
        b = R(2)
        dots(cv, [(232, 340), (300, 340), (700, 340)], t, CY, b, n=3); dots(cv, [(700, 340), (700, 190), (440, 190), (300, 190), (232, 190)], t, CY, b, n=4)
        cv.text((575, 420), 'n = 2:  (10 + 12) ÷ 2', 24, al(YEL, b), True, 'mm')
    panel(cv, (830, 120, 1250, 560), R(3))
    if t >= T(3):
        r = R(3); cv.text((1040, 170), 'in the ADS1299', 24, al(MUTED, r), True, 'mm'); cv.text((1040, 235), 'BIAS_SENSP', 34, al(YEL, r), True, 'mm'); cv.text((1040, 285), 'BIAS_SENSN', 34, al(YEL, r), True, 'mm')
        cv.text((1040, 345), 'one bit per P input', 22, al(FG, r), False, 'mm'); cv.text((1040, 378), 'and per N input', 22, al(FG, r), False, 'mm')
    if t >= T(4): cv.rect((850, 430, 1230, 520), outline=al(GRN, R(4)), r=12); cv.text((1040, 462), 'OpenBCI GUI', 24, al(GRN, R(4)), True, 'mm'); cv.text((1040, 495), '"Bias" per channel', 22, al(FG, R(4)), False, 'mm')

def sc6(cv, t, T, R):
    tau0 = t * 0.04
    ES = lambda tau: 0.14 * (0.8 * math.sin(2 * math.pi * 9 * tau + 0.5) + 0.5 * math.sin(2 * math.pi * 21 * tau + 2.0))
    REF = lambda tau: HUM(tau); ELE = lambda tau: HUM(tau) + ES(tau); AVG = lambda tau: (REF(tau) + ELE(tau)) / 2; DIF = lambda tau: 4 * (ELE(tau) - REF(tau))
    cv.rect((60, 110, 880, 560), outline=al(GRY, 1), r=14)
    cv.text((70, 92), 'one channel, drawn slowed down', 18, al(MUTED, R(0)), False, 'lm')
    a1 = R(1); r2 = t >= T(2)
    if a1 > 0:
        for yc, nm, col, fn, lab in ((175, 'A', BLU, REF, 'reference'), (275, 'B', PUR, ELE, 'electrode')):
            cv.text((75, yc), lab if r2 else f'input {nm}', 20, al(col if r2 else MUTED, a1), True, 'lm'); wave(cv, 175, 860, yc, 38, fn, col, tau0, a=a1)
    if t >= T(4):
        b = R(4)
        for yc in (175, 275): wave(cv, 175, 860, yc, 38, HUM, MUTED, tau0, w=1.5, a=0.7 * b)
        cv.text((860, 128), 'dotted = the shared hum', 18, al(MUTED, b), False, 'rm')
    if t >= T(6):
        c = R(6); cv.text((75, 375), 'average', 20, al(YEL, c), True, 'lm'); wave(cv, 175, 860, 375, 38, AVG, YEL, tau0, w=4, a=c)
        if t >= T(7): wave(cv, 175, 860, 375, 38, HUM, MUTED, tau0, w=1.5, a=0.8 * R(7))
    if t >= T(8):
        d = R(8); cv.text((75, 470), 'difference', 20, al(CY, d), True, 'lm'); cv.text((75, 494), '(zoomed ×4)', 14, al(MUTED, d), False, 'lm'); wave(cv, 175, 860, 478, 38, DIF, CY, tau0, w=3, a=d)
    panel(cv, (905, 110, 1250, 560), R(2))
    if t >= T(2): cv.text((925, 170), 'one input = the reference', 22, al(BLU, R(2)), True, 'lm'); cv.text((925, 205), 'other = scalp electrode', 22, al(PUR, R(2)), True, 'lm')
    if t >= T(3): cv.text((925, 265), 'Cyton: SRB2 → P side', 20, al(MUTED, R(3)), False, 'lm'); cv.text((925, 293), 'TI example: SRB1 → N side', 20, al(MUTED, R(3)), False, 'lm')
    if t >= T(6): cv.text((925, 355), '(reference + electrode) ÷ 2', 22, al(YEL, R(6)), True, 'lm'); cv.text((925, 390), '= hum + ½ EEG', 28, al(YEL, R(6)), True, 'lm')
    if t >= T(7): cv.text((925, 445), 'EEG is tiny next to the hum', 20, al(FG, R(7)), False, 'lm'); cv.text((925, 478), '→ almost pure hum', 26, al(YEL, R(7)), True, 'lm')
    if t >= T(8): cv.text((925, 525), 'difference = EEG', 28, al(CY, R(8)), True, 'lm')
    if t >= T(4): cv.text((880, 92), 'not to scale: real hum is far bigger', 15, al(MUTED, R(4)), False, 'rm')

def sc7(cv, t, T, R):
    tau0 = t * 0.04; a = R(0); cv.rect((60, 100, 880, 580), outline=al(GRY, 1), r=14)
    amps = [1.0, 1.12, 0.9, 1.04]; phs = [0.0, 0.5, -0.4, 0.2]; cols = [BLU, PUR, GRN, CY]
    for k in range(4):
        yc = 160 + k * 85; cv.text((75, yc), f'CH{k + 1}', 22, al(cols[k], a), True, 'lm'); wave(cv, 170, 860, yc, 30, lambda tau, k=k: HUM(tau, phs[k], amps[k]), cols[k], tau0, a=a)
    if t >= T(1):
        b = R(1); cv.text((75, 520), 'average', 22, al(YEL, b), True, 'lm')
        wave(cv, 170, 860, 520, 34, lambda tau: sum(HUM(tau, phs[k], amps[k]) for k in range(4)) / 4, YEL, tau0, w=5, a=b)
    panel(cv, (905, 100, 1250, 580), R(0))
    cv.text((1077, 170), 'each channel sees', 22, al(FG, a), False, 'mm'); cv.text((1077, 205), 'a slightly different hum', 22, al(FG, a), False, 'mm')
    if t >= T(1): cv.text((1077, 330), 'average of all', 24, al(YEL, R(1)), True, 'mm'); cv.text((1077, 365), 'switched-on channels', 24, al(YEL, R(1)), True, 'mm'); cv.text((1077, 430), '= the hum on your body', 24, al(FG, R(1)), True, 'mm')

def sc8(cv, t, T, R):
    tau0 = t * 0.04; a = R(0)
    cv.rect((70, 110, 330, 230), outline=al(GRY, a), r=12); wave(cv, 85, 315, 170, 36, HUM, YEL, tau0, a=a, w=4); cv.text((200, 252), 'average = hum', 20, al(YEL, a), True, 'mm')
    cv.line([(330, 170), (420, 170), (420, 300), (480, 300)], al(YEL, a), 3)
    cv.poly([(480, 265), (480, 395), (610, 330)], outline=al(COR, a)); cv.text((498, 300), '−', 30, al(COR, a), True, 'mm'); cv.text((498, 362), '+', 30, al(COR, a), True, 'mm')
    cv.line([(380, 362), (480, 362)], al(FG, a), 3); cv.text((380, 392), 'reference level', 18, al(MUTED, a), False, 'lm'); cv.text((545, 425), 'bias amplifier', 20, al(MUTED, a), False, 'mm')
    b = R(1)
    if b > 0: cv.rect((650, 110, 910, 230), outline=al(COR, b), r=12); wave(cv, 665, 895, 170, 36, lambda tau: -HUM(tau), COR, tau0, a=b, w=4); cv.text((780, 252), 'BIAS OUT = upside-down hum', 20, al(COR, b), True, 'mm')
    c = R(2)
    if c > 0:
        cv.line([(610, 330), (690, 330)], al(FG, c), 3); zig(cv, 690, 820, 330, FG, c, 'R5', COR); cv.line([(820, 330), (930, 330)], al(FG, c), 3)
        cv.circ(1030, 330, 90, outline=al(BLU, c), w=3); cv.text((1030, 322), 'your head', 26, al(FG, c), True, 'mm'); cv.text((1030, 358), 'bias electrode', 18, al(MUTED, c), False, 'mm')
        dots(cv, [(610, 330), (690, 330), (820, 330), (940, 330)], t, COR, c, n=4, speed=0.4)
        shrink = ease(ramp(t, T(2) + 1.5, 2.0)); h = 90 - 65 * shrink
        cv.text((1030, 452), 'hum on your body', 22, al(MUTED, c), True, 'mm'); cv.rect((945, 468, 1015, 568), outline=al(GRY, c), r=6)
        cv.d.rectangle([950 * S, (563 - h) * S, 1010 * S, 563 * S], fill=al(YEL, c)); cv.text((980, 588), 'with bias', 18, al(MUTED, c), False, 'mm')
        cv.rect((1045, 468, 1115, 568), outline=al(GRY, c), r=6); cv.d.rectangle([1050 * S, (563 - 90) * S, 1110 * S, 563 * S], fill=al(GRY, c)); cv.text((1080, 588), 'no bias', 18, al(MUTED, c), False, 'mm')
    if t >= T(3): cv.text((440, 520), 'cleaner signals on every channel', 30, al(YEL, R(3)), True, 'mm')

def sc9(cv, t, T, R):
    cv.text((640, 120), 'To sum up', 50, al(FG, R(0)), True, 'mm')
    items = [('1', 'Currents into the shared wire add up to zero'), ('2', 'Equal resistors  →  the voltage is the plain average'), ('3', 'The switches choose who takes part'), ('4', 'The amplifier flips it and drives it back into your body')]
    for k, (n, s) in enumerate(items):
        a = R(k + 1); y = 230 + k * 95; cv.circ(220, y, 28, outline=al(YEL, a), w=3); cv.text((220, y), n, 30, al(YEL, a), True, 'mm'); cv.text((280, y), s, 34, al(FG, a), False, 'lm')
    if t >= T(4) + 1.0: cv.text((640, 595), 'V = (V1 + V2 + … + Vn) ÷ n', 36, al(YEL, ramp(t, T(4) + 1.0)), True, 'mm')

SC = [sc1, sc2, sc3_scene, sc4, sc5, sc6, sc7, sc8, sc9]

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
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/out/v.mp4', '-i', f'{D}/out/a.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{D}/out/bias_average.mp4'], check=True)
        print('DONE')
