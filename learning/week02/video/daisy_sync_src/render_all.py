import json,subprocess,re,html,base64,os,sys
D=os.path.dirname(os.path.abspath(__file__)); FPS=15
durs=json.load(open(f'{D}/durs.json')); os.makedirs(f'{D}/raw',exist_ok=True); labels={}
for sc,d in enumerate(durs):
    n=round(d*FPS)
    for f0 in range(0,n,150):
        f1=min(n,f0+150)
        subprocess.run(f'rm -rf "{D}/prof"',shell=True)
        out=subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--headless=new','--use-angle=swiftshader','--enable-unsafe-swiftshader','--force-device-scale-factor=1',f'--user-data-dir={D}/prof','--allow-file-access-from-files','--window-size=1280,900','--virtual-time-budget=120000','--dump-dom',f'file://{D}/vpage.html?scene={sc}&dur={d}&f0={f0}&f1={f1}'],capture_output=True,text=True).stdout
        m=re.search('VOUT_BEGIN(.*?)VOUT_END',out,re.S)
        if not m: print('FAILED',sc,f0,flush=True); sys.exit(1)
        for fr in json.loads(html.unescape(m.group(1))):
            open(f'{D}/raw/s{sc}_{fr["f"]:04d}.jpg','wb').write(base64.b64decode(fr['img'].split(',')[1]))
            labels[f's{sc}_{fr["f"]:04d}']=fr['labels']
        print('scene',sc,'frames',f0,f1,'of',n,flush=True)
json.dump(labels,open(f'{D}/labels.json','w')); print('DONE')
