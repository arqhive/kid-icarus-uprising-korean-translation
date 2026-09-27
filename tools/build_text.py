# -*- coding: utf-8 -*-
"""번역(translation/ko.json)을 게임 파일에 넣는다.

  python tools/build_text.py            → work/build/romfs/jp/... + Azahar 모드 폴더 복사
  python tools/build_text.py --no-mod   → 빌드만

메시지 id 는 'stage/a0100.zrc/stage/bin.arc/bin/msg_00.bin#A001_01' 형식(앞의 jp/ 생략).
경로에서 .arc/.zrc 로 끝나는 칸마다 darc 가 한 겹이다. romfs 파일(.zrc)은 LZ11 압축 darc.
번역이 없는 메시지는 원문을 둔다(후리가나 포함 그대로).
"""
import sys, os, json, re, shutil, collections, time
sys.path.insert(0, os.path.dirname(__file__))
import msbt, msgtext, darc, lz11

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROMFS = os.path.join(ROOT, 'extract', 'jp', 'romfs')
OUT = os.path.join(ROOT, 'work', 'build', 'romfs')
TID = '0004000000030000'
MOD = os.path.join(os.environ['APPDATA'], 'Azahar', 'load', 'mods', TID)


def split_path(p):
    """'jp/stage/a0100.zrc/stage/bin.arc/bin/msg_00.bin' → ['jp/stage/a0100.zrc', 'stage/bin.arc', 'bin/msg_00.bin']"""
    parts = p.split('/')
    out, cur = [], []
    for x in parts:
        cur.append(x)
        if x.endswith(('.arc', '.zrc')):
            out.append('/'.join(cur)); cur = []
    if cur:
        out.append('/'.join(cur))
    return out


def load_ko():
    units = json.load(open(os.path.join(ROOT, 'translation', 'units.json'), encoding='utf-8'))
    ko = json.load(open(os.path.join(ROOT, 'translation', 'ko.json'), encoding='utf-8'))
    per_msg = {}
    for u in units:
        if u['key'] in ko:
            for i in u['ids']:
                per_msg[i] = ko[u['key']]
    # 같은 내용의 파일이 여러 벌(a7000~a7028 15벌, msg_05 39벌, 도감 2벌) — 추출은 첫 벌만 했으므로 나머지 벌에도 넣는다
    import list_msbt
    for ps in list_msbt.groups(os.path.join(ROOT, 'unpack', 'jp')):
        first = ps[0][3:]
        for p in ps[1:]:
            for mid, t in list(per_msg.items()):
                if mid.startswith(first + '#'):
                    per_msg[p[3:] + mid[len(first):]] = t
    return per_msg


def rebuild_nested(blob, chain, repl_leaf):
    """blob(darc 바이트, 압축 해제됨) 안에서 chain 경로를 따라 들어가 leaf 를 바꾼 새 darc 바이트."""
    ent = {p: (o, s) for p, o, s in darc.parse(blob)}
    head = chain[0]
    o, s = ent[head]
    inner = blob[o:o + s]
    if len(chain) == 1:
        new_inner = repl_leaf(inner)
    else:
        comp = inner[:1] == b'\x11'
        d = lz11.decompress(inner) if comp else inner
        new_inner = rebuild_nested(d, chain[1:], repl_leaf)
        if comp:
            new_inner = lz11.compress(new_inner)
    return darc.rebuild(blob, {head: new_inner})


def main():
    per_msg = load_ko()
    # romfs 파일 → [(내부 경로 체인, 라벨→번역)]
    todo = collections.defaultdict(lambda: collections.defaultdict(dict))
    for mid, text in per_msg.items():
        path, label = mid.split('#', 1)
        chain = split_path('jp/' + path)
        todo[chain[0]][tuple(chain[1:])][label] = text
    shutil.rmtree(OUT, ignore_errors=True)
    t0 = time.time()
    n = 0
    for rf, msgs in sorted(todo.items()):
        raw = open(os.path.join(SRC_ROMFS, rf), 'rb').read()
        comp = raw[:1] == b'\x11'
        blob = lz11.decompress(raw) if comp else raw
        for chain, labels in msgs.items():
            def repl(b, labels=labels):
                m = msbt.MSBT(b)
                idx = {v: k for k, v in m.labels.items()}
                texts = list(m.texts)
                for lb, t in labels.items():
                    texts[idx[lb]] = msgtext.encode(t)
                return m.build(texts)
            blob = rebuild_nested(blob, list(chain), repl)
            n += len(labels)
        data = lz11.compress(blob) if comp else blob
        dst = os.path.join(OUT, rf)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(data)
    print('메시지 %d개, romfs 파일 %d개 (%.0f초) → %s' % (n, len(todo), time.time() - t0, OUT))
    if '--no-mod' not in sys.argv:
        dst = os.path.join(MOD, 'romfs')
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(OUT, dst)
        print('Azahar 모드:', dst)


if __name__ == '__main__':
    main()
