# -*- coding: utf-8 -*-
"""3DS BCFNT(CFNT) 읽기·쓰기.

구조: 헤더(0x14) → FINF → TGLP(글리프 시트) → CWDH(글자 폭, 여러 개) → CMAP(문자→인덱스, 여러 개).
섹션 사이 참조는 '섹션 데이터 시작'(매직+8) 기준 절대 오프셋이다.
Azahar 는 공유 폰트를 옮길 때 섹션 크기를 더해 가며 다음 섹션을 찾으므로,
TGLP 섹션 크기는 시트 데이터까지 포함해야 한다(check_walk 로 검사).
"""
import struct


class Font:
    pass


def parse(d):
    assert d[:4] == b'CFNT', d[:4]
    f = Font()
    f.version = struct.unpack_from('<I', d, 8)[0]
    p = 0x14
    assert d[p:p + 4] == b'FINF'
    (f.font_type, f.line_feed, f.alter_idx, f.def_left, f.def_glyph_w, f.def_char_w,
     f.encoding, tglp, cwdh, cmap, f.height, f.width, f.ascent, f.reserved) = struct.unpack_from(
        '<BBHbBBBIIIBBBB', d, p + 8)
    # TGLP
    q = tglp - 8
    assert d[q:q + 4] == b'TGLP'
    (f.cell_w, f.cell_h, f.baseline, f.max_w, sheet_size, nsheets, f.sheet_fmt,
     f.cols, f.rows, f.sheet_w, f.sheet_h, sdata) = struct.unpack_from('<BBbBIHHHHHHI', d, q + 8)
    f.sheets = [d[sdata + i * sheet_size: sdata + (i + 1) * sheet_size] for i in range(nsheets)]
    f.sheet_size = sheet_size
    # CWDH: 인덱스 → (left, glyph_w, char_w)
    f.widths = {}
    o = cwdh
    while o:
        q = o - 8
        start, end, nxt = struct.unpack_from('<HHI', d, q + 8)
        for i in range(start, end + 1):
            f.widths[i] = struct.unpack_from('<bBB', d, q + 16 + (i - start) * 3)
        o = nxt
    # CMAP: 코드 → 인덱스
    f.cmap = {}
    o = cmap
    while o:
        q = o - 8
        cs, ce, method, _, nxt = struct.unpack_from('<HHHHI', d, q + 8)
        b = q + 20
        if method == 0:       # direct
            base = struct.unpack_from('<H', d, b)[0]
            for c in range(cs, ce + 1):
                f.cmap[c] = base + (c - cs)
        elif method == 1:     # table
            for c in range(cs, ce + 1):
                i = struct.unpack_from('<H', d, b + (c - cs) * 2)[0]
                if i != 0xFFFF:
                    f.cmap[c] = i
        else:                 # scan
            n = struct.unpack_from('<H', d, b)[0]
            for k in range(n):
                c, i = struct.unpack_from('<HH', d, b + 2 + k * 4)
                f.cmap[c] = i
        o = nxt
    return f


def _pad(out, a):
    while len(out) % a:
        out.append(0)


def build(f):
    """Font → CFNT 바이트. 시트는 0x80 정렬, CWDH·CMAP 은 각각 하나로 합쳐 쓴다(CMAP 은 scan 방식)."""
    out = bytearray(0x14)
    finf_p = len(out)
    out += bytes(0x20)
    # TGLP (섹션 크기에 시트 데이터 포함)
    tglp_p = len(out)
    out += bytes(0x20)
    _pad(out, 0x80)
    sdata = len(out)
    for s in f.sheets:
        assert len(s) == f.sheet_size
        out += s
    _pad(out, 4)
    struct.pack_into('<4sIBBbBIHHHHHHI', out, tglp_p, b'TGLP', len(out) - tglp_p, f.cell_w, f.cell_h,
                     f.baseline, f.max_w, f.sheet_size, len(f.sheets), f.sheet_fmt, f.cols, f.rows,
                     f.sheet_w, f.sheet_h, sdata)
    # CWDH
    cwdh_p = len(out)
    n = max(f.widths) + 1
    body = bytearray()
    for i in range(n):
        body += struct.pack('<bBB', *f.widths.get(i, (0, 0, 0)))
    _pad(body, 4)
    out += struct.pack('<4sIHHI', b'CWDH', 16 + len(body), 0, n - 1, 0) + body
    # CMAP (scan 하나)
    cmap_p = len(out)
    items = sorted(f.cmap.items())
    body = bytearray(struct.pack('<H', len(items)) + b''.join(struct.pack('<HH', c, i) for c, i in items))
    while (len(body) + 20) % 4:
        body.append(0)
    out += struct.pack('<4sIHHHHI', b'CMAP', 20 + len(body), 0, 0xFFFF, 2, 0, 0) + body
    struct.pack_into('<4sIBBHbBBBIIIBBBB', out, finf_p, b'FINF', 0x20, f.font_type, f.line_feed,
                     f.alter_idx, f.def_left, f.def_glyph_w, f.def_char_w, f.encoding,
                     tglp_p + 8, cwdh_p + 8, cmap_p + 8, f.height, f.width, f.ascent, f.reserved)
    struct.pack_into('<4sHHIII', out, 0, b'CFNT', 0xFEFF, 0x14, f.version, len(out), 4)
    return bytes(out)


def check_walk(d):
    """Azahar RelocateSharedFont 와 같은 방식으로 섹션을 따라가며 FINF 오프셋과 맞는지 본다."""
    n = struct.unpack_from('<I', d, 0x10)[0]
    p = struct.unpack_from('<H', d, 6)[0]
    first = {}
    assumed = {}
    for _ in range(n):
        magic = d[p:p + 4]
        size = struct.unpack_from('<I', d, p + 4)[0]
        first.setdefault(magic, p)
        if magic == b'FINF':
            t, w, c = struct.unpack_from('<III', d, p + 0x10)
            assumed = {b'TGLP': t - 8, b'CWDH': w - 8, b'CMAP': c - 8}
        p += size
    ok = bool(assumed) and all(first.get(k) == v for k, v in assumed.items())
    return ok, first, assumed
