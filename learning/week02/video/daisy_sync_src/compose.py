"""Overlay titles, labels, captions and animated diagrams on the 3D frames, then encode with the narration."""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__)); FPS = 15; W, H = 1280, 720
durs = json.load(open(f'{D}/durs.json')); narr = json.load(open(f'{D}/narr.json')); labels = json.load(open(f'{D}/labels.json'))
F = lambda s, b=False: ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf' if b else '/System/Library/Fonts/Supplemental/Arial.ttf', s)
MONO = lambda s: ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', s)
YEL, BG, FG, MUTED = (240, 224, 74), (13, 19, 17), (232, 239, 235), (147, 165, 157)
CY, DZ, CLK, ST, RD, OR = (167, 123, 255), (79, 209, 255), (240, 224, 74), (122, 162, 255), (79, 209, 255), (255, 138, 92)

TITLES = ["Cyton + Daisy: 16 channels", "Two identical ADS1299 chips", "Channels 9–16 come in", "The Daisy bus: 8 pins",
          "Sync trick 1: one clock", "Sync trick 2: one START", "Sync trick 3: one doorbell", "Taking turns on the radio", "Summary"]

def spoken(t):  # narration text -> on-screen text
    for a, b in [("A.D.S. twelve ninety-nine", "ADS1299"), ("T.V.S.", "TVS"), ("S.P.I.", "SPI"), ("C.S. 2", "CS2"), ("C.S. 1", "CS1"), ("C.L.K.", "CLK"), ("PIC 32", "PIC32"), ("S.R.B.", "SRB"), ("E E G", "EEG"), ("A D S 1299", "ADS1299"), ("T V S", "TVS"), ("S P I", "SPI"), ("C S 2", "CS2"), ("C S 1", "CS1"),
                 ("C L K", "CLK"), ("P I C 32", "PIC32"), ("S R B", "SRB"), ("2.2 kilo-ohm", "2.2 kΩ"), ("1 nanofarad", "1 nF"), ("megahertz", "MHz")]:
        t = t.replace(a, b)
    return t

def captions(sc):
    sents = re.split(r'(?<=[.!?])\s+', spoken(narr[sc]).strip())
    total = sum(len(s) for s in sents); usable = durs[sc] - 0.9; out = []; t = 0
    for s in sents:
        d = usable * len(s) / total; out.append((t, t + d, s)); t += d
    return out

def wrap(dr, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if dr.textlength(trial, font=font) <= maxw: cur = trial
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def pill(dr, x, y, text):
    f = F(17, True); tw = dr.textlength(text, font=f); bx, by = x - tw / 2 - 10, y - 46
    bx = max(8, min(W - tw - 28, bx))
    dr.line([(x, y - 6), (x, by + 30)], fill=YEL, width=2); dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=YEL)
    dr.rounded_rectangle([bx, by, bx + tw + 20, by + 30], 6, fill=YEL); dr.text((bx + 10, by + 5), text, font=f, fill=BG)

def panel(img, box, title):
    ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rounded_rectangle(box, 12, fill=(13, 19, 17, 228), outline=(60, 78, 70, 255), width=2); img.alpha_composite(ov)
    dr = ImageDraw.Draw(img); dr.text((box[0] + 16, box[1] + 12), title, font=F(15, True), fill=MUTED); return dr

def square(dr, x0, y, w, period, phase, col, h=22):
    pts, x, hi = [], x0 - phase % period, True
    while x < x0 + w:
        a, b = max(x, x0), min(x + period / 2, x0 + w)
        yy = y if hi else y + h
        if b > a: pts += [(a, yy), (b, yy)]
        x += period / 2; hi = not hi
    for i in range(len(pts) - 1): dr.line([pts[i], pts[i + 1]], fill=col, width=3)

