import sys,os,hashlib,struct; sys.path.insert(0,os.path.dirname(__file__)); import msbt
def groups(root):
    seen={}
    for r,ds,fs in os.walk(root):
        for f in fs:
            p=os.path.join(r,f).replace(os.sep,'/')
            with open(p,'rb') as fh:
                if fh.read(8)!=b'MsgStdBn': continue
            d=open(p,'rb').read()
            seen.setdefault(hashlib.md5(d).hexdigest(),[]).append(os.path.relpath(p,root).replace(os.sep,'/'))
    return sorted((sorted(v) for v in seen.values()), key=lambda x:x[0])
if __name__=='__main__':
    root=sys.argv[1]
    for ps in groups(root):
        m=msbt.load(os.path.join(root,ps[0])); a=m.section(b'ATR1')
        n,sz=struct.unpack_from('<II',a,0)
        print(len(m.texts), sz, len(ps), ps[0], m.label(0))
