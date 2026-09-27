# -*- coding: utf-8 -*-
"""개발용: 한글판 CIA(또는 3DS) 만들기. 배포 패처와 같은 kiupatch 를 쓴다.

  python tools/build_all.py
  python tools/build_cia.py [--cia <일본판.cia>] [--out <결과.cia 또는 .3ds>]

--cia 를 빼면 작업 폴더의 일본판 CIA(CTR-P-AKDJ)를, --out 을 빼면 바탕화면 KidIcarusUprising_KO.cia 를 쓴다.
payload 는 work/payload 에 새로 만든다(make_patcher.build_payload).
외부 도구가 한글 경로를 못 받는 경우가 있어 작업 폴더는 영문 경로(사용자 폴더의 kiu_work)를 쓴다.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import kiupatch, make_patcher

ROOT = make_patcher.ROOT


def main():
    a = sys.argv
    src = a[a.index('--cia') + 1] if '--cia' in a else \
        os.path.join(ROOT, [f for f in os.listdir(ROOT) if 'AKDJ' in f and f.endswith('.cia')][0])
    dst = a[a.index('--out') + 1] if '--out' in a else \
        os.path.join(os.path.expanduser('~'), 'Desktop', 'KidIcarusUprising_KO.cia')
    t0 = time.time()
    payload = os.path.join(ROOT, 'work', 'payload')
    n = make_patcher.build_payload(payload, 'dev')
    print('payload: romfs 파일 %d개' % n)
    work = os.path.join(os.path.expanduser('~'), 'kiu_work')
    kiupatch.patch(src, dst, payload, os.path.join(ROOT, 'tools', 'bin'), work)
    print('완료: %s (%.1f MB, %.0f초)' % (dst, os.path.getsize(dst) / 1e6, time.time() - t0))


if __name__ == '__main__':
    main()
