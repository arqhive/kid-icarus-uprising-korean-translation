# -*- coding: utf-8 -*-
"""Azahar 용 한글 시스템 폰트(공유 폰트) 만들기.

Azahar 는 본체 공유 폰트 덤프가 없으면 내장 대체 폰트(한글 없음)를 쓴다.
이 스크립트는 그 대체 폰트를 바탕으로
  - 가나·기호·라틴 등 한자 아닌 글리프는 전부 유지
  - 한자는 게임 원문에 나오는 것 + JIS 1수준만 유지 (공유 폰트 메모리 0x332000 한도 때문)
  - KS X 1001 한글 2,350자 추가 (Noto Sans KR)
해서 cbf_std.bcfnt.lz 를 만들고, 시스템 아카이브 0004009B00014002 (CFA)로 Azahar NAND 에 넣는다.

  python tools/build_sysfont.py            # 빌드 + 설치
  python tools/build_sysfont.py --preview  # 미리보기 PNG 만 (work/font/preview.png)
  python tools/build_sysfont.py --remove   # Azahar 에서 제거(내장 대체 폰트로 복귀)
  python tools/build_sysfont.py --cfa-only # 배포용 work/font/cfa/font.cfa 만 만들기(설치 안 함)
"""
import sys, os, json, struct, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import bcfnt, ctxb, lz11

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, 'work', 'font')
AZ_EXE = os.environ.get('AZAHAR_EXE', os.path.join(os.path.expanduser('~'), 'az', 'azahar.exe'))   # 내장 대체 공유 폰트를 꺼낼 azahar.exe
BIN = os.path.join(ROOT, 'tools', 'bin')
NAND_TITLE = os.path.join(os.environ['APPDATA'], 'Azahar', 'nand', '00000000000000000000000000000000',
                          'title', '0004009b', '00014002')
KR_FONT = os.path.join(ROOT, 'tools', 'fonts', 'NotoSansKR-VF.ttf')
WGHT = 500           # 한자(얇은 고딕)와 비슷한 두께
LIMIT = 0x332000 - 0x80
STRIDE = 25          # 시트 안 칸 간격 (cell_w 24 + 1)


def load_base():
    """azahar.exe 안의 대체 폰트 romfs 에서 cbf_std.bcfnt.lz 를 꺼내 푼다."""
    p = os.path.join(W, 'azahar_cbf_std.bcfnt')
    if os.path.exists(p):
        return open(p, 'rb').read()
    d = open(AZ_EXE, 'rb').read()
    name = 'cbf_std.bcfnt.lz'.encode('utf-16le')
    k = d.find(name)
    # romfs 파일 메타 이름 앞 0x20 바이트가 메타, 그 앞 0x58 이 헤더 시작
    r = k - 0x20 - 0x58
    hl, dho, dhl, dmo, dml, fho, fhl, fmo, fml, dat = struct.unpack_from('<10I', d, r)
    off, size = struct.unpack_from('<QQ', d, r + fmo + 8)
    f = lz11.decompress(d[r + dat + off: r + dat + off + size])
    os.makedirs(W, exist_ok=True)
    open(p, 'wb').write(f)
    return f


def is_kanji(c):
    return 0x4E00 <= c <= 0x9FFF or 0x3400 <= c <= 0x4DBF or 0xF900 <= c <= 0xFAFF


def keep_kanji():
    s = set()
    rows = json.load(open(os.path.join(ROOT, 'text', '신광신화_전체텍스트.json'), encoding='utf-8'))
    for r in rows:
        s |= {ord(ch) for ch in r['jp'] if is_kanji(ord(ch))}
    game = len(s)
    for hi in range(0x88, 0x99):          # JIS 1수준 = SJIS 889F..9872
        for lo in range(0x40, 0xFD):
            try:
                ch = bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError:
                continue
            if (hi, lo) >= (0x88, 0x9F) and (hi, lo) <= (0x98, 0x72) and is_kanji(ord(ch)):
                s.add(ord(ch))
    return s, game


def hangul_2350():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            ch = bytes([hi, lo]).decode('euc-kr')
            out.append(ord(ch))
    return out


_SHEET = {}


