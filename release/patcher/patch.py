# -*- coding: utf-8 -*-
"""신 광신화 파르테나의 거울 한글 패치 적용기 — 일본판 CIA / 3DS 파일을 한글판으로 만든다.

  패치하기.bat 에 .cia 또는 .3ds 파일을 끌어다 놓는다 (여러 개 가능).
  python patch.py <파일> [<파일> ...]

결과는 원본과 같은 폴더에 `<원래 이름>_KO.cia` / `<원래 이름>_KO.3ds` 로 생긴다. 원본 파일은 바뀌지 않는다.
암호화된 파일이면 boot9.bin(필요하면 seeddb.bin)이 있어야 한다. 패치 폴더(이 파일의 한 단계 위)에 두거나
Azahar·Citra 의 sysdata 폴더, 사용자 폴더의 .3ds 폴더에 있으면 자동으로 찾는다.
"""
import json, os, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, 'lib'))
import kiupatch

PAYLOAD = os.path.join(HERE, 'payload')


def ask():
    print('\n일본판 신 광신화 파르테나의 거울 .cia 또는 .3ds 파일 경로를 입력하세요 (파일을 이 창에 끌어다 놓아도 됩니다).')
    return input('> ').strip().strip('"')


def main():
    man = json.load(open(os.path.join(PAYLOAD, 'manifest.json'), encoding='utf-8'))
    print('신 광신화 파르테나의 거울 한글 패치 %s (CIA·3DS 패처)\n' % man['version'])
    files = [a for a in sys.argv[1:] if a.strip()] or [ask()]
    ok = 0
    for src in files:
        src = src.strip('"')
        print('=' * 60 + '\n' + os.path.basename(src))
        if not os.path.isfile(src):
            print('[오류] 파일을 찾을 수 없습니다: %s' % src)
            continue
        stem, ext = os.path.splitext(src)
        if ext.lower() not in ('.cia', '.3ds', '.cci'):
            print('[오류] .cia 또는 .3ds 파일만 넣을 수 있습니다.')
            continue
        dst = stem + '_KO' + ('.cia' if ext.lower() == '.cia' else '.3ds')
        t = time.time()
        try:
            kiupatch.patch(src, dst, PAYLOAD, os.path.join(HERE, 'bin'), os.path.join(TOP, 'work'),
                           key_extra=(TOP, HERE))
        except SystemExit as e:
            print('[오류] %s' % e)
            continue
        except Exception:
            traceback.print_exc()
            print('[오류] 예상하지 못한 문제가 생겼습니다.')
            continue
        print('\n완료 (%d초): %s' % (time.time() - t, dst))
        ok += 1
    print('\n%d개 중 %d개 완료.' % (len(files), ok))
    return 0 if ok == len(files) else 1


if __name__ == '__main__':
    sys.exit(main())
