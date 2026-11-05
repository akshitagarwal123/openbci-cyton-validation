"""Course compositor: overlays (chapter cards, labels, schematic close-ups, diagrams, captions) + narration, one MP4 per chapter, then the full course."""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, f'{D}/../dvid'); import compose as K           # reuse fonts, pills, panels and the sync diagrams
F, MONO, YEL, BG, FG, MUTED = K.F, K.MONO, K.YEL, K.BG, K.FG, K.MUTED
FPS, W, H = 15, 1280, 720
C = json.load(open(f'{D}/course.json')); DU = json.load(open(f'{D}/durs.json'))
NCH = max(s['ch'] for s in C) + 1
SCHIMG = {'cy': Image.open(f'{D}/cyton_schematic.jpg').convert('RGB'), 'dz': Image.open(f'{D}/daisy_schematic.jpg').convert('RGB')}
SCL = {'cy': 5037 / 2000, 'dz': 4836 / 2000}
SCH = {"full": ("cy", (0, 0, 2000, 1285), "Cyton schematic: the whole sheet"), "power": ("cy", (40, 40, 900, 372), "Schematic · power supply"),
       "input": ("cy", (1187, 250, 1357, 402), "Schematic · input connector (PL1)"), "prot": ("cy", (420, 1035, 800, 1255), "Schematic · TVS, 2.2 kΩ, 1 nF"),
       "ads": ("cy", (962, 450, 1543, 1138), "Schematic · ADS1299"), "vref": ("cy", (1080, 880, 1440, 1070), "Schematic · VREF / VCAP capacitors"),
       "decoup": ("cy", (900, 40, 1108, 372), "Schematic · ADS1299 decoupling"), "bias": ("cy", (985, 535, 1150, 625), "Schematic · R5 ‖ C16 on the bias output"),
       "mcu": ("cy", (1543, 450, 1973, 1138), "Schematic · PIC32"), "radio": ("cy", (1563, 38, 1975, 450), "Schematic · RFduino radio"),
       "sd": ("cy", (63, 517, 309, 715), "Schematic · SD card"), "accel": ("cy", (63, 721, 309, 984), "Schematic · accelerometer + OR gate"),
       "dz_full": ("dz", (380, 130, 1545, 1145), "Daisy schematic"), "dz_bus": ("dz", (1275, 140, 1445, 435), "Daisy schematic · Daisy bus + header")}
_cache = {}
def sch_img(key):
    if key not in _cache:
        src, box, title = SCH[key]; s = SCL[src]
        im = SCHIMG[src].crop(tuple(int(v * s) for v in box)); mw, mh = 500, 300
        r = min(mw / im.width, mh / im.height); im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
        _cache[key] = (im, title)
    return _cache[key]
PANEL_SC = {"clock": 4, "start": 5, "drdy": 6, "packets": 7}
FLOWS = {"signal": ("Brain signal", "#2ec4a0"), "power": ("Power", "#ffb347"), "bias": ("Bias loop", "#ff8a5c"), "motion": ("Motion", "#a77bff"),
         "storage": ("SD card", "#7fe3e3"), "clock": ("PIC32 clock", "#f0e04a"), "controls": ("Buttons & switch", "#c9d2dc"), "daisy": ("Daisy signal", "#4fd1ff"),
         "daisybus": ("Daisy bus", "#7aa2ff"), "daisypower": ("Daisy power", "#ffd36e"), "vsig": ("Daisy signal", "#4fd1ff"), "vclock": ("Shared 2.048 MHz clock", "#f0e04a"),
         "vstart": ("START command", "#7aa2ff"), "vdrdy": ("Data ready (DRDY)", "#ff8a5c"), "vread": ("SPI read", "#4fd1ff"), "vread1": ("SPI read", "#4fd1ff"), "vradio": ("Radio packets", "#2ec4a0")}
hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def bt8(img):
    dr = K.panel(img, (772, 70, 1262, 330), "BRAINTECH-8 VS THE CYTON")
    rows = [("ESP32-S3 with Wi-Fi", "replaces PIC32 + RFduino"), ("stronger 3.3 V supply", "Wi-Fi bursts ≈ 350 mA"), ("47 pF C0G input caps", "instead of 1 nF"),
            ("2 × 100 kΩ on BIAS", "in series with the electrode"), ("LiPo + USB charging", "instead of a 3–6 V pack"), ("same ADS1299 core", "protection, VCAPs, bias loop")]
    for i, (a, b) in enumerate(rows):
        y = 112 + i * 35; dr.text((790, y), a, font=F(17, True), fill=FG); dr.text((1020, y + 2), b, font=F(15), fill=MUTED)

