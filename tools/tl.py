# -*- coding: utf-8 -*-
"""번역 관리 도구.

  python tools/tl.py prep                  원문 단위 만들기 → translation/units.json (같은 원문은 한 단위)
  python tools/tl.py dump <묶음> <카테고리|파일접두> [시작] [끝]
                                           원문 묶음 → work/src/<묶음>.json
  python tools/tl.py check <묶음>          translation/batches/<묶음>.json 검사(반영 안 함)
  python tools/tl.py apply                 모든 묶음 → translation/ko.json
  python tools/tl.py status                진행 현황

단위 키(key)는 그 원문을 쓰는 첫 메시지 id(파일#라벨). 번역 묶음 파일 형식: {"key": "번역문", ...}
편집 문자열: 줄바꿈은 실제 \n, 태그는 {0.2:6400} 식(원문에서 그대로 복사). 후리가나는 원문에서 이미 뺐다.
"""
import sys, os, re, json, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
import bcfnt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'translation')
UNITS = os.path.join(T, 'units.json')
SRC = os.path.join(ROOT, 'work', 'src')
TAG = re.compile(r'\{[^}]*\}')

_font = None


def font():
    global _font
    if _font is None:
        p = os.path.join(ROOT, 'work', 'font', 'cbf_std_ko.bcfnt')   # tools/build_sysfont.py 가 만든다
        _font = bcfnt.parse(open(p, 'rb').read()) if os.path.exists(p) else False
    return _font


def width(line):
    f = font()
    if not f:          # 폰트가 없으면 어림값(전각 24px, 반각 12px)
        return sum(24 if ord(ch) > 0xff else 12 for ch in TAG.sub('', line))
    w = 0
    for ch in TAG.sub('', line):
        i = f.cmap.get(ord(ch))
        w += f.widths[i][2] if i is not None else 24
    return w


def strip_ruby(s):
    return re.sub(r'\{ruby:([^|]*)\|[^}]*\}', r'\1', s)


# 카테고리별 줄 폭 한도(px). 원문 최대치 기준. 메뉴·UI 는 단위별 원문 폭을 따로 본다.
CAT_LIMIT = {'스토리 대사(공중전)': 552, '스토리 대사(지상전)': 504, '대사(H)': 504, '지상전 잡담(R)': 504,
             '도감': 624, '시스템 메시지·팁': 624,
             '스태프롤': 280}  # 스태프롤은 전용 폰트(fnt.bin), 북미판 로마자 이름 최대 폭 기준


