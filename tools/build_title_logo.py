# -*- coding: utf-8 -*-
"""타이틀 로고(MenShowTop0000) 채색판 만들기.

원본 게임은 로고 그림의 글자 몸통을 투명하게 두고, 그 뒤에 몸통 모양(일본어)의 3D 메시를
그라데이션(MenShowTop0001)으로 칠해 비치게 한다. 한글판은 메시를 끄고(build_all.plan_title)
로고 그림의 몸통을 직접 같은 그라데이션으로 칠해 불투명하게 만든다. 그래서 텍스처 형식을 LA4 → ETC1A4 로 바꾼다.

입력 (로컬, 저장소에 없음):
  images/GPT/게임내/메뉴/menu_000_MenShowTop0000.png   한글 로고(흑백·알파)
  images/GPT/타이틀_몸통마스크_512x256.png              한글 큰 제목 몸통 마스크(흰색 = 몸통)
  unpack/jp/.../MenShowTop0001                          원본 그라데이션 텍스처
출력: work/title_color/MenShowTop0000_color.png
"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import cgfx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, 'images', 'GPT', '게임내', '메뉴', 'menu_000_MenShowTop0000.png')
MASK = os.path.join(ROOT, 'images', 'GPT', '타이틀_몸통마스크_512x256.png')
BIND = os.path.join(ROOT, 'unpack', 'jp', 'jp', 'menu', '000.zrc', 'menu', 'bind.arc', 'bind', '00.bcres')
OUT = os.path.join(ROOT, 'work', 'title_color', 'MenShowTop0000_color.png')
GRAD_ROWS = 86        # 그라데이션 텍스처 32x128 중 색이 있는 윗부분(빨강 → 노랑 → 흰색), 아래는 검정


def make():
    d = open(BIND, 'rb').read()
    t = [x for x in cgfx.textures(d) if x[0] == 'MenShowTop0001'][0]
    g = np.asarray(cgfx.decode(d, t).convert('RGB')).astype(float)[:, t[1] // 2]
    body = np.asarray(Image.open(MASK).convert('L')) > 127
    out = np.asarray(Image.open(LOGO).convert('RGBA')).astype(float).copy()
    ys = np.where(body.any(1))[0]
    y0, y1 = ys.min(), ys.max()
    for y in range(y0, y1 + 1):
        m = body[y]
        out[y, m, :3] = g[int((y - y0) / (y1 - y0 + 1) * (GRAD_ROWS - 1))]
        out[y, m, 3] = 255
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    Image.fromarray(out.clip(0, 255).astype(np.uint8), 'RGBA').save(OUT)
    return OUT


if __name__ == '__main__':
    print(make())
