# -*- coding: utf-8 -*-
"""darc 아카이브 읽기/쓰기 (zrc = LZ11 압축 darc)."""
import struct, os
import lz11


def load(path):
    d = open(path, 'rb').read()
    if d[:1] == b'\x11':
        d = lz11.decompress(d)
    return d


def parse(d):
    """[(경로, 오프셋, 크기)] 반환. 경로는 '/' 구분."""
    assert d[:4] == b'darc'
    tbl_off, tbl_len, data_off = struct.unpack_from('<III', d, 0x10)
    cnt = struct.unpack_from('<III', d, tbl_off)[2]
    names_off = tbl_off + cnt * 12

    def name(o):
        p = names_off + o
        e = p
        while d[e:e + 2] != b'\0\0':
            e += 2
        return d[p:e].decode('utf-16le')
    out = []
    stack = []  # (끝 인덱스, 경로)
    for i in range(cnt):
        n, a, b = struct.unpack_from('<III', d, tbl_off + i * 12)
        while stack and i >= stack[-1][0]:
            stack.pop()
        nm = name(n & 0xFFFFFF)
        base = stack[-1][1] if stack else ''
        if n & 0x1000000:
            stack.append((b, (base + '/' + nm) if nm not in ('', '.') else base))
        else:
            out.append(((base + '/' + nm).lstrip('/'), a, b))
    return out


def extract(path, outdir):
    d = load(path)
    for p, o, s in parse(d):
        dst = os.path.join(outdir, p)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(d[o:o + s])


def rebuild(d, repl, align=0x80):
    """원본 darc 바이트 d 에서 repl{경로: 새 바이트} 만 바꿔 다시 묶는다(표·이름 그대로, 데이터 0x80 정렬)."""
    assert d[:4] == b'darc'
    tbl_off, tbl_len, data_off = struct.unpack_from('<III', d, 0x10)
    cnt = struct.unpack_from('<III', d, tbl_off)[2]
    paths = {}
    for p, o, s in parse(d):
        paths[(o, s)] = p
    files = []
    for i in range(cnt):
        n, a, b = struct.unpack_from('<III', d, tbl_off + i * 12)
        if not n & 0x1000000:
            files.append((a, i, paths[(a, b)], d[a:a + b]))
    files.sort()
    out = bytearray(d[:data_off])
    for k, (a, i, p, blob) in enumerate(files):
        blob = repl.get(p, blob)
        if k:
            out += b'\0' * ((-len(out)) % align)
        struct.pack_into('<II', out, tbl_off + i * 12 + 4, len(out), len(blob))
        out += blob
    struct.pack_into('<I', out, 0x0C, len(out))
    return bytes(out)
