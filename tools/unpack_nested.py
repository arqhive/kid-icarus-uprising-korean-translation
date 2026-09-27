import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import darc
ROOT = sys.argv[1]
n = 0
changed = True
while changed:
    changed = False
    for r, ds, fs in os.walk(ROOT):
        for f in fs:
            p = os.path.join(r, f)
            with open(p, 'rb') as fh: h = fh.read(8)
            if h[:4] == b'darc' or (h[:1] == b'\x11' and h[4:8] == b'darc'):
                d = darc.load(p)
                os.remove(p)
                for q, o, s in darc.parse(d):
                    dst = os.path.join(p, q)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    open(dst, 'wb').write(d[o:o+s])
                n += 1; changed = True
print(n, 'nested')
