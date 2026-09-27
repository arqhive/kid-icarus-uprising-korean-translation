# -*- coding: utf-8 -*-
"""PICA 텍스처 인코더 (CGFX TXOB 용). 8x8 타일(행 우선) 안 모턴 순서.

  encode(img, pica, mips=1) -> bytes
지원: 0 RGBA8, 1 RGB8, 2 RGBA5551, 3 RGB565, 4 RGBA4, 5 LA8, 7 L8, 8 A8, 9 LA4, 10 L4, 11 A4, 12 ETC1, 13 ETC1A4
ETC1 계열은 에버 오아시스 tools/etc1.py(etcpak) 방식.
"""
import numpy as np
import etcpak
from PIL import Image
import ctxb

MT = ctxb.MT


def _tiles(a):
    """(h,w,...) 배열 → 모턴 순서 픽셀 배열 (N, ...)"""
    h, w = a.shape[:2]
    idx_y = np.array([y for _, y in MT]); idx_x = np.array([x for x, _ in MT])
    out = []
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            out.append(a[ty + idx_y, tx + idx_x])
    return np.concatenate(out)


def _q(v, bits):
    return (v.astype(np.int32) * ((1 << bits) - 1) + 127) // 255


def _lum(rgba):
    # L 포맷: 원본 디코드가 (v,v,v) 이므로 RGB 평균이면 충분(회색 그림)
    return (rgba[..., 0].astype(np.int32) + rgba[..., 1] + rgba[..., 2] + 1) // 3


def _etc(img, alpha):
    a = np.array(img.convert('RGBA'))
    h, w = a.shape[:2]
    raw = etcpak.compress_etc1_rgb(np.ascontiguousarray(a).tobytes(), w, h)
    blocks = np.frombuffer(raw, dtype=np.uint8).reshape(h // 4, w // 4, 8)
    out = bytearray()
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for sb in range(4):
                sx = tx + (sb & 1) * 4; sy = ty + (sb >> 1) * 4
                if alpha:
                    v = 0
                    for x in range(4):
                        for y in range(4):
                            q = (int(a[sy + y, sx + x, 3]) * 15 + 127) // 255
                            v |= q << ((x * 4 + y) * 4)
                    out += v.to_bytes(8, 'little')
                out += bytes(blocks[sy // 4, sx // 4][::-1])
    return bytes(out)


def encode_level(img, pica):
    if pica in (12, 13):
        return _etc(img, pica == 13)
    a = np.array(img.convert('RGBA'))
    t = _tiles(a)
    r, g, b, al = t[:, 0], t[:, 1], t[:, 2], t[:, 3]
    if pica == 0:
        return np.stack([al, b, g, r], 1).astype(np.uint8).tobytes()
    if pica == 1:
        return np.stack([b, g, r], 1).astype(np.uint8).tobytes()
    if pica == 2:
        v = _q(r, 5) << 11 | _q(g, 5) << 6 | _q(b, 5) << 1 | (al >= 128)
        return v.astype('<u2').tobytes()
    if pica == 3:
        v = _q(r, 5) << 11 | _q(g, 6) << 5 | _q(b, 5)
        return v.astype('<u2').tobytes()
    if pica == 4:
        v = _q(r, 4) << 12 | _q(g, 4) << 8 | _q(b, 4) << 4 | _q(al, 4)
        return v.astype('<u2').tobytes()
    L = _lum(t)
    if pica == 5:
        return np.stack([al, L], 1).astype(np.uint8).tobytes()
    if pica == 7:
        return L.astype(np.uint8).tobytes()
    if pica == 8:
        return al.astype(np.uint8).tobytes()
    if pica == 9:
        return (_q(L, 4) << 4 | _q(al, 4)).astype(np.uint8).tobytes()
    if pica in (10, 11):
        v = _q(L if pica == 10 else al, 4).astype(np.uint8)
        return (v[0::2] | (v[1::2] << 4)).astype(np.uint8).tobytes()
    raise ValueError('지원하지 않는 형식 %d' % pica)


def encode(img, pica, mips=1):
    img = img.convert('RGBA')
    out = bytearray()
    w, h = img.size
    for m in range(mips):
        lv = img if m == 0 else img.resize((max(8, w >> m), max(8, h >> m)), Image.LANCZOS)
        out += encode_level(lv, pica)
    return bytes(out)
