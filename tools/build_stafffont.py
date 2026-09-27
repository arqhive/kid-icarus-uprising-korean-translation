# -*- coding: utf-8 -*-
"""스태프롤 전용 폰트(stage/a2600.zrc/stage/bin.arc/bin/fnt.bin)에 번역에 쓴 글자를 추가한다.

원본: 426자, 25x25 칸, 32x1024 A4 시트(세로 39칸, 칸 간격 26). 명조 계열이라 한글은 송명(SongMyung, OFL).
  python tools/build_stafffont.py [--preview]   → work/font/fnt_staff_ko.bin (+ work/font/staff_preview.png)
build_all.py 가 make() 를 불러 쓴다.
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import bcfnt, ctxb, tex_encode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'unpack', 'jp', 'jp', 'stage', 'a2600.zrc', 'stage', 'bin.arc', 'bin', 'fnt.bin')
FONT = os.path.join(ROOT, 'tools', 'fonts', 'SongMyung-Regular.ttf')
PITCH = 26


def needed_chars():
    K = json.load(open(os.path.join(ROOT, 'translation', 'ko.json'), encoding='utf-8'))
    U = json.load(open(os.path.join(ROOT, 'translation', 'units.json'), encoding='utf-8'))
    s = set()
    for u in U:
        if u['cat'] == '스태프롤' and u['key'] in K:
            s |= set(K[u['key']].replace('\n', ''))
    return s


def glyph(f, i):
    per = f.cols * f.rows
    a = np.asarray(ctxb.decode(f.sheets[i // per], f.sheet_w, f.sheet_h, 0x6756, 0x6760).split()[3]) // 17
    k = i % per
    x, y = (k % f.cols) * PITCH, (k // f.cols) * PITCH
    return a[y:y + f.cell_h, x:x + f.cell_w].copy()


def render(chars, f, ref):
    """ref: 기준 한자 글리프(알파) — 잉크 위아래를 맞춘다."""
    SS = 4
    ys = [y for y in range(ref.shape[0]) if ref[y].max() > 0]
    top, bot = ys[0], ys[-1]
    size = (bot - top + 1) * SS
    font = ImageFont.truetype(FONT, int(size * 1.12))
    probe = Image.new('L', (f.cell_w * SS * 2, f.cell_h * SS * 2), 0)
    ImageDraw.Draw(probe).text((0, 0), '한', font=font, fill=255)
    bb = probe.getbbox()
    dy = top * SS - bb[1]
    out = {}
    for c in chars:
        if c == '·':   # 가운뎃점: 폰트 글리프가 너무 작아 직접 그린다
            a = np.zeros((f.cell_h, f.cell_w), np.uint8)
            cy = (top + bot) // 2
            a[cy - 1:cy + 2, 3:6] = 15
            out[c] = (a, (0, 9, 9))
            continue
        im = Image.new('L', (f.cell_w * SS, f.cell_h * SS), 0)
        bx = font.getbbox(c)
        w = bx[2] - bx[0]
        hangul = 0xAC00 <= ord(c) <= 0xD7A3
        x0 = (f.cell_w * SS - w) // 2 - bx[0] if hangul else SS - bx[0]
        ImageDraw.Draw(im).text((x0, dy), c, font=font, fill=255)
        a = np.asarray(im.resize((f.cell_w, f.cell_h), Image.BOX), dtype=np.float32)
        a = np.clip(np.round(a / 17), 0, 15).astype(np.uint8)
        if hangul:
            wd = (1, f.cell_w - 2, f.cell_w)
        else:
            xs = [x for x in range(f.cell_w) if a[:, x].max() > 0] or [0]
            wd = (0, xs[-1] + 1, xs[-1] + 2)
        out[c] = (a, wd)
    return out


def make():
    f = bcfnt.parse(open(SRC, 'rb').read())
    per = f.cols * f.rows
    n0 = max(f.widths) + 1
    old = [glyph(f, i) for i in range(n0)]
    new = sorted(c for c in needed_chars() if ord(c) not in f.cmap and c != '\n')
    ref = old[f.cmap[ord('高')]]
    rend = render(new, f, ref)
    alphas = old + [rend[c][0] for c in new]
    for k, c in enumerate(new):
        f.widths[n0 + k] = rend[c][1]
        f.cmap[ord(c)] = n0 + k
    nsheets = (len(alphas) + per - 1) // per
    sheets = []
    for s in range(nsheets):
        a = np.zeros((f.sheet_h, f.sheet_w), np.uint8)
        for k, g in enumerate(alphas[s * per:(s + 1) * per]):
            x, y = (k % f.cols) * PITCH, (k // f.cols) * PITCH
            a[y:y + f.cell_h, x:x + f.cell_w] = g
        img = Image.fromarray(np.dstack([np.full_like(a, 255)] * 3 + [a * 17]).astype(np.uint8), 'RGBA')
        sheets.append(tex_encode.encode_level(img, 11))
    f.sheets = sheets
    data = bcfnt.build(f)
    g = bcfnt.parse(data)
    assert g.cmap == f.cmap and bcfnt.check_walk(data)[0]
    return data, new


def preview(data, path):
    f = bcfnt.parse(data)
    lines = ['디렉터 & 시나리오', '사쿠라이 마사히로', '다카야마 미나미·히사카와 아야', '高山 みなみ Nintendo']
    im = Image.new('L', (560, 34 * len(lines)), 30)
    for r, line in enumerate(lines):
        x = 4
        for ch in line:
            i = f.cmap.get(ord(ch), f.alter_idx)
            left, gw, cw = f.widths.get(i, (0, 8, 8))
            a = glyph(f, i)
            im.paste(255, (x + left, r * 34 + 4), Image.fromarray((a * 17).astype(np.uint8)))
            x += cw
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(path)


if __name__ == '__main__':
    data, new = make()
    out = os.path.join(ROOT, 'work', 'font', 'fnt_staff_ko.bin')
    open(out, 'wb').write(data)
    print('추가 %d자 → %s (%d 바이트)' % (len(new), out, len(data)))
    if '--preview' in sys.argv:
        preview(data, os.path.join(ROOT, 'work', 'font', 'staff_preview.png'))
