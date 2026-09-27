# 후보 텍스처를 PNG 로 (md5 중복 제거), 목록 CSV
import sys, os, json, csv
sys.path.insert(0, os.path.dirname(__file__))
import cgfx
jp = json.load(open('work/tex_jp.json', encoding='utf-8'))
us = json.load(open('work/tex_us.json', encoding='utf-8'))
usmd5 = {}
for r in us:
    if r['path'].startswith('us/'):
        usmd5.setdefault((r['path'][3:], r['name']), []).append(r)
OUT = 'images/jp'; OUTUS = 'images/us_ref'
os.makedirs(OUT, exist_ok=True); os.makedirs(OUTUS, exist_ok=True)
groups = {}
for r in jp:
    us_l = usmd5.get((r['path'][3:], r['name']))
    if us_l and any(x['md5'] == r['md5'] for x in us_l):
        continue
    u = us_l[0] if us_l else None
    groups.setdefault(r['md5'], []).append((r, u))
cache = {}
def load(p):
    if p not in cache:
        cache.clear(); cache[p] = open(p, 'rb').read()
    return cache[p]
rows = []
for md5, lst in sorted(groups.items(), key=lambda x: (x[1][0][0]['path'], x[1][0][0]['name'])):
    r, u = lst[0]
    area = r['path'].split('/')[1] if r['path'].split('/')[1] not in ('0.arc', '00.arc') else 'resident'
    sub = r['path'].split('/')[2] if area in ('menu', 'info', 'stage', 'doll') else ''
    fn = '%s_%s_%s.png' % (area, sub.replace('.zrc', ''), r['name'])
    fn = fn.replace('__', '_')
    d = load('unpack/jp/' + r['path'])
    t = (r['name'], r['w'], r['h'], [k for k, v in cgfx.NAMES.items() if v == r['fmt']][0], r['off'], r['size'])
    cgfx.decode(d, t).save(os.path.join(OUT, fn))
    if u:
        du = open('unpack/us/' + u['path'], 'rb').read()
        tu = (u['name'], u['w'], u['h'], [k for k, v in cgfx.NAMES.items() if v == u['fmt']][0], u['off'], u['size'])
        cgfx.decode(du, tu).save(os.path.join(OUTUS, fn))
    rows.append([fn, r['name'], r['w'], r['h'], r['fmt'], len(lst), ' | '.join(sorted({x[0]['path'] for x in lst})), 'Y' if u else ''])
with open('images/목록.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['파일', '텍스처명', '너비', '높이', '포맷', '사용처수', '원본경로', '북미판대응'])
    w.writerows(rows)
print(len(rows), 'images')
