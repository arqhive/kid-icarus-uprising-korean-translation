# -*- coding: utf-8 -*-
"""그림 글씨 현황판: 원본(images/게임내)과 현재본(images/GPT/게임내)을 나란히 보는 HTML.

  python tools/make_gallery.py   → review/그림_현황판.html (그림을 data URI로 넣어 파일 하나로 열림)
"""
import os, csv, json, time, html, base64

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, 'images', '게임내')
CUR = os.path.join(ROOT, 'images', 'GPT', '게임내')
OUT = os.path.join(ROOT, 'review', '그림_현황판.html')


def uri(p):
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()


def main():
    meta = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'translation', 'graphics.csv'), encoding='utf-8-sig')):
        meta[r['분류'] + '/' + r['파일']] = r
    items = []
    for d, _, fs in os.walk(ORIG):
        for f in fs:
            if not f.endswith('.png'):
                continue
            rel = os.path.relpath(os.path.join(d, f), ORIG).replace(os.sep, '/')
            cur = os.path.join(CUR, rel)
            m = meta.get(rel, {})
            items.append({
                'cat': rel.split('/')[0], 'name': f[:-4], 'rel': rel,
                'cur': os.path.exists(cur),
                'mtime': os.path.getmtime(cur) if os.path.exists(cur) else 0,
                'w': int(m.get('너비') or 0), 'h': int(m.get('높이') or 0),
                'fmt': m.get('포맷', ''), 'uses': m.get('사용처수', ''),
                'o': uri(os.path.join(d, f)), 'c': uri(cur) if os.path.exists(cur) else '',
            })
    items.sort(key=lambda x: (x['cat'], x['name']))
    data = json.dumps(items, ensure_ascii=False)
    stamp = time.strftime('%Y-%m-%d %H:%M')
    open(OUT, 'w', encoding='utf-8').write(PAGE.replace('__DATA__', data).replace('__STAMP__', html.escape(stamp)))
    print('%s: 그림 %d장(현재본 %d장)' % (OUT, len(items), sum(x['cur'] for x in items)))


