# 전체 CGFX 텍스처 목록 -> JSON  (path, name, w, h, fmt, md5)
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(__file__))
import cgfx
root, out = sys.argv[1], sys.argv[2]
rows = []
for r, ds, fs in os.walk(root):
    for f in fs:
        p = os.path.join(r, f)
        with open(p, 'rb') as fh:
            if fh.read(4) != b'CGFX': continue
        d = open(p, 'rb').read()
        for t in cgfx.textures(d):
            name, w, h, pica, off, size = t
            md5 = hashlib.md5(d[off:off + size]).hexdigest()
            rows.append(dict(path=os.path.relpath(p, root).replace(os.sep, '/'), name=name, w=w, h=h,
                             fmt=cgfx.NAMES.get(pica, pica), off=off, size=size, md5=md5))
json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
print(len(rows), 'textures,', len({r['md5'] for r in rows}), 'unique')
