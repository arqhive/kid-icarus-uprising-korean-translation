# -*- coding: utf-8 -*-
"""텍스트 + 그림 글씨 + 스태프롤 폰트를 한 번에 넣어 romfs 교체 파일을 만든다.

  python tools/build_all.py [--mod] [--only <경로 조각>]
    → work/build/romfs/jp/... 와 release/luma/titles/0004000000030000/romfs (LayeredFS 배포용)
    --mod: Azahar 모드 폴더에도 복사 / --only: 경로에 조각이 든 romfs 파일만 다시 만듦

- 텍스트: translation/ko.json (build_text.load_ko)
- 그림: images/GPT/게임내/<분류>/<파일>.png(로컬) → translation/graphics.csv 의 원본 경로 전부(같은 md5 인스턴스)
- 타이틀 로고: build_title_logo 채색판(ETC1A4) + 뒤 색판 메시 끄기(plan_title)
- 스태프롤 폰트: tools/build_stafffont.make()
romfs 파일마다 한 번만 풀고(LZ11·darc 여러 겹) 모든 교체를 한 뒤 다시 묶는다.
"""
import sys, os, csv, json, shutil, hashlib, collections, time
sys.path.insert(0, os.path.dirname(__file__))
import msbt, msgtext, darc, lz11, cgfx, tex_encode, build_text, build_stafffont, build_title_logo
from PIL import Image

ROOT = build_text.ROOT
OUT = build_text.OUT
SRC = build_text.SRC_ROMFS
GPT = os.path.join(ROOT, 'images', 'GPT', '게임내')
CSV = os.path.join(ROOT, 'translation', 'graphics.csv')
TID = '0004000000030000'
STAFF_FONT = 'jp/stage/a2600.zrc/stage/bin.arc/bin/fnt.bin'


def txob_all(d):
    """[(name, w, h, pica, mips, off, size)] 이미지 텍스처 전부(같은 이름 여러 개 포함)"""
    import struct
    out = []
    i = 0
    while True:
        i = d.find(b'TXOB', i)
        if i < 0:
            return out
        if struct.unpack_from('<I', d, i - 4)[0] == 0x20000011:
            W = struct.unpack_from('<20I', d, i)
            out.append((cgfx.cstr(d, i + 8 + W[2]), W[6], W[5], W[12], W[9], i + 4 * 17 + W[17], W[16]))
        i += 4


def plan_textures():
    """romfs 경로별 leaf 체인 → [(텍스처명, 원본 md5, 인코딩 바이트)]"""
    rows = list(csv.reader(open(CSV, encoding='utf-8-sig')))[1:]
    jobs = collections.defaultdict(list)
    cache = {}
    n_img = 0
    for r in rows:
        cat, fn, name, paths = r[0], r[1], r[2], r[7].split(' | ')
        png = os.path.join(GPT, cat, fn)
        if not os.path.exists(png):
            continue      # 모델 텍스처 등 이번에 제외한 그림
        if name == TITLE_TEX:
            continue      # 타이틀 로고는 plan_title() 이 컬러 형식으로 따로 넣는다
        n_img += 1
        # 기준 원본 md5: 첫 경로의 같은 이름 텍스처
        d0 = open(os.path.join(ROOT, 'unpack', 'jp', paths[0]), 'rb').read()
        t0 = [t for t in txob_all(d0) if t[0] == name][0]
        md5 = hashlib.md5(d0[t0[5]:t0[5] + t0[6]]).hexdigest()
        img = Image.open(png).convert('RGBA')
        assert img.size == (t0[1], t0[2]), (fn, img.size, t0[1:3])
        key = (png, t0[3], t0[4])
        if key not in cache:
            cache[key] = tex_encode.encode(img, t0[3], t0[4])
            assert len(cache[key]) == t0[6], (fn, len(cache[key]), t0[6])
        for p in paths:
            chain = build_text.split_path(p)
            jobs[chain[0]].append((tuple(chain[1:]), ('tex', name, md5, cache[key])))
    return jobs, n_img