PAGE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>그림 글씨 현황판</title>
<style>
:root{--bg:#f4f4f2;--card:#fff;--ink:#1d1d1b;--sub:#6b6b66;--line:#ddddd8;--acc:#2f6fd6;--new:#d6492f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17171a;--card:#212125;--ink:#ececea;--sub:#9a9a96;--line:#34343a;--acc:#7aa7ff;--new:#ff7a5c}}
:root[data-theme="dark"]{--bg:#17171a;--card:#212125;--ink:#ececea;--sub:#9a9a96;--line:#34343a;--acc:#7aa7ff;--new:#ff7a5c}
*{box-sizing:border-box}
html,body{overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Malgun Gothic",system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:18px;margin:0 0 8px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.bar input,.bar select,.bar button{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
.bar button.on{border-color:var(--acc);color:var(--acc)}
.sum{color:var(--sub);font-size:13px}
main{padding:12px 16px 40px}
h2{font-size:15px;margin:22px 0 8px}
h2 small{color:var(--sub);font-weight:normal}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,var(--col,520px)),1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px}
.card.new{border-color:var(--new)}
.head{display:flex;flex-wrap:wrap;justify-content:space-between;gap:2px 8px;font-size:12px;color:var(--sub);margin-bottom:6px;word-break:break-all}
.head b{color:var(--ink);font-weight:600}
.tag{color:var(--new);font-weight:600}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.pair figure{margin:0;min-width:0}
.pair figcaption{font-size:11px;color:var(--sub)}
.box{border-radius:4px;overflow:hidden;display:flex;justify-content:center}
.box img{display:block;image-rendering:pixelated;max-width:100%;max-height:70vh;height:auto;object-fit:contain}
.bg-black .box{background:#000}
.bg-white .box{background:#fff}
.bg-check .box{background:repeating-conic-gradient(#999 0 25%,#ccc 0 50%) 0 0/16px 16px}
.none{font-size:12px;color:var(--sub);padding:12px}
</style></head>
<body class="bg-black">
<header>
<h1>그림 글씨 현황판</h1>
<div class="bar">
<input id="q" type="search" placeholder="이름 검색 (예: b093)">
<select id="cat"><option value="">전체 분류</option></select>
<select id="sort"><option value="cat">분류순</option><option value="new">최근 바뀐 순</option></select>
<span>바탕</span><button data-bg="black" class="on">검정</button><button data-bg="check">체크</button><button data-bg="white">흰색</button>
<span>배율</span><button data-z="1">1배</button><button data-z="2" class="on">2배</button><button data-z="3">3배</button>
<span class="sum" id="sum"></span>
</div>
<div class="sum">만든 때 __STAMP__ · 왼쪽 원본(images/게임내), 오른쪽 현재본(images/GPT/게임내) · 빨간 테두리 = 최근 24시간 안에 바뀐 그림</div>
</header>
<main id="main"></main>
<script>
const D=__DATA__;let Z=2;
const now=Math.max(...D.map(x=>x.mtime));
const cats=[...new Set(D.map(x=>x.cat))];
const sel=document.getElementById('cat');
cats.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c+' ('+D.filter(x=>x.cat===c).length+')';sel.appendChild(o)});
function esc(s){return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function img(src,x){return `<div class="box"><img loading="lazy" src="${src}" style="width:${x.w*Z}px" alt=""></div>`}
function card(x){
  const isNew=x.cur&&now-x.mtime<86400;
  return `<div class="card${isNew?' new':''}"><div class="head"><b>${esc(x.name)}</b><span>${x.w}×${x.h} ${esc(x.fmt)}${x.uses?' · 쓰인 곳 '+x.uses:''}${isNew?' · <span class="tag">최근 바뀜</span>':''}</span></div>
  <div class="pair"><figure><figcaption>원본</figcaption>${img(x.o,x)}</figure>
  <figure><figcaption>현재본</figcaption>${x.cur?img(x.c,x):'<div class="none">현재본 없음(원본 그대로 씀)</div>'}</figure></div></div>`}
function draw(){
  const q=document.getElementById('q').value.trim().toLowerCase(),c=sel.value,s=document.getElementById('sort').value;
  let L=D.filter(x=>(!c||x.cat===c)&&(!q||x.rel.toLowerCase().includes(q)));
  document.getElementById('sum').textContent=`${L.length}장 표시 / 전체 ${D.length}장 (현재본 ${D.filter(x=>x.cur).length}장)`;
  const m=document.getElementById('main');
  if(s==='new'){L=[...L].sort((a,b)=>b.mtime-a.mtime);m.innerHTML=`<div class="grid">${L.map(card).join('')}</div>`;return}
  m.innerHTML=cats.filter(k=>L.some(x=>x.cat===k)).map(k=>{const G=L.filter(x=>x.cat===k);return `<h2>${esc(k)} <small>${G.length}장</small></h2><div class="grid">${G.map(card).join('')}</div>`}).join('')}
document.querySelectorAll('[data-bg]').forEach(b=>b.onclick=()=>{document.body.className='bg-'+b.dataset.bg;document.querySelectorAll('[data-bg]').forEach(x=>x.classList.toggle('on',x===b))});
document.querySelectorAll('[data-z]').forEach(b=>b.onclick=()=>{Z=+b.dataset.z;document.documentElement.style.setProperty('--col',{1:'300px',2:'520px',3:'760px'}[Z]);document.querySelectorAll('[data-z]').forEach(x=>x.classList.toggle('on',x===b));draw()});
['q','cat','sort'].forEach(i=>document.getElementById(i).addEventListener('input',draw));
draw();
</script></body></html>'''

if __name__ == '__main__':
    main()
