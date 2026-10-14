# -*- coding: utf-8 -*-
"""원본 / GPT 이미지 비교 시트.  python tools/gpt_sheets.py → review/이미지비교/*.png

- 보스 이름 배너는 BL(256)·BR(64)을 이어 붙여 한 장으로(이음매 확인)
- 체크무늬 배경(투명 확인), 작은 이미지는 확대
"""
import os, re, glob
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, 'images', '게임내')
GPT = os.path.join(ROOT, 'images', 'GPT', '게임내')
OUT = os.path.join(ROOT, 'review', '이미지비교')
FONT = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 13)
MAXW = 1200


def checker(w, h, s=8):
    im = Image.new('RGBA', (w, h), (150, 150, 150, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=(105, 105, 105, 255))
    return im


def show(im, scale):
    im = im.convert('RGBA').resize((im.width * scale, im.height * scale), Image.NEAREST)
    bg = checker(*im.size)
    bg.alpha_composite(im)
    return bg


def pairs():
    """[(분류, 제목, 원본 이미지, GPT 이미지)]"""
    out = []
    for cat in sorted(os.listdir(GPT)):
        files = sorted(os.listdir(os.path.join(GPT, cat)))
        used = set()
        for f in files:
            if f in used:
                continue
            m = re.match(r'(info_\w+?)_BL_(\d+)\.png$', f)
            if m:
                br = '%s_BR_%s.png' % (m.group(1), m.group(2))
                if br in files:
                    used |= {f, br}
                    def join(d):
                        a = Image.open(os.path.join(d, cat, f)).convert('RGBA')
                        b = Image.open(os.path.join(d, cat, br)).convert('RGBA')
                        im = Image.new('RGBA', (a.width + b.width, a.height))
                        im.paste(a, (0, 0)); im.paste(b, (a.width, 0))
                        return im
                    out.append((cat, f.replace('_BL_', '_BL+BR_'), join(ORIG), join(GPT)))
                    continue
            used.add(f)
            out.append((cat, f, Image.open(os.path.join(ORIG, cat, f)), Image.open(os.path.join(GPT, cat, f))))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for p in glob.glob(os.path.join(glob.escape(OUT), '*.png')):
        os.remove(p)
    bycat = {}
    for cat, name, a, b in pairs():
        bycat.setdefault(cat, []).append((name, a, b))
    n = 0
    for cat, items in bycat.items():
        blocks = []
        for name, a, b in items:
            scale = max(1, min(4, 480 // max(a.width, 1), 240 // max(a.height, 1)))
            A, B = show(a, scale), show(b, scale)
            w = A.width * 2 + 30
            h = A.height + 22
            blk = Image.new('RGB', (w, h), (30, 30, 30))
            ImageDraw.Draw(blk).text((0, 2), '%s  %dx%d  (왼쪽 원본 / 오른쪽 GPT)' % (name, a.width, a.height),
                                     font=FONT, fill=(255, 230, 80))
            blk.paste(A.convert('RGB'), (0, 20)); blk.paste(B.convert('RGB'), (A.width + 30, 20))
            blocks.append(blk)
        # 세로로 쌓되 높이 2400 넘으면 새 장
        page, pages, y = [], [], 0
        for b in blocks:
            if page and y + b.height > 2400:
                pages.append(page); page, y = [], 0
            page.append(b); y += b.height + 8
        if page:
            pages.append(page)
        for i, pg in enumerate(pages):
            W = max(b.width for b in pg); H = sum(b.height + 8 for b in pg)
            im = Image.new('RGB', (W, H), (30, 30, 30))
            y = 0
            for b in pg:
                im.paste(b, (0, y)); y += b.height + 8
            im.save(os.path.join(OUT, '%s_%02d.png' % (cat, i + 1)))
            n += 1
    print('시트 %d장 → %s' % (n, OUT))


if __name__ == '__main__':
    main()
