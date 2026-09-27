# -*- coding: utf-8 -*-
"""빌드 결과 검사: 빌드된 romfs 를 다시 풀어 모든 메시지가 (번역 있으면 번역, 없으면 원문) 인지 확인."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import msbt, msgtext, darc, lz11, list_msbt, build_text

ROOT = build_text.ROOT


def open_chain(path):
    chain = build_text.split_path(path)
    p = os.path.join(build_text.OUT, chain[0])
    if not os.path.exists(p):
        p = os.path.join(build_text.SRC_ROMFS, chain[0])
    b = open(p, 'rb').read()
    for c in chain[1:]:
        if b[:1] == b'\x11':
            b = lz11.decompress(b)
        ent = {q: (o, s) for q, o, s in darc.parse(b)}
        o, s = ent[c]
        b = b[o:o + s]
    return b


def main():
    per = build_text.load_ko()
    rows = json.load(open(os.path.join(ROOT, 'text', '신광신화_전체텍스트.json'), encoding='utf-8'))
    byfile = {}
    for r in rows:
        byfile.setdefault(r['id'].split('#')[0], []).append(r)
    bad = ok = 0
    for ps in list_msbt.groups(os.path.join(ROOT, 'unpack', 'jp')):
        for p in ps:
            m = msbt.MSBT(open_chain(p))
            key = p[3:]
            for i in range(len(m.texts)):
                mid = key + '#' + m.label(i)
                want = per.get(mid)
                got = msgtext.decode(m.texts[i])
                if want is None:
                    orig = msbt.load(os.path.join(ROOT, 'unpack', 'jp', p)).texts[i]
                    good = m.texts[i] == orig
                else:
                    good = got == want
                if good:
                    ok += 1
                else:
                    bad += 1
                    if bad < 10:
                        print('불일치', mid, repr(got[:30]), repr((want or '')[:30]))
    print('메시지 %d개 확인, 불일치 %d' % (ok + bad, bad))
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
