# -*- coding: utf-8 -*-
"""CGFX(bcres) 안 TXOB 이미지 텍스처 목록·디코드."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ctxb

# PICA 포맷 번호 -> (glFormat, glType) : ctxb.decode 인자
PICA = {0: (0x6752, 0x1401), 1: (0x6754, 0x1401), 2: (0x6752, 0x8034), 3: (0x6754, 0x8363),
        4: (0x6752, 0x8033), 5: (0x6758, 0x1401), 7: (0x6757, 0x1401), 8: (0x6756, 0x1401),
        9: (0x6758, 0x6760), 10: (0x6757, 0x6760), 11: (0x6756, 0x6760), 12: (0x675a, 0), 13: (0x675b, 0)}
BPP = {0: 32, 1: 24, 2: 16, 3: 16, 4: 16, 5: 16, 6: 16, 7: 8, 8: 8, 9: 8, 10: 4, 11: 4, 12: 4, 13: 8}
NAMES = {0: 'RGBA8', 1: 'RGB8', 2: 'RGBA5551', 3: 'RGB565', 4: 'RGBA4', 5: 'LA8', 6: 'HILO8', 7: 'L8',
         8: 'A8', 9: 'LA4', 10: 'L4', 11: 'A4', 12: 'ETC1', 13: 'ETC1A4'}


def cstr(d, o):
    e = d.index(b'\0', o)
    return d[o:e].decode('ascii', 'replace')


def textures(d):
    """[(name, w, h, pica, data_off, data_size)]"""
    out = []
    i = 0
    while True:
        i = d.find(b'TXOB', i)
        if i < 0:
            return out
        try:
            flag = struct.unpack_from('<I', d, i - 4)[0]
            W = struct.unpack_from('<20I', d, i)
            if flag == 0x20000011:
                name = cstr(d, i + 8 + W[2])
                h, w, mips, pica = W[5], W[6], W[9], W[12]
                size = W[16]; off = i + 4 * 17 + W[17]
                out.append((name, w, h, pica, off, size))
        except Exception:
            pass
        i += 4


def decode(d, t):
    name, w, h, pica, off, size = t
    pf, dt = PICA[pica]
    return ctxb.decode(d[off:off + w * h * BPP[pica] // 8], w, h, pf, dt)


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    for t in textures(d):
        print(t[0], t[1], t[2], NAMES.get(t[3], t[3]), hex(t[4]), t[5])