def glyph_alpha(f, i):
    """시트에서 글리프 i 의 24x30 알파(0~15) 배열."""
    si = i // (f.cols * f.rows)
    k = i % (f.cols * f.rows)
    if si not in _SHEET:
        _SHEET.clear()
        _SHEET[si] = np.asarray(ctxb.decode(f.sheets[si], f.sheet_w, f.sheet_h, 0x6756, 0x6760).split()[3]) // 17
    a = _SHEET[si]
    x, y = (k % f.cols) * STRIDE, (k // f.cols) * (f.cell_h + 2)
    return a[y:y + f.cell_h, x:x + f.cell_w].copy()


def render_hangul(codes, cell_w=24, cell_h=30):
    SS = 4
    font = ImageFont.truetype(KR_FONT, 22 * SS)
    try:
        font.set_variation_by_axes([WGHT])
    except Exception:
        pass
    # 기준 글자 '한'의 잉크가 y 2..22 에 오도록 기준선 잡기
    probe = Image.new('L', (cell_w * SS, cell_h * SS), 0)
    ImageDraw.Draw(probe).text((0, 0), '한', font=font, fill=255)
    bb = probe.getbbox()
    dy = 2 * SS - bb[1]
    out = {}
    for c in codes:
        im = Image.new('L', (cell_w * SS, cell_h * SS), 0)
        dr = ImageDraw.Draw(im)
        bx = font.getbbox(chr(c))
        w = bx[2] - bx[0]
        dr.text(((cell_w * SS - w) // 2 - bx[0], dy), chr(c), font=font, fill=255)
        a = np.asarray(im.resize((cell_w, cell_h), Image.BOX), dtype=np.float32)
        out[c] = np.clip(np.round(a / 17), 0, 15).astype(np.uint8)
    return out


def encode_a4(a):
    """알파(0~15) HxW → PICA A4 타일 바이트."""
    h, w = a.shape
    out = bytearray(w * h // 2)
    p = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for i in range(64):
                x, y = ctxb.MT[i]
                v = int(a[ty + y, tx + x])
                if p & 1:
                    out[p >> 1] |= v << 4
                else:
                    out[p >> 1] = v
                p += 1
    return bytes(out)


def build():
    base = bcfnt.parse(load_base())
    kan, game_k = keep_kanji()
    inv = {}
    for c, i in base.cmap.items():
        inv.setdefault(i, []).append(c)
    keep = []          # (코드들, 원본 인덱스)
    for i in sorted(inv):
        cs = inv[i]
        if all(is_kanji(c) for c in cs) and not any(c in kan for c in cs):
            continue
        keep.append((cs, i))
    hg = [c for c in hangul_2350() if c not in base.cmap]
    per = base.cols * base.rows
    total = len(keep) + len(hg)
    nsheets = (total + per - 1) // per
    est = nsheets * base.sheet_size + total * 3 + total * 4 + 0x200
    print('유지 %d (게임 한자 %d, 유지 한자 %d) + 한글 %d = %d자, 시트 %d장, 예상 %d 바이트 / 한도 %d' % (
        len(keep), game_k, sum(1 for cs, _ in keep if all(is_kanji(c) for c in cs)), len(hg), total,
        nsheets, est, LIMIT))
    kr = render_hangul(hg)
    glyphs = []        # (alpha, widths, codes)
    for cs, i in keep:
        glyphs.append((glyph_alpha(base, i), base.widths.get(i, (base.def_left, base.def_glyph_w, base.def_char_w)), cs))
    for c in hg:
        glyphs.append((kr[c], (1, 22, 24), [c]))
    f = base
    sheets = []
    for s in range(nsheets):
        a = np.zeros((f.sheet_h, f.sheet_w), np.uint8)
        for k, g in enumerate(glyphs[s * per:(s + 1) * per]):
            x, y = (k % f.cols) * STRIDE, (k // f.cols) * (f.cell_h + 2)
            a[y:y + f.cell_h, x:x + f.cell_w] = g[0]
        sheets.append(encode_a4(a))
    old_alt = inv.get(base.alter_idx, [ord('?')])[0]
    f.sheets = sheets
    f.widths = {k: g[1] for k, g in enumerate(glyphs)}
    f.cmap = {}
    for k, g in enumerate(glyphs):
        for c in g[2]:
            f.cmap[c] = k
    f.alter_idx = f.cmap.get(old_alt, f.cmap[ord('?')])
    data = bcfnt.build(f)
    print('BCFNT %d 바이트 (한도 %d)' % (len(data), LIMIT))
    assert len(data) <= LIMIT, '공유 폰트 메모리 한도 초과'
    # 왕복 검사
    g = bcfnt.parse(data)
    assert g.cmap == f.cmap and len(g.sheets) == len(sheets)
    open(os.path.join(W, 'cbf_std_ko.bcfnt'), 'wb').write(data)
    return data


def preview(data):
    f = bcfnt.parse(data)
    text = ['新・光神話 パルテナの鏡', '시작하기 새 데이터 게임 방법', '피트, 파르테나 님! 메두사가 부활했어요.',
            'あいうえお カタカナ ABC 123 한글과 漢字']
    im = Image.new('L', (620, 40 * len(text)), 30)
    for r, line in enumerate(text):
        x = 4
        for ch in line:
            i = f.cmap.get(ord(ch), f.alter_idx)
            left, gw, cw = f.widths[i]
            s = f.sheets[i // (f.cols * f.rows)]
            k = i % (f.cols * f.rows)
            a = ctxb.decode(s, f.sheet_w, f.sheet_h, 0x6756, 0x6760).split()[3]
            gx, gy = (k % f.cols) * STRIDE, (k // f.cols) * (f.cell_h + 2)
            cell = a.crop((gx, gy, gx + f.cell_w, gy + f.cell_h))
            im.paste(255, (x + left, r * 40 + 5), cell.crop((0, 0, f.cell_w, f.cell_h)))
            x += cw
    im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
    p = os.path.join(W, 'preview.png')
    im.save(p)
    print('미리보기', p)


def romfs_single(name, blob):
    """파일 하나짜리 romfs level3."""
    nm = name.encode('utf-16le')
    nml = (len(nm) + 3) & ~3
    dirmeta = struct.pack('<IIIIII', 0, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0xFFFFFFFF, 0)
    filemeta = struct.pack('<IIQQII', 0, 0xFFFFFFFF, 0, len(blob), 0xFFFFFFFF, len(nm)) + nm + b'\0' * (nml - len(nm))
    dh = struct.pack('<I', 0); fh = struct.pack('<I', 0)
    hdr = 0x28
    dho = hdr; dmo = dho + len(dh); fho = dmo + len(dirmeta); fmo = fho + len(fh)
    dat = (fmo + len(filemeta) + 15) & ~15
    head = struct.pack('<10I', hdr, dho, len(dh), dmo, len(dirmeta), fho, len(fh), fmo, len(filemeta), dat)
    body = head + dh + dirmeta + fh + filemeta
    return body + b'\0' * (dat - len(body)) + blob


def install(data):
    lz = lz11.compress(data)
    print('LZ11 %d 바이트' % len(lz))
    work = os.path.join(W, 'cfa')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, 'romfs'))
    open(os.path.join(work, 'romfs', 'cbf_std.bcfnt.lz'), 'wb').write(lz)
    rsf = ('BasicInfo:\n  Title: SharedFont\n  ProductCode: CTR-N-SFNT\n  ContentType: Application\n'
           '  Logo: None\n\nTitleInfo:\n  UniqueId: 0x14002\n  Category: SharedContents\n\n'
           'Option:\n  UseOnSD: false\n  EnableCompress: false\n  EnableCrypt: false\n\n'
           'RomFs:\n  RootPath: romfs\n')
    open(os.path.join(work, 'font.rsf'), 'w').write(rsf)
    r = subprocess.run([os.path.join(BIN, 'makerom.exe'), '-f', 'cfa', '-o', 'font.cfa', '-rsf', 'font.rsf',
                        '-target', 't', '-ignoresign'], cwd=work, capture_output=True, text=True)
    print(r.stdout[-500:], r.stderr[-800:])
    cfa = os.path.join(work, 'font.cfa')
    assert os.path.exists(cfa), 'makerom 실패'
    print('CFA:', cfa)
    if '--cfa-only' in sys.argv:          # 배포용: Azahar 에 설치하지 않고 파일만
        return
    dst = os.path.join(NAND_TITLE, 'content')
    os.makedirs(dst, exist_ok=True)
    shutil.copy(cfa, os.path.join(dst, '00000000.app'))
    print('설치:', os.path.join(dst, '00000000.app'))


def main():
    if '--remove' in sys.argv:
        shutil.rmtree(NAND_TITLE, ignore_errors=True)
        print('제거:', NAND_TITLE)
        return
    data = build()
    preview(data)
    if '--preview' not in sys.argv:
        install(data)


if __name__ == '__main__':
    main()
