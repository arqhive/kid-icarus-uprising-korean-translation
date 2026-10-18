# -*- coding: utf-8 -*-
"""CIA·3DS 패처 꾸리기 → release/patcher (payload·lib·bin) + release/python(임베디드 파이썬)

  python tools/build_all.py                    # 먼저 한글 romfs 를 만든다(release/luma)
  python tools/make_patcher.py v0.4.7 [--python <임베디드 파이썬 zip 또는 폴더>]

payload 에는 한글 romfs 파일, 배너 로고 텍스처(한글판), 게임 이름, 원본 파일 MD5 만 담는다.
배너·아이콘은 사용자 파일 안의 것을 고쳐 쓰므로 원본 배너·아이콘은 들어가지 않는다.
lib 에는 kiupatch·lz11 과 pyctr·pycryptodomex(설치된 것 복사), bin 에는 3dstool·makerom 을 넣는다.
"""
import sys, os, json, shutil, hashlib, zipfile, struct
sys.path.insert(0, os.path.dirname(__file__))
import lz11, cgfx, tex_encode
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TID = '0004000000030000'
TITLE = '신 광신화 파르테나의 거울'
LUMA_ROMFS = os.path.join(ROOT, 'release', 'luma', 'titles', TID, 'romfs')
ORIG_ROMFS = os.path.join(ROOT, 'extract', 'jp', 'romfs')
ORIG_BANNER = os.path.join(ROOT, 'extract', 'jp', 'exefs', 'banner.bin')
BANNER_PNG = os.path.join(ROOT, 'images', 'GPT', '홈배너')
LOGOS = {'JPN_JP0': '배너_로고_JPN_JP0_256x128.png', 'JPN_JP3': '배너_작은로고_JPN_JP3_64x32.png'}
PATCHER = os.path.join(ROOT, 'release', 'patcher')


def banner_logos():
    """원본 배너 일본 칸의 로고 텍스처 형식에 맞춰 한글 로고를 인코딩 → {이름: 바이트}"""
    b = open(ORIG_BANNER, 'rb').read()
    offs = struct.unpack_from('<17I', b, 0x08)
    cwav = struct.unpack_from('<I', b, 0x84)[0]
    ends = sorted(set(o for o in offs if o) | {cwav})
    o = offs[9]
    g = lz11.decompress(b[o:ends[ends.index(o) + 1]])
    out = {}
    for name, w, h, pica, off, size in cgfx.textures(g):
        if name in LOGOS:
            img = Image.open(os.path.join(BANNER_PNG, LOGOS[name])).convert('RGBA')
            assert img.size == (w, h), (name, img.size)
            out[name] = tex_encode.encode(img, pica, 1)
            assert len(out[name]) == size
    assert len(out) == len(LOGOS)
    return out


def build_payload(dst, version):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(LUMA_ROMFS, os.path.join(dst, 'romfs'))
    src_md5 = {}
    for root, _, files in os.walk(LUMA_ROMFS):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), LUMA_ROMFS).replace(os.sep, '/')
            src_md5[rel] = hashlib.md5(open(os.path.join(ORIG_ROMFS, rel), 'rb').read()).hexdigest()
    os.makedirs(os.path.join(dst, 'banner'))
    for name, data in banner_logos().items():
        open(os.path.join(dst, 'banner', name + '.bin'), 'wb').write(data)
    json.dump({'short': TITLE, 'long': TITLE}, open(os.path.join(dst, 'titles.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    json.dump({'version': version, 'title_id': TID, 'source_md5': src_md5},
              open(os.path.join(dst, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(src_md5)


def main():
    ver = sys.argv[1]
    py = sys.argv[sys.argv.index('--python') + 1] if '--python' in sys.argv else None
    n = build_payload(os.path.join(PATCHER, 'payload'), ver)
    lib = os.path.join(PATCHER, 'lib')
    os.makedirs(lib, exist_ok=True)
    for f in ('kiupatch.py', 'lz11.py'):
        shutil.copyfile(os.path.join(ROOT, 'tools', f), os.path.join(lib, f))
    import pyctr, Cryptodome
    for m in (pyctr, Cryptodome):
        d = os.path.join(lib, m.__name__)
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(os.path.dirname(m.__file__), d, ignore=shutil.ignore_patterns('__pycache__', '*.pyi', 'SelfTest'))
    b = os.path.join(PATCHER, 'bin')
    os.makedirs(b, exist_ok=True)
    for f in ('3dstool.exe', 'makerom.exe'):
        shutil.copyfile(os.path.join(ROOT, 'tools', 'bin', f), os.path.join(b, f))
    if py:
        dst = os.path.join(ROOT, 'release', 'python')
        if os.path.exists(dst):
            shutil.rmtree(dst)
        if os.path.isdir(py):
            shutil.copytree(py, dst)
        else:
            with zipfile.ZipFile(py) as z:
                for i in z.infolist():
                    if i.is_dir():
                        continue
                    parts = i.filename.replace('\\', '/').split('/')
                    if 'python' not in parts[:-1]:
                        continue      # 다른 배포 ZIP 에서 python/ 폴더만 꺼낸다
                    rel = parts[parts.index('python') + 1:]
                    out = os.path.join(dst, *rel)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    open(out, 'wb').write(z.read(i))
    print('패처 준비 완료: payload 파일 %d개, lib·bin → %s%s' % (n, PATCHER, ', 파이썬 → release/python' if py else ''))


if __name__ == '__main__':
    main()
