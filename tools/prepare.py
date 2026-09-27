# -*- coding: utf-8 -*-
"""원본 준비를 한 번에: CIA 추출 → darc 풀기 → 원문·화자 추출 → 번역 단위 만들기.

  python tools/prepare.py "일본판.cia" ["북미판.cia"]

1. extract/jp (북미판을 주면 extract/us 도)      tools/extract.py
2. unpack/jp (unpack/us)                          tools/unpack_all.py + unpack_nested.py
3. text/신광신화_전체텍스트.json                   tools/extract_text.py (영어판은 참고용, 없어도 됨)
4. translation/units.json                          tools/tl.py prep
그다음 python tools/build_all.py 로 빌드한다.
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda n: os.path.join(ROOT, 'tools', n)


def run(*a):
    print('>', ' '.join(os.path.basename(x) if x.endswith('.py') else x for x in a))
    subprocess.run([sys.executable] + list(a), cwd=ROOT, check=True)


def main():
    cias = sys.argv[1:]
    if not cias:
        sys.exit(__doc__)
    for cia, reg in zip(cias, ('jp', 'us')):
        run(T('extract.py'), cia, os.path.join('extract', reg))
        run(T('unpack_all.py'), os.path.join('extract', reg, 'romfs'), os.path.join('unpack', reg))
        run(T('unpack_nested.py'), os.path.join('unpack', reg))
    run(T('extract_text.py'))
    run(T('tl.py'), 'prep')


if __name__ == '__main__':
    main()
