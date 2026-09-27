# 이미지 목록 -> 확인용 시트 (체크무늬 배경 + 파일명)
import sys, os
from PIL import Image, ImageDraw, ImageFont
def sheet(files, out, cell=200, cols=6):
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 11)
    rows = (len(files) + cols - 1) // cols
    W = cols * (cell + 8); H = rows * (cell + 30)
    im = Image.new('RGB', (W, H), (40, 40, 40)); dr = ImageDraw.Draw(im)
    for k, f in enumerate(files):
        x = (k % cols) * (cell + 8) + 4; y = (k // cols) * (cell + 30) + 4
        s = Image.open(f).convert('RGBA'); w, h = s.size
        sc = min(cell / w, cell / h, 2)
        s = s.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.NEAREST)
        bg = Image.new('RGBA', s.size, (128, 128, 128, 255))
        cb = ImageDraw.Draw(bg)
        for yy in range(0, s.size[1], 8):
            for xx in range(0, s.size[0], 8):
                if (xx // 8 + yy // 8) % 2: cb.rectangle([xx, yy, xx + 7, yy + 7], fill=(90, 90, 90, 255))
        bg.alpha_composite(s); im.paste(bg.convert('RGB'), (x, y))
        dr.text((x, y + cell + 2), os.path.basename(f)[:34], font=font, fill=(255, 255, 0))
        dr.text((x, y + cell + 15), '%dx%d' % (w, h), font=font, fill=(200, 200, 200))
    im.save(out)
if __name__ == '__main__':
    import glob
    out = sys.argv[1]; files = sorted(sum((glob.glob(g) for g in sys.argv[2:]), []))
    n = 36
    for i in range(0, len(files), n):
        sheet(files[i:i + n], out.replace('.png', '_%02d.png' % (i // n)))
    print(len(files), 'files', (len(files) + n - 1) // n, 'sheets')