def prep():
    rows = json.load(open(os.path.join(ROOT, 'text', '신광신화_전체텍스트.json'), encoding='utf-8'))
    units = collections.OrderedDict()
    for r in rows:
        s = strip_ruby(r['jp'])
        if not TAG.sub('', s).strip():
            continue
        u = units.get(s)
        if u is None:
            u = units[s] = dict(key=r['id'], cat=r['category'], stage=r['stage'], label=r['label'],
                                speaker=r['speaker'], jp=s, en=r['en_plain'], ids=[], speakers=[])
        u['ids'].append(r['id'])
        if r['speaker'] and r['speaker'] not in u['speakers']:
            u['speakers'].append(r['speaker'])
    out = []
    for u in units.values():
        u['jp_px'] = max(width(l) for l in u['jp'].split('\n'))
        u['limit'] = max(CAT_LIMIT[u['cat']], u['jp_px']) if u['cat'] in CAT_LIMIT else 0
        out.append(u)
    os.makedirs(T, exist_ok=True)
    json.dump(out, open(UNITS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('단위 %d개 → %s' % (len(out), UNITS))


def load_units():
    return json.load(open(UNITS, encoding='utf-8'))


def dump(name, sel, a=None, b=None):
    us = [u for u in load_units() if u['cat'] == sel or u['key'].startswith(sel)]
    us = us[int(a) if a else 0:int(b) if b else None]
    os.makedirs(SRC, exist_ok=True)
    rows = [dict(key=u['key'], speaker='/'.join(u['speakers']), label=u['label'], jp=u['jp'], en=u['en'],
                 max_px=(u['limit'] or u['jp_px'])) for u in us]
    json.dump(rows, open(os.path.join(SRC, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%s: %d개 (%s ~ %s)' % (name, len(rows), rows[0]['key'] if rows else '', rows[-1]['key'] if rows else ''))


KANA = re.compile(r'[぀-ヿ一-鿿]')


def check_one(u, ko):
    """(오류 목록, 경고 목록)"""
    err, warn = [], []
    jt = collections.Counter(TAG.findall(u['jp']))
    kt = collections.Counter(TAG.findall(ko))
    if jt != kt:
        err.append('태그 불일치 %s → %s' % (dict(jt), dict(kt)))
    if ko.count('\n') > u['jp'].count('\n'):
        err.append('줄 수 초과(원문 %d줄, 번역 %d줄)' % (u['jp'].count('\n') + 1, ko.count('\n') + 1))
    f = font()
    miss = sorted({ch for ch in TAG.sub('', ko) if f and ord(ch) not in f.cmap and ch != '\n'})
    if miss:
        err.append('폰트에 없는 글자 %s' % ''.join(miss))
    left = KANA.findall(TAG.sub('', ko))
    if left and not KANA.findall(u['en'] or ''):
        warn.append('일본어·한자 남음 %s' % ''.join(left))
    lim = u['limit'] or u['jp_px']
    for line in ko.split('\n'):
        w = width(line)
        if u['limit'] and w > lim:
            err.append('줄 폭 %dpx > %dpx: %s' % (w, lim, line))
        elif not u['limit'] and w > lim:
            (err if w > lim * 1.35 + 24 else warn).append('원문보다 넓음 %dpx(원문 %dpx): %s' % (w, lim, line))
    if '~.' in ko or '~,' in ko:
        err.append('물결표 뒤 부호')
    if '그녀' in ko:
        warn.append('그녀 사용')
    if '　' in ko and '　' not in u['jp']:
        warn.append('전각 공백')
    return err, warn


def check(name, quiet=False):
    us = {u['key']: u for u in load_units()}
    p = os.path.join(T, 'batches', name + '.json')
    ko = json.load(open(p, encoding='utf-8'))
    ne = nw = 0
    for k, v in ko.items():
        if k not in us:
            print('[오류] 없는 키', k); ne += 1; continue
        e, w = check_one(us[k], v)
        for x in e:
            print('[오류]', k, x); ne += 1
        if not quiet:
            for x in w:
                print('[경고]', k, x); nw += 1
    srcp = os.path.join(SRC, name + '.json')
    if os.path.exists(srcp):
        src = [r['key'] for r in json.load(open(srcp, encoding='utf-8'))]
        miss = [k for k in src if k not in ko]
        if miss:
            print('[오류] 미번역 %d개: %s' % (len(miss), ', '.join(miss[:5])))
            ne += len(miss)
    print('%s: %d개, 오류 %d, 경고 %d' % (name, len(ko), ne, nw))
    return ne


def apply():
    allko = {}
    for p in sorted(glob.glob(os.path.join(T, 'batches', '*.json'))):
        allko.update(json.load(open(p, encoding='utf-8')))
    json.dump(allko, open(os.path.join(T, 'ko.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('반영 %d개 → translation/ko.json' % len(allko))


def status():
    us = load_units()
    ko = {}
    for p in glob.glob(os.path.join(T, 'batches', '*.json')):
        ko.update(json.load(open(p, encoding='utf-8')))
    c = collections.Counter(); d = collections.Counter()
    for u in us:
        c[u['cat']] += 1
        d[u['cat']] += u['key'] in ko
    for k in c:
        print('%-16s %5d / %5d' % (k, d[k], c[k]))
    print('합계 %d / %d' % (sum(d.values()), len(us)))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'prep':
        prep()
    elif cmd == 'dump':
        dump(*sys.argv[2:])
    elif cmd == 'check':
        sys.exit(1 if check(sys.argv[2], '--quiet' in sys.argv) else 0)
    elif cmd == 'apply':
        apply()
    elif cmd == 'status':
        status()
