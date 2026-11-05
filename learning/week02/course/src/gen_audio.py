import json, urllib.request, os, subprocess, time
D = os.path.dirname(os.path.abspath(__file__))
k = open(os.path.expanduser('~/.config/elevenlabs/key')).read().strip()
C = json.load(open(f'{D}/course.json')); durs = []
for i, sc in enumerate(C):
    mp3 = f'{D}/audio/s{i:02d}.mp3'
    if not os.path.exists(mp3):
        body = json.dumps({"text": sc["tts"], "model_id": "eleven_multilingual_v2",
                           "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": 0.95}}).encode()
        for attempt in range(4):
            try:
                req = urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL?output_format=mp3_44100_128',
                                             data=body, headers={'xi-api-key': k, 'Content-Type': 'application/json'})
                open(mp3, 'wb').write(urllib.request.urlopen(req, timeout=180).read()); break
            except urllib.error.HTTPError as e:
                msg = e.read()[:300]; print('scene', i, 'HTTP', e.code, msg, flush=True)
                if e.code in (401, 402, 403) or b'quota' in msg: raise SystemExit(1)
                time.sleep(5 * (attempt + 1))
            except Exception as e:
                print('scene', i, 'error', e, flush=True); time.sleep(5 * (attempt + 1))
        else: raise SystemExit(1)
    lead = 3.5 if sc["first"] else 0.4
    wav = f'{D}/audio/s{i:02d}.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp3, '-af', f'adelay={int(lead*1000)}:all=1,apad=pad_dur=0.8', '-ar', '44100', '-ac', '2', wav], check=True)
    d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', wav], capture_output=True, text=True).stdout)
    durs.append({"dur": round(d, 2), "lead": lead}); print('scene', i, round(d, 1), 's', flush=True)
json.dump(durs, open(f'{D}/durs.json', 'w')); print('TOTAL', round(sum(x["dur"] for x in durs) / 60, 1), 'min')
