# -*- coding: utf-8 -*-
"""그림 한 장씩 검수: 원본/현재본을 크게 보고 통과·GPT 재작업·Claude 수정을 고르면 review/그림_검수.json 에 바로 저장한다.

  python tools/review_images.py [포트=8765]   → 브라우저로 http://localhost:8765
보스 배너처럼 BL/BR 로 나뉜 그림은 이어 붙여 한 장으로 보여 준다(결과는 두 파일 모두에 적용).
"""
import os, sys, csv, json, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, 'images', '게임내')
CUR = os.path.join(ROOT, 'images', 'GPT', '게임내')
SAVE = os.path.join(ROOT, 'review', '그림_검수.json')


def units():
    meta = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'translation', 'graphics.csv'), encoding='utf-8-sig')):
        meta[r['분류'] + '/' + r['파일']] = r
    rels = sorted(os.path.relpath(os.path.join(d, f), ORIG).replace(os.sep, '/')
                  for d, _, fs in os.walk(ORIG) for f in fs if f.endswith('.png'))
    out, seen = [], set()
    for rel in rels:
        if rel in seen:
            continue
        parts = [rel]
        if '_BL_' in rel and rel.replace('_BL_', '_BR_') in rels:
            parts.append(rel.replace('_BL_', '_BR_'))
        elif '_BR_' in rel and rel.replace('_BR_', '_BL_') in rels:
            continue                    # BL 쪽에서 함께 처리
        seen.update(parts)
        m = meta.get(rel, {})
        out.append({'id': rel, 'cat': rel.split('/')[0], 'parts': parts,
                    'cur': [os.path.exists(os.path.join(CUR, p)) for p in parts],
                    'info': '%s×%s %s' % (m.get('너비', '?'), m.get('높이', '?'), m.get('포맷', ''))})
    return out


