import base64, json, os, re, subprocess, sys, urllib.request, urllib.error, time
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D); sys.path.insert(0, f'{D}/../course')
from narr import NARR
from course_spec import tts as _tts
EXTRA = [('VREFP','V-ref P'),('VREFN','V-ref N'),('PD_REFBUF','P.D. ref buffer'),('CONFIG3','CONFIG 3'),('X7R','X 7 R'),('X5R','X 5 R'),('C0G','C 0 G'),('AVDD','A.V.D.D.'),('AVSS','A.V.S.S.')]
def tts(s):
    for a, b in EXTRA: s = s.replace(a, b)
    return _tts(s)
k = open(os.path.expanduser('~/.config/elevenlabs/key')).read().strip()
os.makedirs(f'{D}/audio', exist_ok=True); out = []
for i, text in enumerate(NARR):
    ss = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text.strip()); tt = [tts(s) for s in ss]; full = ' '.join(tt)
    starts = [0]
    for x in tt[:-1]: starts.append(starts[-1] + len(x) + 1)
    mp3 = f'{D}/audio/s{i}.mp3'; tj = f'{D}/audio/s{i}.json'
    if not (os.path.exists(mp3) and os.path.exists(tj)):
        body = json.dumps({"text": full, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": 0.95}}).encode()
        for attempt in range(4):
            try:
                req = urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL/with-timestamps?output_format=mp3_44100_128', data=body, headers={'xi-api-key': k, 'Content-Type': 'application/json'})
                r = json.load(urllib.request.urlopen(req, timeout=180)); break
            except urllib.error.HTTPError as e:
                m = e.read()[:300]; print('scene', i + 1, 'HTTP', e.code, m, flush=True)
                if e.code in (401, 402, 403) or b'quota' in m: raise SystemExit(1)
                time.sleep(5 * (attempt + 1))
            except Exception as e: print('scene', i + 1, 'error', e, flush=True); time.sleep(5 * (attempt + 1))
        else: raise SystemExit(1)
        open(mp3, 'wb').write(base64.b64decode(r['audio_base64'])); st = r['alignment']['character_start_times_seconds']
        json.dump({"starts": [st[min(s, len(st) - 1)] for s in starts], "nchar": len(r['alignment']['characters']), "nfull": len(full)}, open(tj, 'w'))
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3], capture_output=True, text=True).stdout)
    t = json.load(open(tj)); out.append({"audio": dur, "starts": t["starts"]}); print('scene', i + 1, round(dur, 1), 's', t["starts"][:4], 'chars ok' if t["nchar"] == t["nfull"] else f'CHAR MISMATCH {t["nchar"]} vs {t["nfull"]}', flush=True)
json.dump(out, open(f'{D}/timing.json', 'w')); print('TOTAL', round(sum(x['audio'] for x in out) / 60, 2), 'min')