def diagram(img, sc, t, u):
    X0, Y0, X1, Y1 = 812, 70, 1262, 360
    if sc == 1:
        dr = panel(img, (X0, Y0, X1, Y0 + 214), "BOTH CHIPS, SAME SETTINGS")
        for i, (lab, col, ch) in enumerate([("Cyton ADS1299", CY, "channels 1–8"), ("Daisy ADS1299", DZ, "channels 9–16")]):
            y = Y0 + 48 + i * 82; dr.rounded_rectangle([X0 + 16, y, X1 - 16, y + 66], 8, outline=col, width=2)
            dr.text((X0 + 30, y + 8), lab, font=F(19, True), fill=col); dr.text((X0 + 240, y + 10), ch, font=F(17), fill=FG)
            dr.text((X0 + 30, y + 38), "gain ×24 · 24-bit · 250 samples/s", font=F(16), fill=MUTED)
    elif sc == 3:
        dr = panel(img, (X0, Y0, X1, Y0 + 330), "J1: THE 8-PIN DAISY BUS")
        rows = [("DVDD", "3.3 V power", 0.10), ("GND", "ground", 0.10), ("MISO", "data out · shared", 0.30), ("SCK", "SPI clock · shared", 0.30),
                ("RST", "reset · shared", 0.62), ("CLK", "2.048 MHz clock", 0.70), ("MOSI", "data in · shared", 0.30), ("CS2", "Daisy's chip-select", 0.80)]
        for i, (pin, what, at) in enumerate(rows):
            on = u >= at; y = Y0 + 46 + i * 34; col = YEL if on else (70, 84, 78)
            dr.text((X0 + 22, y), f"{i + 1}", font=MONO(17), fill=MUTED); dr.text((X0 + 52, y), pin, font=MONO(19), fill=col)
            dr.text((X0 + 140, y + 1), what, font=F(17), fill=FG if on else (70, 84, 78))
    elif sc == 4:
        dr = panel(img, (X0, Y0, X1, Y0 + 270), "ONE CLOCK, SHARED BY BOTH CHIPS")
        ph = t * 60
        for i, (lab, col) in enumerate([("Cyton ADS1299", CY), ("Daisy ADS1299", DZ)]):
            y = Y0 + 56 + i * 84; dr.text((X0 + 16, y - 6), lab, font=F(15, True), fill=col); square(dr, X0 + 16, y + 18, X1 - X0 - 32, 26, ph, CLK)
        for k in range(3):
            x = X0 + 60 + ((k * 150 - ph * 0.6) % 420)
            for yy in range(Y0 + 44, Y0 + 220, 10): dr.line([(x, yy), (x, yy + 5)], fill=(255, 255, 255), width=1)
        dr.text((X0 + 16, Y0 + 228), "same 2.048 MHz ticks · 8,192 ticks = 1 sample", font=F(16), fill=FG)
    elif sc in (5, 6):
        dr = panel(img, (X0, Y0, X1, Y0 + 300), "WHAT THE PIC32 DOES" if sc == 5 else "ONE DRDY, THEN TWO READS")
        cur = X0 + 110 + (X1 - X0 - 130) * min(1, u * 1.15)
        rows = ([("CS1", CY), ("CS2", DZ), ("MOSI", ST), ("Cyton", CY), ("Daisy", DZ)] if sc == 5 else
                [("DRDY", OR), ("Daisy DRDY", (90, 100, 96)), ("CS1", CY), ("CS2", DZ), ("MISO", RD)])
        for i, (lab, col) in enumerate(rows):
            y = Y0 + 50 + i * 46; dr.text((X0 + 16, y), lab, font=MONO(15), fill=col)
            x0, x1 = X0 + 110, min(cur, X1 - 16)
            if sc == 5:
                if i < 2:
                    dr.line([(x0, y + 4), (min(x1, x0 + 70), y + 4)], fill=col, width=3)
                    if x1 > x0 + 70: dr.line([(x0 + 70, y + 4), (x0 + 70, y + 22), (min(x1, x0 + 180), y + 22)], fill=col, width=3)
                    if x1 > x0 + 180: dr.line([(x0 + 180, y + 22), (x0 + 180, y + 4), (x1, y + 4)], fill=col, width=3)
                elif i == 2 and x1 > x0 + 90:
                    dr.rounded_rectangle([x0 + 90, y, x0 + 170, y + 26], 4, fill=ST); dr.text((x0 + 98, y + 4), "START", font=F(15, True), fill=BG)
                elif i > 2 and x1 > x0 + 180:
                    dr.rounded_rectangle([x0 + 180, y, x1, y + 26], 4, fill=col); dr.text((x0 + 188, y + 4), "converting…", font=F(15, True), fill=BG)
            else:
                if i == 0:
                    dr.line([(x0, y + 4), (min(x1, x0 + 40), y + 4)], fill=col, width=3)
                    if x1 > x0 + 40: dr.line([(x0 + 40, y + 4), (x0 + 40, y + 22), (x1, y + 22)], fill=col, width=3)
                elif i == 1: dr.text((x0, y + 2), "not connected", font=F(15), fill=(110, 120, 116))
                elif i == 2 and x1 > x0 + 60:
                    e = min(x1, x0 + 170); dr.line([(x0 + 60, y + 22), (e, y + 22)], fill=col, width=3)
                elif i == 3 and x1 > x0 + 180:
                    e = min(x1, x0 + 300); dr.line([(x0 + 180, y + 22), (e, y + 22)], fill=col, width=3)
                elif i == 4:
                    if x1 > x0 + 60: dr.rounded_rectangle([x0 + 60, y, min(x1, x0 + 170), y + 26], 4, fill=CY)
                    if x1 > x0 + 110: dr.text((x0 + 68, y + 4), "27 B", font=F(15, True), fill=BG)
                    if x1 > x0 + 180: dr.rounded_rectangle([x0 + 180, y, min(x1, x0 + 300), y + 26], 4, fill=DZ)
                    if x1 > x0 + 230: dr.text((x0 + 188, y + 4), "27 B", font=F(15, True), fill=BG)
            dr.line([(cur, Y0 + 44), (cur, Y0 + 280)], fill=(255, 255, 255), width=1)
    elif sc == 7:
        dr = panel(img, (X0, Y0, X1, Y0 + 220), "RADIO PACKETS TAKE TURNS")
        off = (t * 70) % 120
        for k in range(-1, 5):
            x = X0 + 16 + k * 120 - off + 120; n = int(t * 70 // 120) + k
            if x < X0 + 10 or x + 108 > X1 - 10: continue
            odd = n % 2 == 1; col = CY if odd else DZ
            dr.rounded_rectangle([x, Y0 + 56, x + 108, Y0 + 116], 8, fill=col)
            dr.text((x + 10, Y0 + 62), f"#{n}", font=MONO(15), fill=BG); dr.text((x + 10, Y0 + 86), "ch 1–8" if odd else "ch 9–16", font=F(17, True), fill=BG)
        dr.text((X0 + 16, Y0 + 134), "odd packets: Cyton · even packets: Daisy", font=F(16), fill=FG)
        dr.text((X0 + 16, Y0 + 162), "each = average of 2 samples", font=F(16), fill=FG)
        dr.text((X0 + 16, Y0 + 186), "→ every channel at 125 per second", font=F(16), fill=YEL)
    elif sc == 8:
        dr = panel(img, (X0, Y0, X1, Y0 + 250), "HOW 16 CHANNELS STAY IN SYNC")
        items = [("One clock", "Cyton chip's CLK drives both", 0.05), ("One START", "both chip-selects low together", 0.12),
                 ("One doorbell", "only the Cyton's DRDY is used", 0.2), ("SRB tip", "join both SRB pins: Y-splitter", 0.62)]
        for i, (a, b, at) in enumerate(items):
            if u < at: continue
            y = Y0 + 50 + i * 48; dr.text((X0 + 18, y), str(i + 1) if i < 3 else "!", font=F(20, True), fill=YEL)
            dr.text((X0 + 44, y), a, font=F(19, True), fill=FG); dr.text((X0 + 44, y + 23), b, font=F(15), fill=MUTED)

def frame(sc, f, caps):
    t = f / FPS; u = t / durs[sc]
    img = Image.open(f'{D}/raw/s{sc}_{f:04d}.jpg').convert('RGBA'); dr = ImageDraw.Draw(img)
    for x, y, text in labels.get(f's{sc}_{f:04d}', []):
        if 0 < x < W and 60 < y < H - 120: pill(dr, x, y, text)
    dr.rounded_rectangle([18, 16, 34 + dr.textlength(TITLES[sc], font=F(24, True)) + 64, 58], 8, fill=(13, 19, 17, 235))
    dr.text((30, 22), f"{sc + 1}/9", font=MONO(18), fill=YEL); dr.text((82, 21), TITLES[sc], font=F(24, True), fill=FG)
    diagram(img, sc, t, u); dr = ImageDraw.Draw(img)
    cap = next((c for a, b, c in caps if a <= t < b), caps[-1][2] if t >= caps[-1][0] else "")
    if cap:
        lines = wrap(dr, cap, F(25), 1080); h = 20 + 34 * len(lines)
        ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle([90, H - h - 22, W - 90, H - 18], 10, fill=(8, 12, 11, 215)); img.alpha_composite(ov)
        dr = ImageDraw.Draw(img)
        for i, l in enumerate(lines): dr.text((W / 2 - dr.textlength(l, font=F(25)) / 2, H - h - 12 + i * 34), l, font=F(25), fill=FG)
    return img.convert('RGB')

if __name__ == '__main__':
    only = sys.argv[1:]
    if only:                                   # preview: compose.py sc frame
        sc, f = int(only[0]), int(only[1]); frame(sc, f, captions(sc)).save(f'{D}/comp_{sc}_{f}.jpg'); sys.exit()
    os.makedirs(f'{D}/out', exist_ok=True)
    enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', f'{D}/out/video_only.mp4'], stdin=subprocess.PIPE)
    for sc, d in enumerate(durs):
        caps = captions(sc)
        for f in range(round(d * FPS)): frame(sc, f, caps).save(enc.stdin, 'JPEG', quality=92)
        print('composed scene', sc, flush=True)
    enc.stdin.close(); enc.wait()
    # narration: each scene's audio padded to its scene length
    parts = []
    for sc, d in enumerate(durs):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/s{sc}.aiff', '-af', f'apad=whole_dur={round(d * FPS) / FPS}', '-ar', '44100', '-ac', '2', f'{D}/out/a{sc}.wav'], check=True)
        parts.append(f"file '{D}/out/a{sc}.wav'")
    open(f'{D}/out/alist.txt', 'w').write('\n'.join(parts))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{D}/out/alist.txt', '-c', 'pcm_s16le', f'{D}/out/audio.wav'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/out/video_only.mp4', '-i', f'{D}/out/audio.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{D}/out/daisy_sync.mp4'], check=True)
    print('DONE')
