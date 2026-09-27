# -*- coding: utf-8 -*-
"""일본판 MSBT 전량 추출 + 화자 판별 + 북미판 영어 대조.

  python tools/extract_text.py
  → text/신광신화_전체텍스트.json, text/신광신화_전체텍스트.tsv, text/화자별_집계.tsv

화자 판별 (스테이지 대사 MSBT 의 ATR1 11바이트):
  byte0 = 얼굴 코드 + 1 (0 이면 초상화 없음), byte3 = 1 이면 피트 쪽 대사.
  얼굴 코드는 캐릭터마다 구간이 정해져 있다 (SPEAKERS). 구간 → 초상화 FB 번호 오프셋은
  info/*.zrc 의 FB_nnn 텍스처와 장별로 대조해 확정했다.
  초상화 없는 대사는 byte3=1 이면 피트, 아니면 주변 대사에서 상대 화자를 추정한다.
"""
import sys, os, re, json, struct, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
import msbt, msgtext, list_msbt

JP = 'unpack/jp'
US = 'unpack/us'
OUT = 'text'

# (코드 시작, 끝, 일본어 이름, 영어 이름, FB 오프셋)
SPEAKERS = [
    (0, 23, 'ピット', 'Pit', 0),
    (24, 29, 'メデューサ', 'Medusa', 86),
    (30, 45, 'パルテナ', 'Palutena', 0),
    (46, 59, 'ハデス', 'Hades', 25),
    (60, 76, 'ナチュレ', 'Viridi', -10),
    (77, 79, 'アロン', 'Arlon', 113),
    (80, 89, 'ブラックピット', 'Dark Pit', 10),
    (90, 94, 'ラーズ', 'Pyrrhon', 40),
    (95, 95, 'オーラムラーズ', 'Aurum Pyrrhon', 40),
    (96, 99, '親衛隊', 'Centurions', 174),
    (100, 105, 'エレカ', 'Phosphora', 50),
    (106, 108, 'パンドーラ', 'Pandora', 68),
    (110, 112, 'タナトス', 'Thanatos', 150),
    (115, 117, 'ポセイドン', 'Poseidon', 125),
    (120, 124, 'ヒュードラー', 'Hewdraw', 100),
    (125, 129, 'マグナ', 'Magnus', 15),
    (130, 133, 'ディントス', 'Dyntos', 30),
    (134, 134, '魔王ガイナス', 'Dark Lord Gaol', 96),
    (135, 138, 'パンドーラ', 'Pandora', 35),
    (139, 139, 'パルテナもどき', 'Pseudo-Palutena', 71),
    (140, 142, 'パンドーラ', 'Pandora', 40),
    (143, 144, '戦車の主', 'Chariot Master', 57),
    (145, 145, 'メデューサ', 'Medusa', -30),
    (146, 148, 'ヒュードラー', 'Hewdraw', 79),
]
PIT = ('ピット', 'Pit')

# 초상화도 피트 표시도 없는 대사 — 문맥(앞뒤 대사·영어판)으로 판정
_P = ('パルテナ', 'Palutena'); _N = ('ナチュレ', 'Viridi'); _R = ('ラーズ', 'Pyrrhon')
_H = ('ハデス', 'Hades'); _M = ('メデューサ', 'Medusa')
MANUAL = {
    'a1000#A176_07': _P,                       # 길 안내
    'a1400#A235_01': None,                     # 「電光の? エレカ?」 피트는 아님(byte3=0). 타나토스 추정, 미확정
    'a1500#A260_04': _R, 'a1500#A261_01': _R,  # 화면 밖 웃음 → 이어서 래즈 등장
    'a1700#A291_03': _R, 'a1700#A292_01': _R, 'a1700#A293_01': _R,
    'a1700#A294_01': _R, 'a1700#A294_02': _R, 'a1700#A294_03': _R, 'a1700#A294_05': _R,
    'a1800#A309_02': _N,
    'a2100#A348_03': _N, 'a2100#A348_04': _N, 'a2100#A348_05': _N, 'a2100#A348_07': _N,
    'a2400#A414_01': ('ディントス', 'Dyntos'),
    'a2200#A367_04': None,                     # 「そうですとも!」 반지 속 피트 가능성, 미확정
    'a2600#A500_06': _P,                       # 4장 A061_05 인용
    'a2600#A500_22': ('エレカ', 'Phosphora'),  # 14장 G401_06 인용
    'a2600#A500_32': ('戦車の主', 'Chariot Master'),  # 19장 G563_08 인용
    'a2600#A500_16': _N,
    'a2600#A500_44': PIT, 'a2600#A500_45': _H, 'a2600#A500_46': PIT,   # 서로 이름을 외치는 장면
    'a2600#*': {'A501': _H},                   # 엔딩 뒤 하데스 독백
    'b0906#G254_01': _M, 'b0906#G254_02': _M, 'b0906#G254_03': _M,
    'g0500#G114_03': ('パンドーラ', 'Pandora'),
}

