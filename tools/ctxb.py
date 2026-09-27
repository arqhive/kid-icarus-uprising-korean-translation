"""Grezzo ctxb 텍스처 추출/디코드 (3DS PICA 포맷)."""
import struct
from PIL import Image

ETC_MOD=[[2,8,-2,-8],[5,17,-5,-17],[9,29,-9,-29],[13,42,-13,-42],[18,60,-18,-60],[24,80,-24,-80],[33,106,-33,-106],[47,183,-47,-183]]
def _c(v): return 0 if v<0 else 255 if v>255 else v
def etc1_block(blk):
    hi,lo=struct.unpack('<II',blk[:8]) if False else (None,None)
    v=int.from_bytes(blk[:8],'little')
    flip=(v>>32)&1; diff=(v>>33)&1
    t1=(v>>37)&7; t2=(v>>34)&7
    if diff:
        def d3(x): return x-8 if x>=4 else x
        r=(v>>59)&31; g=(v>>51)&31; b=(v>>43)&31
        r2=r+d3((v>>56)&7); g2=g+d3((v>>48)&7); b2=b+d3((v>>40)&7)
        e=lambda x:(x<<3)|(x>>2)
        c1=(e(r),e(g),e(b)); c2=(e(r2&31),e(g2&31),e(b2&31))
    else:
        e=lambda x:x*17
        c1=(e((v>>60)&15),e((v>>52)&15),e((v>>44)&15)); c2=(e((v>>56)&15),e((v>>48)&15),e((v>>40)&15))
    out=[[None]*4 for _ in range(4)]
    for x in range(4):
        for y in range(4):
            i=x*4+y
            sub=(y>=2) if flip else (x>=2)
            base,tb=(c2,t2) if sub else (c1,t1)
            idx=((v>>i)&1)|(((v>>(i+16))&1)<<1)
            m=ETC_MOD[tb][[0,1,2,3][idx]]
            # idx mapping: 0->+a,1->+b,2->-a,3->-b
            m=[ETC_MOD[tb][0],ETC_MOD[tb][1],-ETC_MOD[tb][0],-ETC_MOD[tb][1]][idx]
            out[y][x]=(_c(base[0]+m),_c(base[1]+m),_c(base[2]+m))
    return out

def morton(i):
    x=y=0
    for b in range(3):
        x|=((i>>(2*b))&1)<<b; y|=((i>>(2*b+1))&1)<<b
    return x,y
MT=[morton(i) for i in range(64)]

def decode(data,w,h,pf,dt):
    img=Image.new('RGBA',(w,h)); px=img.load()
    if pf in (0x675a,0x675b):
        a4=pf==0x675b; bs=16 if a4 else 8; p=0
        for ty in range(0,h,8):
            for tx in range(0,w,8):
                for sb in range(4):
                    sx=tx+(sb&1)*4; sy=ty+(sb>>1)*4
                    if a4: al=int.from_bytes(data[p:p+8],'little'); blk=data[p+8:p+16]
                    else: blk=data[p:p+8]
                    p+=bs
                    c=etc1_block(blk)
                    for y in range(4):
                        for x in range(4):
                            a=((al>>((x*4+y)*4))&15)*17 if a4 else 255
                            px[sx+x,sy+y]=c[y][x]+(a,)
        return img
    bpp={(0x6758,0x1401):16,(0x6758,0x6760):8,(0x6752,0x8033):16,(0x6752,0x8034):16,(0x6754,0x8363):16,(0x6752,0x1401):32,(0x6754,0x1401):24,(0x6756,0x1401):8,(0x6757,0x1401):8,(0x6756,0x6760):4,(0x6757,0x6760):4}[(pf,dt)]
    p=0
    for ty in range(0,h,8):
        for tx in range(0,w,8):
            for i in range(64):
                x,y=MT[i]; X,Y=tx+x,ty+y
                if bpp==4:
                    n=(data[p>>1]>>((p&1)*4))&15; p+=1; v=n*17
                    px[X,Y]=(255,255,255,v) if pf==0x6756 else (v,v,v,255); continue
                b=data[p:p+bpp//8]; p+=bpp//8
                if (pf,dt)==(0x6758,0x1401): px[X,Y]=(b[1],b[1],b[1],b[0])
                elif (pf,dt)==(0x6758,0x6760): l=(b[0]>>4)*17; px[X,Y]=(l,l,l,(b[0]&15)*17)
                elif dt==0x8033: v=b[0]|b[1]<<8; px[X,Y]=(((v>>12)&15)*17,((v>>8)&15)*17,((v>>4)&15)*17,(v&15)*17)
                elif dt==0x8034: v=b[0]|b[1]<<8; e=lambda q:(q<<3)|(q>>2); px[X,Y]=(e((v>>11)&31),e((v>>6)&31),e((v>>1)&31),255*(v&1))
                elif dt==0x8363: v=b[0]|b[1]<<8; px[X,Y]=(((v>>11)&31)<<3,((v>>5)&63)<<2,(v&31)<<3,255)
                elif bpp==32: px[X,Y]=(b[3],b[2],b[1],b[0])
                elif bpp==24: px[X,Y]=(b[2],b[1],b[0],255)
                elif pf==0x6756: px[X,Y]=(255,255,255,b[0])
                else: px[X,Y]=(b[0],b[0],b[0],255)
    return img

def iter_ctxb(d):
    i=0
    while True:
        i=d.find(b'ctxb',i)
        if i<0: return
        size,cnt,_,coff,toff=struct.unpack_from('<5I',d,i+4)
        c=i+coff
        if d[c:c+4]==b'tex ':
            n=struct.unpack_from('<I',d,c+8)[0]
            for k in range(n):
                e=c+12+k*36
                ln,a,b,w,h,pf,dt,off=struct.unpack_from('<I6HI',d,e)
                yield i,k,w,h,pf,dt,d[i+toff+off:i+toff+off+ln]
        i+=4
