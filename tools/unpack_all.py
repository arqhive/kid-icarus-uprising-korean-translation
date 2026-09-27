import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from multiprocessing import Pool
import darc
SRC = sys.argv[1]; DST = sys.argv[2]
SKIP = ('music', 'voice', 'movie')

def job(rel):
    try:
        darc.extract(os.path.join(SRC, rel), os.path.join(DST, rel))
        return None
    except Exception as e:
        return '%s: %s' % (rel, e)

if __name__ == '__main__':
    todo = []
    for r, ds, fs in os.walk(SRC):
        for f in fs:
            rel = os.path.relpath(os.path.join(r, f), SRC)
            if rel.split(os.sep)[1] if os.sep in rel else '' in SKIP: pass
            parts = rel.split(os.sep)
            if len(parts) > 1 and parts[1] in SKIP: continue
            if f.endswith(('.zrc', '.arc')):
                todo.append(rel)
    print(len(todo), 'archives')
    with Pool(12) as p:
        for e in p.imap_unordered(job, todo):
            if e: print(e)
