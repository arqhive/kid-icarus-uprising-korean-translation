# -*- coding: utf-8 -*-
"""PSLB(이진 JSON) 읽기. 타입: 01 문자열, 02 정수, 03 실수, 04 불, 05 객체, 06 배열."""
import struct, json, sys


def parse(d):
    assert d[:4] == b'PSLB'
    p = [0x10]

    def u32():
        v = struct.unpack_from('<I', d, p[0])[0]; p[0] += 4; return v

    def s():
        n = u32(); v = d[p[0]:p[0] + n]; p[0] += n
        try: return v.decode('utf-8')
        except UnicodeDecodeError: return v.decode('cp932', 'replace')

    def val():
        t = d[p[0]]; p[0] += 1
        if t == 1: return s()
        if t == 2:
            v = struct.unpack_from('<i', d, p[0])[0]; p[0] += 4; return v
        if t == 3:
            v = struct.unpack_from('<f', d, p[0])[0]; p[0] += 4; return round(v, 4)
        if t == 4:
            v = d[p[0]]; p[0] += 1; return bool(v)
        if t == 5:
            n = u32(); o = {}
            for _ in range(n):
                k = s(); o[k] = val()
            return o
        if t == 6:
            n = u32(); return [val() for _ in range(n)]
        if t == 0: return None
        raise ValueError('type %d at %x' % (t, p[0] - 1))
    return val()


if __name__ == '__main__':
    print(json.dumps(parse(open(sys.argv[1], 'rb').read()), ensure_ascii=False, indent=1))
