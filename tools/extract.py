# -*- coding: utf-8 -*-
"""CIA 에서 romfs 전체와 exefs(banner/icon/code) 를 뽑는다.
  python tools/extract.py <cia> <출력폴더>
"""
import sys, os
sysdata = os.path.join(os.environ.get('APPDATA', ''), 'Azahar', 'sysdata')
for var, name in (('BOOT9_PATH', 'boot9.bin'), ('SEEDDB_PATH', 'seeddb.bin')):
    if var not in os.environ and os.path.exists(os.path.join(sysdata, name)):
        os.environ[var] = os.path.join(sysdata, name)
from pyctr.type.cia import CIAReader


def walk(romfs, path):
    info = romfs.get_info_from_path(path)
    if hasattr(info, 'contents'):
        for name in info.contents:
            yield from walk(romfs, path.rstrip('/') + '/' + name)
    else:
        yield path


def main():
    cia, out = sys.argv[1], sys.argv[2]
    n = 0
    with CIAReader(cia) as c:
        print('contents:', [(k, v.program_id if hasattr(v, 'program_id') else '') for k, v in c.contents.items()])
        ncch = c.contents[0]
        romfs = ncch.romfs
        for p in walk(romfs, '/'):
            dst = os.path.join(out, 'romfs', p.lstrip('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with romfs.open(p) as f, open(dst, 'wb') as o:
                o.write(f.read())
            n += 1
        os.makedirs(os.path.join(out, 'exefs'), exist_ok=True)
        for name in ncch.exefs.entries:
            with ncch.exefs.open(name) as f, open(os.path.join(out, 'exefs', name + '.bin'), 'wb') as o:
                o.write(f.read())
    print('%d files -> %s' % (n, out))


if __name__ == '__main__':
    main()
