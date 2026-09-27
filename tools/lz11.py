"""3DS LZ11 압축/해제.

배너(banner.bin) 안의 CGFX 가 LZ11 로 압축돼 있어서 필요하다.
압축은 해시 체인 기반 탐욕 매칭이라 닌텐도 원본보다 조금 커지지만,
게임이 읽는 데는 문제가 없다(형식이 같다).
"""
import struct

WINDOW = 0x1000          # 거리 최대 4096
MIN_MATCH = 3
MAX_MATCH = 0x10110      # 3바이트 인코딩의 상한
MAX_CHAIN = 64           # 후보 탐색 깊이 (속도/크기 절충)


def decompress(d):
    assert d[0] == 0x11, "LZ11 이 아니다"
    size = d[1] | d[2] << 8 | d[3] << 16
    p = 4
    if size == 0:
        size = struct.unpack_from("<I", d, 4)[0]
        p = 8
    out = bytearray()
    while len(out) < size:
        flags = d[p]
        p += 1
        for i in range(8):
            if len(out) >= size:
                break
            if not (flags & (0x80 >> i)):
                out.append(d[p])
                p += 1
                continue
            a = d[p]
            p += 1
            ind = a >> 4
            if ind == 0:
                b, c = d[p], d[p + 1]
                p += 2
                cnt = (((a & 0xF) << 4) | (b >> 4)) + 0x11
                disp = (((b & 0xF) << 8) | c) + 1
            elif ind == 1:
                b, c, e = d[p], d[p + 1], d[p + 2]
                p += 3
                cnt = (((a & 0xF) << 12) | (b << 4) | (c >> 4)) + 0x111
                disp = (((c & 0xF) << 8) | e) + 1
            else:
                b = d[p]
                p += 1
                cnt = ind + 1
                disp = (((a & 0xF) << 8) | b) + 1
            for _ in range(cnt):
                out.append(out[-disp])
    return bytes(out[:size])


def _encode_token(cnt, disp):
    d = disp - 1
    if cnt <= 0x10:                       # 3..16
        return bytes([((cnt - 1) << 4) | (d >> 8), d & 0xFF])
    if cnt <= 0x110:                      # 17..272
        c = cnt - 0x11
        return bytes([c >> 4, ((c & 0xF) << 4) | (d >> 8), d & 0xFF])
    c = cnt - 0x111                       # 273..65808
    return bytes([0x10 | (c >> 12), (c >> 4) & 0xFF,
                  ((c & 0xF) << 4) | (d >> 8), d & 0xFF])


def compress(src):
    n = len(src)
    heads = {}                            # 3바이트 키 -> 최근 위치 목록
    out = bytearray(b"\x11" + bytes([n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF]))
    if n > 0xFFFFFF:
        out = bytearray(b"\x11\x00\x00\x00" + struct.pack("<I", n))

    chunk = bytearray()
    flags = 0
    nflag = 0
    pos = 0
    while pos < n:
        best_len, best_disp = 0, 0
        if pos + MIN_MATCH <= n:
            key = src[pos:pos + MIN_MATCH]
            for cand in reversed(heads.get(key, ())[-MAX_CHAIN:]):
                disp = pos - cand
                if disp > WINDOW:
                    break
                limit = min(MAX_MATCH, n - pos)
                if limit <= best_len:
                    break
                ln = 0
                while ln < limit and src[cand + ln] == src[pos + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_disp = ln, disp
                    if ln == limit:
                        break

        if best_len >= MIN_MATCH:
            flags |= 0x80 >> nflag
            chunk += _encode_token(best_len, best_disp)
            step = best_len
        else:
            chunk.append(src[pos])
            step = 1
        nflag += 1
        if nflag == 8:
            out.append(flags)
            out += chunk
            flags, nflag, chunk = 0, 0, bytearray()

        # 지나간 위치를 해시에 등록
        for k in range(pos, min(pos + step, n - MIN_MATCH + 1)):
            heads.setdefault(src[k:k + MIN_MATCH], []).append(k)
        pos += step

    if nflag:
        out.append(flags)
        out += chunk
    while len(out) % 4:
        out.append(0)
    return bytes(out)
