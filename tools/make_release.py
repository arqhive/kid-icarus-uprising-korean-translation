# -*- coding: utf-8 -*-
"""배포 ZIP 세 개 만들기.

  python tools/build_all.py
  python tools/build_sysfont.py --cfa-only                           # Azahar 한글 시스템 폰트(work/font/cfa/font.cfa)
  python tools/make_patcher.py v0.4.7 [--python <임베디드 파이썬>]      # release/patcher·release/python 채우기
  python tools/make_release.py v0.4.7

release/AKDJ_KPatch_<버전>_LayeredFS.zip
  luma/titles/0004000000030000/romfs/...   SD 카드 루트에 푸는 LayeredFS 패치
release/AKDJ_KPatch_<버전>_CIA.zip
  AKDJ_KPatch_<버전>_CIA/패치하기.bat, patcher/, python/   일본판 CIA·3DS 를 한글판으로 만드는 패처
release/AKDJ_KPatch_<버전>_AzaharFont.zip
  Azahar 한글 시스템 폰트(00000000.app)와 설치 안내
셋 다 README_KO.txt(= release/README_한국어.txt), LICENSE.txt 를 넣는다.
"""
import sys, os, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TID = '0004000000030000'
REL = os.path.join(ROOT, 'release')
LUMA = os.path.join(REL, 'luma')
FONT_CFA = os.path.join(ROOT, 'work', 'font', 'cfa', 'font.cfa')
NAME = 'AKDJ_KPatch_%s'


def add_tree(z, src, arc):
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            p = os.path.join(root, f)
            z.write(p, (arc + '/' + os.path.relpath(p, src).replace(os.sep, '/')).lstrip('/'))
            n += 1
    return n


def main():
    ver = sys.argv[1]
    if not os.path.isdir(os.path.join(LUMA, 'titles', TID, 'romfs')):
        sys.exit('release/luma 가 비어 있습니다. 먼저 python tools/build_all.py 를 실행하세요.')
    if not os.path.isdir(os.path.join(REL, 'python')) or not os.path.isdir(os.path.join(REL, 'patcher', 'payload')):
        sys.exit('패처가 준비되지 않았습니다. 먼저 python tools/make_patcher.py %s 를 실행하세요.' % ver)
    if not os.path.isfile(FONT_CFA):
        sys.exit('Azahar 폰트가 없습니다. 먼저 python tools/build_sysfont.py --cfa-only 를 실행하세요.')
    docs = [(os.path.join(REL, 'README_한국어.txt'), 'README_KO.txt'), (os.path.join(ROOT, 'LICENSE'), 'LICENSE.txt')]

    a = os.path.join(REL, (NAME + '_LayeredFS.zip') % ver)
    with zipfile.ZipFile(a, 'w', zipfile.ZIP_DEFLATED) as z:
        n = add_tree(z, LUMA, 'luma')
        for p, name in docs:
            z.write(p, name)
    print('%s: LayeredFS 파일 %d개 (%s 바이트)' % (a, n, format(os.path.getsize(a), ',')))

    b = os.path.join(REL, (NAME + '_CIA.zip') % ver)
    top = (NAME + '_CIA') % ver
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(REL, '패치하기.bat'), top + '/패치하기.bat')
        n = add_tree(z, os.path.join(REL, 'patcher'), top + '/patcher')
        n += add_tree(z, os.path.join(REL, 'python'), top + '/python')
        for p, name in docs:
            z.write(p, top + '/' + name)
    print('%s: 파일 %d개 (%s 바이트)' % (b, n + 3, format(os.path.getsize(b), ',')))

    c = os.path.join(REL, (NAME + '_AzaharFont.zip') % ver)
    with zipfile.ZipFile(c, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(FONT_CFA, 'nand/00000000000000000000000000000000/title/0004009b/00014002/content/00000000.app')
        for p, name in docs:
            z.write(p, name)
    print('%s: (%s 바이트)' % (c, format(os.path.getsize(c), ',')))


if __name__ == '__main__':
    main()