def load():
    return json.load(open(SAVE, encoding='utf-8')) if os.path.exists(SAVE) else {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urllib.parse.unquote(self.path.split('?')[0])
        if p == '/':
            return self.send(200, PAGE.encode(), 'text/html; charset=utf-8')
        if p == '/data':
            return self.send(200, json.dumps({'units': units(), 'done': load()}, ensure_ascii=False).encode(), 'application/json')
        for pre, base in (('/o/', ORIG), ('/c/', CUR)):
            if p.startswith(pre):
                f = os.path.normpath(os.path.join(base, p[len(pre):]))
                if f.startswith(base) and os.path.isfile(f):
                    return self.send(200, open(f, 'rb').read(), 'image/png')
        self.send(404, b'', 'text/plain')

    def do_POST(self):
        if self.path != '/save':
            return self.send(404, b'', 'text/plain')
        d = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        done = load()
        if d.get('result'):
            done[d['id']] = {'result': d['result'], 'memo': d.get('memo', ''), 'parts': d['parts'],
                             'time': time.strftime('%Y-%m-%d %H:%M:%S')}
        else:
            done.pop(d['id'], None)
        tmp = SAVE + '.tmp'
        json.dump(done, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        os.replace(tmp, SAVE)
        self.send(200, b'{"ok":true}', 'application/json')


PAGE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>그림 한 장씩 검수</title>
<style>
:root{--bg:#17171a;--card:#212125;--ink:#ececea;--sub:#9a9a96;--line:#34343a;--ok:#3fa66b;--gpt:#d6862f;--me:#5b8def}
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--ink);font:14px/1.5 "Malgun Gothic",system-ui,sans-serif}
.wrap{display:flex;flex-direction:column;height:100%}
header{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;padding:8px 14px;border-bottom:1px solid var(--line)}
header b{font-size:15px}
.sub{color:var(--sub);font-size:13px}
.prog{flex:1;min-width:120px;height:6px;background:var(--line);border-radius:3px;overflow:hidden}
.prog i{display:block;height:100%;background:var(--ok)}
.view{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);grid-template-rows:minmax(0,1fr);gap:10px;padding:10px 14px}
@media (max-aspect-ratio:1/1){.view{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1fr) minmax(0,1fr)}}
.side{min-height:0;display:flex;flex-direction:column}
.side .lab{font-size:12px;color:var(--sub);margin-bottom:4px}
.stage{flex:1;min-height:0;position:relative;border-radius:6px;overflow:hidden}
.stage canvas{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);image-rendering:pixelated}
.bg-black .stage{background:#000}.bg-white .stage{background:#fff}
.bg-check .stage{background:repeating-conic-gradient(#888 0 25%,#bbb 0 50%) 0 0/16px 16px}
footer{border-top:1px solid var(--line);padding:8px 14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
button{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 12px;cursor:pointer}
button.on{outline:2px solid var(--ink)}
.ok{border-color:var(--ok)}.gpt{border-color:var(--gpt)}.me{border-color:var(--me)}
textarea{flex:1;min-width:200px;height:38px;font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px}
.state{font-weight:600}
.k{color:var(--sub);font-size:12px}
</style></head>
<body class="bg-black"><div class="wrap">
<header>
<b id="title">불러오는 중…</b><span class="sub" id="info"></span>
<div class="prog"><i id="bar"></i></div><span class="sub" id="count"></span>
<span class="sub">바탕</span><button data-bg="black" class="on">검정</button><button data-bg="check">체크</button><button data-bg="white">흰색</button>
<button id="rgb">색만 보기(V)</button>
</header>
<div class="view">
<div class="side"><div class="lab">원본</div><div class="stage"><canvas id="co"></canvas></div></div>
<div class="side"><div class="lab">현재본</div><div class="stage"><canvas id="cc"></canvas></div></div>
</div>
<footer>
<button id="prev">← 이전</button>
<button class="ok" data-r="통과">통과 (Enter)</button>
<button class="gpt" data-r="GPT 재작업">GPT 재작업 (G)</button>
<button class="me" data-r="Claude 수정">Claude 수정 (C)</button>
<textarea id="memo" placeholder="리뷰 메모 (GPT/Claude 고를 때 적어 줘)"></textarea>
<button id="next">다음 →</button>
<span class="state" id="state"></span>
<span class="k">←/→ 이동 · Enter 통과 · G·C 메모와 함께 저장 · V 색만(투명도 무시) · U 결과 지우기 · N 다음 미검수</span>
</footer>
</div>
<script>
let U=[],DONE={},i=0,RGB=false,PEND='',SEQ=0;
const $=id=>document.getElementById(id);
function loadImg(src){return new Promise(r=>{const m=new Image();m.onload=()=>r(m);m.onerror=()=>r(null);m.src=src})}
async function paint(cv,base,u,have,seq){
  const ims=await Promise.all(u.parts.map((p,k)=>have[k]?loadImg(base+encodeURIComponent(p).replace(/%2F/g,'/')):null));
  if(seq!==SEQ)return;  // 그사이 다른 장으로 넘어갔으면 그리지 않음
  const ok=ims.filter(Boolean);const ctx=cv.getContext('2d');
  if(!ok.length){cv.width=300;cv.height=60;ctx.fillStyle='#888';ctx.font='16px sans-serif';ctx.fillText('현재본 없음(원본 그대로 씀)',10,35);return}
  cv.width=ok.reduce((s,m)=>s+m.width,0);cv.height=Math.max(...ok.map(m=>m.height));
  let x=0;for(const m of ok){ctx.drawImage(m,x,0);x+=m.width}
  if(RGB){const d=ctx.getImageData(0,0,cv.width,cv.height);for(let k=3;k<d.data.length;k+=4)d.data[k]=255;ctx.putImageData(d,0,0)}
}
function fit(){for(const cv of [$('co'),$('cc')]){const st=cv.parentElement,f=Math.min(st.clientWidth/cv.width,st.clientHeight/cv.height);
  const z=f;cv.style.width=cv.width*z+'px';cv.style.height=cv.height*z+'px'}}
async function show(){
  const seq=++SEQ,u=U[i];$('title').textContent=u.parts.map(p=>p.split('/').pop()).join(' + ');
  $('info').textContent=u.cat+' · '+u.info+' · '+(i+1)+'번째';
  PEND='';const d=DONE[u.id];$('memo').value=d?d.memo:'';
  $('state').textContent=d?('결과: '+d.result):'아직 안 봄';
  document.querySelectorAll('[data-r]').forEach(b=>b.classList.toggle('on',!!d&&b.dataset.r===d.result));
  await Promise.all([paint($('co'),'/o/',u,u.parts.map(()=>true),seq),paint($('cc'),'/c/',u,u.cur,seq)]);if(seq===SEQ)fit();count()}
function count(){const n=Object.keys(DONE).length;$('count').textContent=`${n} / ${U.length} 검수 · 리뷰 ${Object.values(DONE).filter(x=>x.result!=='통과').length}건`;$('bar').style.width=(100*n/U.length)+'%'}
async function save(r){const u=U[i],memo=$('memo').value.trim();
  if(r&&r!=='통과'&&!memo){PEND=r;$('memo').focus();$('state').textContent=r+': 메모 적고 Enter';return}
  PEND='';
  await fetch('/save',{method:'POST',body:JSON.stringify({id:u.id,parts:u.parts,result:r,memo})});
  if(r)DONE[u.id]={result:r,memo};else delete DONE[u.id];
  if(r){nextTodo()}else show()}
function go(k){i=Math.max(0,Math.min(U.length-1,k));show()}
function nextTodo(){for(let k=1;k<=U.length;k++){const j=(i+k)%U.length;if(!DONE[U[j].id]){go(j);return}}$('state').textContent='전부 검수 끝!';show()}
document.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>save(b.dataset.r));
$('prev').onclick=()=>go(i-1);$('next').onclick=()=>go(i+1);
$('rgb').onclick=()=>{RGB=!RGB;$('rgb').classList.toggle('on',RGB);show()};
document.querySelectorAll('[data-bg]').forEach(b=>b.onclick=()=>{document.body.className='bg-'+b.dataset.bg;document.querySelectorAll('[data-bg]').forEach(x=>x.classList.toggle('on',x===b))});
addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'){if(e.key==='Escape')e.target.blur();if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.target.blur();if(PEND)save(PEND)}return}
  const k=e.key.toLowerCase();if(k==='arrowleft')go(i-1);else if(k==='arrowright')go(i+1);else if(k==='enter')save('통과');
  else if(k==='g')save('GPT 재작업');else if(k==='c')save('Claude 수정');else if(k==='v')$('rgb').click();else if(k==='u')save('');else if(k==='n')nextTodo()});
addEventListener('resize',fit);
fetch('/data').then(r=>r.json()).then(d=>{U=d.units;DONE=d.done;i=Math.max(0,U.findIndex(u=>!DONE[u.id]));show()});
</script></body></html>'''

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print('그림 검수: http://localhost:%d  (결과 %s)' % (port, SAVE), flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