TITLE_TEX = 'MenShowTop0000'
TITLE_BIND = 'jp/menu/000.zrc/menu/bind.arc/bind/00.bcres'
TITLE_MDL = 'jp/menu/000.zrc/menu/mdl.arc/mdl/03.bcres'
TITLE_MESH = 0x3f54


def plan_title():
    """타이틀 로고: 뒤 색판 메시(글자 몸통 모양, 일본어) 무력화 + 로고 텍스처를 LA4 → ETC1A4 컬러로(같은 8bpp·같은 크기).
    몸통을 원본 그라데이션으로 칠하고 불투명하게 막은 그림은 work/title_color/MenShowTop0000_color.png."""
    import struct
    jobs = collections.defaultdict(list)
    # 1) 텍스처
    d0 = open(os.path.join(ROOT, 'unpack', 'jp', TITLE_BIND), 'rb').read()
    t0 = [t for t in txob_all(d0) if t[0] == TITLE_TEX][0]
    md5 = hashlib.md5(d0[t0[5]:t0[5] + t0[6]]).hexdigest()
    data = tex_encode.encode(Image.open(build_title_logo.make()).convert('RGBA'), 13, 1)
    assert len(data) == t0[6]
    ch = build_text.split_path(TITLE_BIND)
    jobs[ch[0]].append((tuple(ch[1:]), ('tex_fmt', TITLE_TEX, md5, data, 13)))
    # 2) 메시: 인덱스를 모두 0 으로(삼각형이 전부 점이 되어 안 그려진다)
    m = bytearray(open(os.path.join(ROOT, 'unpack', 'jp', TITLE_MDL), 'rb').read())
    rel = lambda p: p + struct.unpack_from('<I', m, p)[0]
    b = TITLE_MESH - 4
    fg = rel(rel(b + 12 * 4))
    for q in range(fg, fg + 0x100, 4):
        if struct.unpack_from('<I', m, q)[0] == 0x1401:
            cnt = struct.unpack_from('<I', m, q + 8)[0]
            ip = rel(q + 12)
            m[ip:ip + cnt] = bytes(cnt)
            break
    else:
        raise SystemExit('타이틀 메시 인덱스를 못 찾음')
    ch = build_text.split_path(TITLE_MDL)
    jobs[ch[0]].append((tuple(ch[1:]), ('raw', bytes(m))))
    return jobs


def plan_text():
    per = build_text.load_ko()
    jobs = collections.defaultdict(list)
    grouped = collections.defaultdict(dict)
    for mid, text in per.items():
        path, label = mid.split('#', 1)
        chain = build_text.split_path('jp/' + path)
        grouped[(chain[0], tuple(chain[1:]))][label] = text
    for (rf, ch), labels in grouped.items():
        jobs[rf].append((ch, ('msg', labels)))
    return jobs


def apply_leaf(blob, ops, stats):
    for op in ops:
        if op[0] == 'msg':
            m = msbt.MSBT(blob)
            idx = {v: k for k, v in m.labels.items()}
            texts = list(m.texts)
            for lb, t in op[1].items():
                texts[idx[lb]] = msgtext.encode(t)
            blob = m.build(texts)
            stats['msg'] += len(op[1])
        elif op[0] == 'tex':
            _, name, md5, data = op
            b = bytearray(blob)
            hit = 0
            for t in txob_all(blob):
                if hashlib.md5(blob[t[5]:t[5] + t[6]]).hexdigest() == md5:   # 파일마다 이름이 다를 수 있어 그림 데이터로 찾는다
                    b[t[5]:t[5] + t[6]] = data
                    hit += 1
            if not hit:
                raise SystemExit('텍스처를 못 찾음: %s' % name)
            stats['tex'] += hit
            blob = bytes(b)
        elif op[0] == 'tex_fmt':          # 형식까지 바꾸기(ETC1A4 등, 크기 같을 때만)
            import struct
            _, name, md5, data, pica = op
            b = bytearray(blob)
            GL = {13: (0x675b, 0), 12: (0x675a, 0)}
            hit = 0
            i = 0
            while True:
                i = blob.find(b'TXOB', i)
                if i < 0:
                    break
                if struct.unpack_from('<I', blob, i - 4)[0] == 0x20000011:
                    W = struct.unpack_from('<20I', blob, i)
                    off = i + 4 * 17 + W[17]
                    if hashlib.md5(blob[off:off + W[16]]).hexdigest() == md5 and len(data) == W[16]:
                        b[off:off + W[16]] = data
                        struct.pack_into('<II', b, i + 7 * 4, *GL[pica])
                        struct.pack_into('<I', b, i + 12 * 4, pica)
                        hit += 1
                i += 4
            if not hit:
                raise SystemExit('텍스처를 못 찾음: %s' % name)
            stats['tex'] += hit
            blob = bytes(b)
        elif op[0] == 'raw':
            blob = op[1]
            stats['raw'] += 1
    return blob


