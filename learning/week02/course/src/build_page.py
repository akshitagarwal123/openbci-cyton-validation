import json, os
D = os.path.dirname(os.path.abspath(__file__))
head = open(f'{D}/../cyton3d/preview.html').read().split('<title>')[0]
body = open(f'{D}/../cyton3d/cyton_3d.html').read()
css = '<style>#stage{position:fixed!important;left:0;top:0;width:1280px!important;height:720px!important;border:0!important;border-radius:0!important;z-index:5}</style>'
data = '<script>window.COURSE=' + open(f'{D}/course.json').read() + ';window.DURS=' + open(f'{D}/durs.json').read() + ';</script>'
open(f'{D}/cpage.html', 'w').write(head + css + data + body + '\n<script>' + open(f'{D}/course.js').read() + '</script></body></html>')