def captions(i):
    sc, d = C[i], DU[i]; sents = re.split(r'(?<=[.!?:])\s+(?=[A-Z0-9])', sc['text'].strip())
    total = sum(len(s) for s in sents); t0, usable = d['lead'], d['dur'] - d['lead'] - 0.8; out = []
    for s in sents:
        dd = usable * len(s) / total; out.append((t0, t0 + dd, s)); t0 += dd
    return out

def frame(i, f, caps, labels):
    sc, d = C[i], DU[i]; t = f / FPS; ts = max(0, t - d['lead']); shots = sc['shots']
    k = 0
    for j, sh in enumerate(shots):
        if ts >= sh['at'] * (d['dur'] - d['lead']): k = j
    sh = shots[k]
    img = Image.open(f'{D}/raw/s{i:02d}_{f:05d}.jpg').convert('RGBA'); dr = ImageDraw.Draw(img)
    for x, y, text in labels.get(str(f), []):
        if 0 < x < W and 70 < y < H - 120: K.pill(dr, x, y, text)
    # title block in the style of the turbocharger explainer: numbered uppercase title, subtitle, flow colour key
    title = f"{sc['ch'] + 1:02d}  {sc['chTitle'].upper()}"; sub = f"Chapter {sc['ch'] + 1} of {NCH}  ·  Cyton + Daisy, from battery to brain waves"
    keys = []
    for fl in sh.get('flows', []):
        if fl in FLOWS and FLOWS[fl] not in keys: keys.append(FLOWS[fl])
    bw = max(dr.textlength(title, font=F(26, True)), dr.textlength(sub, font=F(15))) + 36; bh = 82 + 24 * len(keys)
    ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle([14, 12, 14 + bw, 12 + bh], 10, fill=(13, 19, 17, 210)); img.alpha_composite(ov)
    dr = ImageDraw.Draw(img); dr.text((30, 22), title, font=F(26, True), fill=FG); dr.text((30, 22), f"{sc['ch'] + 1:02d}", font=F(26, True), fill=YEL)
    dr.text((30, 58), sub, font=F(15), fill=MUTED)
    for j, (nm, col) in enumerate(keys):
        y = 88 + j * 24; dr.ellipse([32, y + 4, 42, y + 14], fill=hexc(col)); dr.text((50, y), nm.upper(), font=F(14, True), fill=hexc(col))
    if sh.get('sch'):
        im, cap = sch_img(sh['sch']); x0 = W - 18 - im.width - 16; y0 = 70
        ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); o = ImageDraw.Draw(ov)
        o.rounded_rectangle([x0, y0, W - 18, y0 + im.height + 46], 10, fill=(13, 19, 17, 235), outline=(60, 78, 70, 255), width=2); img.alpha_composite(ov)
        img.paste(im, (x0 + 8, y0 + 38)); ImageDraw.Draw(img).text((x0 + 14, y0 + 10), cap, font=F(15, True), fill=MUTED)
    if sh.get('panel') in PANEL_SC:
        st = sh['at'] * (d['dur'] - d['lead']); K.diagram(img, PANEL_SC[sh['panel']], ts, min(1, (ts - st) / max(1, d['dur'] - d['lead'] - st)))
    elif sh.get('panel') == 'bt8': bt8(img)
    dr = ImageDraw.Draw(img)
    cap = next((c for a, b, c in caps if a <= t < b), "")
    if cap:
        lines = K.wrap(dr, cap, F(25), 1080); hh = 20 + 34 * len(lines)
        ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle([90, H - hh - 22, W - 90, H - 18], 10, fill=(8, 12, 11, 215)); img.alpha_composite(ov)
        dr = ImageDraw.Draw(img)
        for j, l in enumerate(lines): dr.text((W / 2 - dr.textlength(l, font=F(25)) / 2, H - hh - 12 + j * 34), l, font=F(25), fill=FG)
    if sc['first'] and t < d['lead']:                          # chapter title card, fading out
        a = 1.0 if t < d['lead'] - 0.6 else max(0, (d['lead'] - t) / 0.6)
        ov = Image.new('RGBA', img.size, (13, 19, 17, int(235 * a))); o = ImageDraw.Draw(ov)
        col = lambda c: c + (int(255 * a),)
        o.text((W / 2 - o.textlength(f"Chapter {sc['ch'] + 1}", font=F(28)) / 2, 270), f"Chapter {sc['ch'] + 1}", font=F(28), fill=col(YEL))
        o.text((W / 2 - o.textlength(sc['chTitle'], font=F(52, True)) / 2, 320), sc['chTitle'], font=F(52, True), fill=col(FG))
        o.text((W / 2 - o.textlength("Cyton + Daisy, from battery to brain waves", font=F(22)) / 2, 400), "Cyton + Daisy, from battery to brain waves", font=F(22), fill=col(MUTED))
        img.alpha_composite(ov)
    return img.convert('RGB')