def rebuild(blob, items, stats):
    """items: [(체인 튜플, op)] — blob(압축 풀린 darc) 안을 재귀로 고친다."""
    by_head = collections.defaultdict(list)
    for ch, op in items:
        by_head[ch[0]].append((ch[1:], op))
    ent = {p: (o, s) for p, o, s in darc.parse(blob)}
    repl = {}
    for head, sub in by_head.items():
        o, s = ent[head]
        inner = blob[o:o + s]
        leaf_ops = [op for ch, op in sub if not ch]
        deep = [(ch, op) for ch, op in sub if ch]
        if deep:
            comp = inner[:1] == b'\x11'
            d = lz11.decompress(inner) if comp else inner
            d = rebuild(d, deep, stats)
            inner = lz11.compress(d) if comp else d
        if leaf_ops:
            inner = apply_leaf(inner, leaf_ops, stats)
        repl[head] = inner
    return darc.rebuild(blob, repl)


def main():
    t0 = time.time()
    jobs = plan_text()
    tj, n_img = plan_textures()
    for k, v in tj.items():
        jobs[k] += v
    for k, v in plan_title().items():
        jobs[k] += v
    font, added = build_stafffont.make()
    ch = build_text.split_path(STAFF_FONT)
    jobs[ch[0]].append((tuple(ch[1:]), ('raw', font)))
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    if only:                          # 일부 romfs 파일만 다시 만든다(나머지 빌드 결과는 그대로)
        jobs = {k: v for k, v in jobs.items() if only in k}
    else:
        shutil.rmtree(OUT, ignore_errors=True)
    stats = collections.Counter()
    for rf, items in sorted(jobs.items()):
        raw = open(os.path.join(SRC, rf), 'rb').read()
        comp = raw[:1] == b'\x11'
        blob = lz11.decompress(raw) if comp else raw
        blob = rebuild(blob, items, stats)
        data = lz11.compress(blob) if comp else blob
        dst = os.path.join(OUT, rf)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(data)
    print('romfs 파일 %d개: 메시지 %d, 텍스처 %d곳(그림 %d장), 스태프롤 폰트 +%d자 (%.0f초)' % (
        len(jobs), stats['msg'], stats['tex'], n_img, len(added), time.time() - t0))
    luma = os.path.join(ROOT, 'release', 'luma', 'titles', TID, 'romfs')
    if not only:
        shutil.rmtree(os.path.join(ROOT, 'release', 'luma'), ignore_errors=True)
    for r_, _, fs in os.walk(OUT):
        for f in fs:
            p = os.path.join(r_, f)
            q = os.path.join(luma, os.path.relpath(p, OUT))
            os.makedirs(os.path.dirname(q), exist_ok=True)
            shutil.copyfile(p, q)
    print('LayeredFS:', luma)
    if '--mod' in sys.argv:
        dst = os.path.join(build_text.MOD, 'romfs')
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(OUT, dst)
        print('Azahar 모드:', dst)


if __name__ == '__main__':
    main()
