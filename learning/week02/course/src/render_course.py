import json, subprocess, re, html, base64, os, sys
D = os.path.dirname(os.path.abspath(__file__)); FPS = 15
durs = json.load(open(f'{D}/durs.json')); os.makedirs(f'{D}/raw', exist_ok=True)
stills = '--stills' in sys.argv
only = [int(a) for a in sys.argv[1:] if a.isdigit()]
def chrome(q):
    prof = f'{D}/prof'; subprocess.run(['rm', '-rf', prof])
    for attempt in range(3):
        subprocess.run(['rm', '-rf', prof])
        try:
            out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                '--force-device-scale-factor=1', f'--user-data-dir={prof}', '--allow-file-access-from-files', '--window-size=1280,900', '--virtual-time-budget=150000',
                '--dump-dom', f'file://{D}/cpage.html?{q}'], capture_output=True, text=True, timeout=600).stdout
        except subprocess.TimeoutExpired:
            print('timeout', q, flush=True); continue
        m = re.search(r'id="vout">VOUT_BEGIN(\[.*?\])VOUT_END', out, re.S)
        if m:
            fr = json.loads(html.unescape(m.group(1)))
            if fr and isinstance(fr[0], dict): return fr
        print('retry', attempt + 1, q, flush=True)
    return None
for sc, d in enumerate(durs):
    if only and sc not in only: continue
    if stills:
        fr = chrome(f'scene={sc}&f0=0&f1=0&stills=1')
        if fr is None: print('FAILED stills', sc, flush=True); continue
        os.makedirs(f'{D}/stills', exist_ok=True)
        for x in fr: open(f'{D}/stills/s{sc:02d}_{x["shot"]}.jpg', 'wb').write(base64.b64decode(x['img'].split(',')[1]))
        json.dump(fr and [[x['shot'], x['labels']] for x in fr], open(f'{D}/stills/s{sc:02d}.json', 'w')); print('stills', sc, flush=True); continue
    n = round(d['dur'] * FPS)
    if os.path.exists(f'{D}/raw/s{sc:02d}_labels.json'): continue          # resume support
    lp = f'{D}/raw/s{sc:02d}_partial.json'; labels = json.load(open(lp)) if os.path.exists(lp) else {}
    for f0 in range(0, n, 50):
        f1 = min(n, f0 + 50)
        if all(str(f) in labels for f in range(f0, f1)): continue
        fr = chrome(f'scene={sc}&f0={f0}&f1={f1}')
        if fr is None: print('FAILED', sc, f0, flush=True); sys.exit(1)
        for x in fr:
            open(f'{D}/raw/s{sc:02d}_{x["f"]:05d}.jpg', 'wb').write(base64.b64decode(x['img'].split(',')[1])); labels[str(x['f'])] = x['labels']
        json.dump(labels, open(lp, 'w'))
    json.dump(labels, open(f'{D}/raw/s{sc:02d}_labels.json', 'w')); print('scene', sc, 'done', n, 'frames', flush=True)
print('DONE')