def slug(s): return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')

if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == 'preview':                          # preview scene frame
        i, f = int(args[1]), int(args[2]); frame(i, f, captions(i), json.load(open(f'{D}/raw/s{i:02d}_labels.json'))).save(f'{D}/prev_{i}_{f}.jpg'); sys.exit()
    os.makedirs(f'{D}/out', exist_ok=True); chfiles = []
    def ts(x): return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}"
    full, t0, chsrt = [], 0.0, {}
    for i, sc in enumerate(C):
        for a, b, c in captions(i):
            full.append((t0 + a, t0 + b, c)); chsrt.setdefault(sc['ch'], []).append((a + chsrt.get(('t', sc['ch']), 0.0), b + chsrt.get(('t', sc['ch']), 0.0), c))
        chsrt[('t', sc['ch'])] = chsrt.get(('t', sc['ch']), 0.0) + round(DU[i]['dur'] * FPS) / FPS
        t0 += round(DU[i]['dur'] * FPS) / FPS
    def wsrt(path, items): open(path, 'w').write('\n'.join(f"{k + 1}\n{ts(a)} --> {ts(b)}\n{c}\n" for k, (a, b, c) in enumerate(items)))
    wsrt(f'{D}/out/Cyton_Daisy_course_full.srt', full)
    for ch in range(NCH):
        idx = [i for i, s in enumerate(C) if s['ch'] == ch]; name = f"{D}/out/ch{ch + 1:02d}_{slug(C[idx[0]]['chTitle'])}"
        wsrt(f'{name}.srt', chsrt[ch])
        enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', '-preset', 'medium', f'{name}_v.mp4'], stdin=subprocess.PIPE)
        for i in idx:
            caps, labels = captions(i), json.load(open(f'{D}/raw/s{i:02d}_labels.json'))
            for f in range(round(DU[i]['dur'] * FPS)): frame(i, f, caps, labels).save(enc.stdin, 'JPEG', quality=92)
        enc.stdin.close(); enc.wait()
        lst = f'{D}/out/ch{ch + 1:02d}_a.txt'; parts = []
        for i in idx:
            w = f'{D}/out/a{i:02d}.wav'
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{D}/audio/s{i:02d}.wav', '-af', f'apad=whole_dur={round(DU[i]["dur"] * FPS) / FPS}', '-t', f'{round(DU[i]["dur"] * FPS) / FPS}', '-ar', '44100', '-ac', '2', w], check=True)
            parts.append(f"file '{w}'")
        open(lst, 'w').write('\n'.join(parts))
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'pcm_s16le', f'{name}_a.wav'], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{name}_v.mp4', '-i', f'{name}_a.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{name}.mp4'], check=True)
        os.remove(f'{name}_v.mp4'); os.remove(f'{name}_a.wav'); chfiles.append(f'{name}.mp4'); print('chapter', ch + 1, 'done', flush=True)
    open(f'{D}/out/all.txt', 'w').write('\n'.join(f"file '{p}'" for p in chfiles))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{D}/out/all.txt', '-c', 'copy', '-movflags', '+faststart', f'{D}/out/Cyton_Daisy_course_full.mp4'], check=True)
    print('DONE')