# 초상화 코드가 있어도 실제 화자가 다른 대사(화면 밖 목소리, 초상화는 직전 인물 것이 남음) — 1차 검수에서 확인
OVERRIDE = {
    'b0906#G271_01': _H, 'b0906#G272_01': _H, 'b0906#G273_01': _H,   # 9장 끝, 바로 뒤 「ハデス!!」
    'g2300#G689_01': _H,
}


def speaker_of(code):
    for lo, hi, jp, en, off in SPEAKERS:
        if lo <= code <= hi:
            return jp, en, code + off
    return None


def category(path, label):
    parts = path.split('/')
    if '/stage/' in path:
        f = parts[-1]
        if f.startswith('stf'):
            return '스태프롤'
        if f == 'msg_05.bin':
            return '지상전 잡담(R)'
        st = parts[2].replace('.zrc', '')
        if st.startswith('a7'):
            return '대사(H)'
        return '스토리 대사(%s)' % {'a': '공중전', 'g': '지상전', 'b': '지상전'}.get(st[0], st[0])
    if path.endswith('0.arc/resident/03.bin'):
        return '메뉴·시스템'
    if path.endswith('0.arc/resident/04.bin'):
        return '전투 UI·아이템'
    if path.endswith('00.arc/resident/00.bin'):
        return '시스템 메시지·팁'
    if '/menu/' in path:
        return '도감'
    return '기타'


def stage_of(path):
    p = path.split('/')
    return p[2].replace('.zrc', '') if len(p) > 2 and p[1] == 'stage' else ''


def load_us():
    """영어(북미판 us/ 트리) 라벨 → [(경로, 텍스트)]"""
    m = collections.defaultdict(list)
    for ps in list_msbt.groups(US):
        for p in ps:
            if not p.startswith('us/'):
                continue
            if '/stage/' in p and not p.endswith(('msg_00.bin', 'msg_05.bin', 'stf_00.bin')):
                continue      # msg_01/02 등은 스페인어·프랑스어
            mm = msbt.load(os.path.join(US, p))
            for i, t in enumerate(mm.texts):
                m[mm.label(i)].append((p, msgtext.decode(t)))
            break
    return m


