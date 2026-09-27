# -*- coding: utf-8 -*-
"""MSBT 메시지 바이트 <-> 편집 문자열.
  0x0E 태그 → {g.t:paramhex}, 후리가나(0.0) → {ruby:본문|읽기}, 0x0F 닫는 태그 → {/g.t}
"""
import struct


def decode(b):
    out = []
    i = 0
    n = len(b)
    while i + 1 < n:
        c = struct.unpack_from('<H', b, i)[0]; i += 2
        if c == 0:
            break
        if c == 0x0E:
            g, t, sz = struct.unpack_from('<HHH', b, i); i += 6
            p = b[i:i + sz]; i += sz
            if g == 0 and t == 0 and sz >= 4:
                bl, rl = struct.unpack_from('<HH', p, 0)
                ruby = p[4:4 + rl].decode('utf-16le')
                base = b[i:i + bl].decode('utf-16le'); i += bl
                out.append('{ruby:%s|%s}' % (base, ruby))
            else:
                out.append('{%d.%d%s}' % (g, t, (':' + p.hex()) if p else ''))
        elif c == 0x0F:
            g, t = struct.unpack_from('<HH', b, i); i += 4
            out.append('{/%d.%d}' % (g, t))
        else:
            out.append(chr(c))
    return ''.join(out)


def plain(s):
    """태그 제거, 후리가나는 본문만."""
    import re
    s = re.sub(r'\{ruby:([^|]*)\|[^}]*\}', r'\1', s)
    return re.sub(r'\{[^}]*\}', '', s)


def encode(s):
    """편집 문자열 → MSBT 메시지 바이트(끝 NUL 포함). decode 의 역."""
    import re
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == '{':
            j = s.index('}', i)
            tag = s[i + 1:j]
            i = j + 1
            if tag.startswith('ruby:'):
                base, ruby = tag[5:].split('|', 1)
                rb, bb = ruby.encode('utf-16le'), base.encode('utf-16le')
                p = struct.pack('<HH', len(bb), len(rb)) + rb
                out += struct.pack('<HHHH', 0x0E, 0, 0, len(p)) + p + bb
            elif tag.startswith('/'):
                g, t = map(int, tag[1:].split('.'))
                out += struct.pack('<HHH', 0x0F, g, t)
            else:
                gt, _, ph = tag.partition(':')
                g, t = map(int, gt.split('.'))
                p = bytes.fromhex(ph)
                out += struct.pack('<HHHH', 0x0E, g, t, len(p)) + p
        else:
            out += s[i].encode('utf-16le')
            i += 1
    return bytes(out) + b'\0\0'
