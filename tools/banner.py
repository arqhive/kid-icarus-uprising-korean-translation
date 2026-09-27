# -*- coding: utf-8 -*-
"""HOME 메뉴 배너(banner.bin = CBMD) 읽기·쓰기.

CBMD 헤더: 0x08 공통 CGFX 오프셋, 0x0C부터 지역별 CGFX 오프셋 16개(유럽 8·일본·미국 4·중국·한국·대만)(0이면 공통 사용), 0x84 CWAV 오프셋.
CGFX 는 각각 LZ11 로 압축돼 있다. 텍스처(TXOB)는 이름·크기·PICA 형식을 가진다.

  python tools/banner.py dump work/banner/banner.bin work/banner/dump   # 텍스처를 PNG 로
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import lz11, ctxb

REGIONS = ['COMMON', 'EUR_EN', 'EUR_FR', 'EUR_DE', 'EUR_IT', 'EUR_ES', 'EUR_NL', 'EUR_PT', 'EUR_RU',
           'JPN_JP', 'USA_EN', 'USA_FR', 'USA_ES', 'USA_PT', 'CHN_CN', 'KOR_KO', 'TWN_TW']
# CGFX PICA 형식 번호 → ctxb.decode 의 (GL format, GL type)
PICA = {0: (0x6752, 0x1401), 1: (0x6754, 0x1401), 2: (0x6752, 0x8034), 3: (0x6754, 0x8363),
        4: (0x6752, 0x8033), 5: (0x6758, 0x1401), 7: (0x6757, 0x1401), 8: (0x6756, 0x1401),
        9: (0x6758, 0x6760), 10: (0x6757, 0x6760), 11: (0x6756, 0x6760), 12: (0x675a, 0), 13: (0x675b, 0)}


def sections(b):
    """[(지역 이름, 압축 시작, 압축 끝)] — 오프셋 순으로 정렬해 끝을 정한다."""
    offs = struct.unpack_from('<17I', b, 0x08); cwav = struct.unpack_from('<I', b, 0x84)[0]
    ends = sorted(set(o for o in offs if o) | {cwav or len(b)})
    return [(REGIONS[i], o, ends[ends.index(o) + 1]) for i, o in enumerate(offs) if o]


def textures(cgfx):
    """CGFX 안의 TXOB: (이름, 너비, 높이, PICA 형식, 데이터 오프셋, 크기)"""
    out = []; i = 0
    while True:
        i = cgfx.find(b'TXOB', i)
        if i < 0: return out
        base = i - 4
        W = struct.unpack_from('<20I', cgfx, base)
        no = base + 0x0C + W[3]
        name = cgfx[no:cgfx.index(b'\0', no)].decode('ascii', 'replace') if 0 < W[3] < len(cgfx) else '?'
        h, w, fmt, size = W[6], W[7], W[13], W[17]
        data = base + 18 * 4 + W[18]
        if w and h and fmt in PICA and 0 < size <= len(cgfx): out.append((name, w, h, fmt, data, size))
        i += 4


def decode(cgfx, t):
    name, w, h, fmt, data, size = t
    return ctxb.decode(cgfx[data:data + size], w, h, *PICA[fmt])


def dump(src, dst):
    b = open(src, 'rb').read(); os.makedirs(dst, exist_ok=True)
    for reg, a, e in sections(b):
        cgfx = lz11.decompress(b[a:e])
        for t in textures(cgfx):
            decode(cgfx, t).save(os.path.join(dst, '%s_%s.png' % (reg, t[0])))
            print('%-7s %-24s %4dx%-4d fmt%-2d @%#x %d' % (reg, t[0], t[1], t[2], t[3], t[4], t[5]))


if __name__ == '__main__':
    if sys.argv[1] == 'dump': dump(sys.argv[2], sys.argv[3])