def main():
    us = load_us()
    rows = []
    for ps in list_msbt.groups(JP):
        path = ps[0]
        m = msbt.load(os.path.join(JP, path))
        atr = m.section(b'ATR1')
        n, sz = struct.unpack_from('<II', atr, 0)
        cat = category(path, '')
        recs = []
        for i, t in enumerate(m.texts):
            lb = m.label(i)
            s = msgtext.decode(t)
            a = atr[8 + i * sz: 8 + (i + 1) * sz] if sz else b''
            code = a[0] - 1 if sz == 11 else None
            en_c = us.get(lb, [])
            en = ''
            if en_c:
                same = [x for x in en_c if x[0].split('/')[1:] == path.split('/')[1:]]
                en = (same or en_c)[0][1]
            r = dict(id='%s#%s' % (path.replace('jp/', '', 1), lb), file=path, copies=len(ps),
                     category=cat, stage=stage_of(path), index=i, label=lb,
                     speaker='', speaker_en='', speaker_source='', face_code=code, portrait='',
                     pit_side=(a[3] if sz == 11 else None),
                     jp=s, jp_plain=msgtext.plain(s), en=en, en_plain=msgtext.plain(en))
            if code is not None:
                if code >= 0:
                    sp = speaker_of(code)
                    if sp:
                        r['speaker'], r['speaker_en'] = sp[0], sp[1]
                        r['portrait'] = 'FB_%03d' % sp[2]
                        r['speaker_source'] = '얼굴코드'
                    else:
                        r['speaker_source'] = '미상(코드 %d)' % code
                elif a[3] == 1:
                    # 4번째 바이트 = 주인공 자리. 22장은 블랙피트가 주인공이다
                    if stage_of(path)[1:3] == '22':
                        r['speaker'], r['speaker_en'] = 'ブラックピット', 'Dark Pit'
                    else:
                        r['speaker'], r['speaker_en'] = PIT
                    r['speaker_source'] = '주인공 자리 표시(초상화 없음)'
            recs.append(r)
        rows += recs

    # 초상화 없는 대사: ① 같은 문장이 다른 장면에 얼굴코드로 있으면 그 화자 ② 수동 판정표
    known = collections.defaultdict(set)
    for r in rows:
        if r['speaker_source'] == '얼굴코드':
            known[r['jp_plain']].add((r['speaker'], r['speaker_en']))
    for r in rows:
        if r['face_code'] is None or r['speaker'] or not r['jp_plain'].strip():
            continue
        if r['label'].startswith('GRtxt'):       # 조작 설명 UI 글자, 대사 아님
            r['speaker_source'] = ''
            continue
        key = '%s#%s' % (r['stage'], r['label'])
        wild = MANUAL.get(r['stage'] + '#*', {})
        if key in MANUAL or r['label'].split('_')[0] in wild:
            sp = MANUAL[key] if key in MANUAL else wild[r['label'].split('_')[0]]
            if sp:
                r['speaker'], r['speaker_en'] = sp
                r['speaker_source'] = '문맥 판정(초상화 없음)'
            else:
                r['speaker_source'] = '미상(초상화 없음)'
            continue
        k = set()
        if r['stage'] == 'a2600' and r['label'].startswith('A500'):   # 최종장 회상: 앞 장 대사 인용
            k = set(known.get(r['jp_plain'], ()))
            if not k:
                for t, sp in known.items():
                    if len(r['jp_plain']) >= 6 and r['jp_plain'] in t:
                        k |= sp
        if len(k) == 1:
            r['speaker'], r['speaker_en'] = next(iter(k))
            r['speaker_source'] = '같은 문장(회상 인용)'
        else:
            r['speaker_source'] = '미상(초상화 없음)'

    for r in rows:
        k = '%s#%s' % (r['stage'], r['label'])
        if k in OVERRIDE:
            r['speaker'], r['speaker_en'] = OVERRIDE[k]
            r['speaker_source'] = '검수 판정(화면 밖 목소리)'

    # 공용 파일(03.bin)의 대사형 라벨: 같은 라벨이 스테이지에 있으면 화자 차용
    bylabel = {}
    for r in rows:
        if r['speaker'] and r['face_code'] is not None:
            bylabel.setdefault(r['label'], r)
    for r in rows:
        if r['face_code'] is None and re.match(r'^[AGHR]\d{3}_', r['label']) and r['label'] in bylabel:
            q = bylabel[r['label']]
            r['speaker'], r['speaker_en'], r['portrait'] = q['speaker'], q['speaker_en'], q['portrait']
            r['speaker_source'] = '같은 라벨(%s)' % q['stage']

    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(os.path.join(OUT, '신광신화_전체텍스트.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    cols = ['id', 'category', 'stage', 'label', 'speaker', 'speaker_en', 'speaker_source', 'portrait',
            'face_code', 'jp', 'jp_plain', 'en_plain', 'copies']
    with open(os.path.join(OUT, '신광신화_전체텍스트.tsv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(cols)
        for r in rows:
            w.writerow([str(r[c]).replace('\n', '\\n') if r[c] is not None else '' for c in cols])

    # 집계
    cnt = collections.Counter(); chars = collections.Counter()
    for r in rows:
        k = r['speaker'] or '(화자 없음)'
        cnt[k] += 1; chars[k] += len(r['jp_plain'].replace('\n', ''))
    with open(os.path.join(OUT, '화자별_집계.tsv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter='\t'); w.writerow(['화자', '메시지 수', '글자 수'])
        for k, v in cnt.most_common():
            w.writerow([k, v, chars[k]])
    src = collections.Counter(r['speaker_source'] or '-' for r in rows)
    cats = collections.Counter(r['category'] for r in rows)
    catc = collections.Counter()
    for r in rows:
        catc[r['category']] += len(r['jp_plain'].replace('\n', ''))
    print('메시지', len(rows), '글자', sum(chars.values()))
    for k, v in cats.most_common():
        print('  %-14s %5d개 %7d자' % (k, v, catc[k]))
    print('화자 근거', dict(src))
    print('영어 대조 없음', sum(1 for r in rows if not r['en'] and r['jp_plain']))


if __name__ == '__main__':
    main()
