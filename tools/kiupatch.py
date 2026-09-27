# -*- coding: utf-8 -*-
"""신 광신화 파르테나의 거울 한글판 CIA/3DS 만들기 — 개발 도구(build_cia.py)와 배포 패처(release/patcher)가 함께 쓰는 핵심.
(에버 오아시스 한글 패치의 eopatch.py 를 이 게임에 맞게 고친 것)

payload 폴더 구조
  manifest.json          버전, 타이틀 ID, 원본 파일 MD5(교체 대상 romfs 파일)
  romfs/...              교체할 romfs 파일 (LayeredFS 폴더와 같은 구조, jp/...)
  banner/<텍스처>.bin    배너 일본 칸 CGFX 의 한글 로고 텍스처 데이터(JPN_JP0 256x128, JPN_JP3 64x32, ETC1)
  titles.json            HOME 메뉴 짧은 제목·긴 제목

순서
  1. pyctr 로 CIA 콘텐츠 / 3DS 파티션을 모두 복호화 (본편은 seed 암호화 → boot9.bin·seeddb.bin 필요)
  2. 3dstool 로 본편 CXI 를 펼쳐 ExeFS 의 banner·icon 을 고치고, romfs 파일을 교체
  3. 3dstool 로 평문 CXI(--not-encrypt)를 다시 싸고 makerom 으로 CIA 또는 3DS(CCI)로 묶는다

외부 도구는 한글 경로를 제대로 못 받을 수 있어서, 작업 폴더를 cwd 로 두고 짧은 영문 상대 경로만 넘긴다.
"""
import hashlib, json, os, shutil, struct, subprocess, sys

TID = '0004000000030000'
JPN, KOR = 9, 15                  # CBMD 지역 칸: 9 = JPN_JP, 15 = KOR_KO (원본은 한국 칸이 비어 있어 공통 칸을 씀)

log = print


# ---------------------------------------------------------------- 키

def key_dirs(extra=()):
    env = os.environ
    return [d for d in list(extra) + [
        os.path.join(env.get('APPDATA', ''), 'Azahar', 'sysdata'),
        os.path.join(env.get('APPDATA', ''), 'Citra', 'sysdata'),
        os.path.join(env.get('APPDATA', ''), 'Lime3DS', 'sysdata'),
        os.path.join(os.path.expanduser('~'), '.3ds'),
        os.path.join(os.path.expanduser('~'), '3ds'),
    ] if d]


def find_key(name, dirs):
    for d in dirs:
        p = os.path.join(d, name)
        if os.path.isfile(p): return p
    return None


# ---------------------------------------------------------------- 배너·아이콘

def lz11_mod():
    import lz11
    return lz11


def cgfx_textures(cgfx):
    """CGFX 안의 TXOB: [(이름, 너비, 높이, PICA 형식, 데이터 오프셋, 크기)]"""
    out = []; i = 0
    while True:
        i = cgfx.find(b'TXOB', i)
        if i < 0: return out
        base = i - 4
        W = struct.unpack_from('<20I', cgfx, base)
        no = base + 0x0C + W[3]
        name = cgfx[no:cgfx.index(b'\0', no)].decode('ascii', 'replace') if 0 < W[3] < len(cgfx) else '?'
        out.append((name, W[7], W[6], W[13], base + 18 * 4 + W[18], W[17]))
        i += 4


def patch_banner(b, logos):
    """CBMD 일본 칸 CGFX 의 로고 텍스처를 logos{이름: 바이트}로 바꾸고, 한국 칸이 일본 칸을 쓰게 한 뒤 오프셋 표를 다시 쓴다."""
    lz11 = lz11_mod()
    offs = list(struct.unpack_from('<17I', b, 0x08)); cwav = struct.unpack_from('<I', b, 0x84)[0]
    ends = sorted(set(o for o in offs if o) | {cwav})
    span = {o: ends[ends.index(o) + 1] for o in offs if o}
    blobs = {o: b[o:span[o]] for o in span}
    o = offs[JPN]
    if not o: raise SystemExit('배너에 일본 칸이 없습니다.')
    cgfx = bytearray(lz11.decompress(blobs[o]))
    n = 0
    for name, w, h, fmt, data, size in cgfx_textures(cgfx):
        if name in logos:
            if size != len(logos[name]):
                raise SystemExit('배너 로고 그림 형식이 예상과 다릅니다: %s' % name)
            cgfx[data:data + size] = logos[name]; n += 1
    if n != len(logos): raise SystemExit('배너에서 일본어 로고 그림을 찾지 못했습니다.')
    blobs[o] = lz11.compress(bytes(cgfx))
    offs[KOR] = o
    out = bytearray(b[:0x88]); new = {}
    for k in sorted(blobs):
        new[k] = len(out); out += blobs[k]
    struct.pack_into('<17I', out, 0x08, *[new[x] if x else 0 for x in offs])
    out += bytes((-len(out)) % 0x20)
    struct.pack_into('<I', out, 0x84, len(out))
    out += b[cwav:]
    return bytes(out)


def patch_smdh(icon, short, long_):
    out = bytearray(icon)
    if out[:4] != b'SMDH': raise SystemExit('아이콘(SMDH) 형식이 아닙니다.')
    def put(off, text, chars):
        raw = text.encode('utf-16-le')
        out[off:off + chars * 2] = raw + b'\0' * (chars * 2 - len(raw))
    for i in range(12):
        base = 8 + i * 0x200
        put(base, short, 0x40); put(base + 0x80, long_, 0x80)
        put(base + 0x180, 'Nintendo', 0x40)
    return bytes(out)


def rebuild_exefs(d, patches):
    entries = []
    for i in range(10):
        name, off, size = struct.unpack_from('<8sII', d, i * 16)
        if not size: continue
        key = name.rstrip(b'\0').decode()
        entries.append((name, key, patches.get(key, d[0x200 + off:0x200 + off + size])))
    hdr = bytearray(0x200); blob = bytearray()
    for i, (name, key, body) in enumerate(entries):
        struct.pack_into('<8sII', hdr, i * 16, name, len(blob), len(body))
        hdr[0x200 - (i + 1) * 32:0x200 - i * 32] = hashlib.sha256(body).digest()
        blob += body
        blob += b'\0' * ((-len(blob)) % 0x200)
    return bytes(hdr) + bytes(blob)


def exefs_file(d, key):
    for i in range(10):
        name, off, size = struct.unpack_from('<8sII', d, i * 16)
        if size and name.rstrip(b'\0').decode() == key: return d[0x200 + off:0x200 + off + size]
    return None


# ---------------------------------------------------------------- 도구 실행

class Tools:
    def __init__(self, bindir, work):
        self.bin = bindir; self.work = work

    def run(self, name, args, logname):
        exe = os.path.join(self.bin, name + ('.exe' if os.name == 'nt' else ''))
        with open(os.path.join(self.work, logname + '.log'), 'wb') as f:
            r = subprocess.run([exe] + args, cwd=self.work, stdout=f, stderr=subprocess.STDOUT)
        if r.returncode:
            tail = open(os.path.join(self.work, logname + '.log'), encoding='utf-8', errors='replace').read()[-1500:]
            raise SystemExit('%s 실패:\n%s' % (name, tail))


def md5_file(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- 입력

KEY_HELP = ' 암호화된 파일은 boot9.bin 과 seeddb.bin 이 필요합니다. README_한국어.txt 를 확인하세요.'


def key_error(e):
    name = type(e).__name__
    if 'Seed' in name: return 'seed 암호화를 풀 seeddb.bin 이 없거나 이 게임의 seed 가 들어 있지 않습니다.' + KEY_HELP
    if 'Bootrom' in name or 'Keyslot' in name: return '암호화를 풀 boot9.bin 을 찾지 못했습니다.' + KEY_HELP
    return '파일을 읽지 못했습니다 (%s: %s).%s' % (name, e, KEY_HELP)


def raw_cci_partitions(path):
    """키 없이 3DS(NCSD)의 파티션 위치를 읽는다. 모두 평문(NoCrypto)이어야 한다 → [(번호, 오프셋, 크기)]"""
    with open(path, 'rb') as f:
        h = f.read(0x200)
        if h[0x100:0x104] != b'NCSD': raise SystemExit('3DS(NCSD) 파일이 아닙니다.')
        out = []
        for i in range(8):
            off, size = struct.unpack_from('<II', h, 0x120 + i * 8)
            if not size: continue
            f.seek(off * 0x200); n = f.read(0x200)
            if n[0x100:0x104] != b'NCCH': raise SystemExit('파티션 %d 가 NCCH 가 아닙니다.' % i)
            if not n[0x18F] & 0x04: raise SystemExit('암호화된 3DS 파일입니다.' + KEY_HELP)
            if i == 0 and '%016x' % struct.unpack_from('<Q', n, 0x118)[0] != TID:
                raise SystemExit('일본판 신 광신화 파르테나의 거울(%s) 파일이 아닙니다.' % TID)
            out.append((i, off * 0x200, size * 0x200))
    return out


def raw_cia_contents(path):
    """키 없이 CIA 콘텐츠 위치를 읽는다. 콘텐츠·NCCH 모두 평문이어야 한다 → ([(번호, ID, 오프셋, 크기)], 버전)"""
    al = lambda x: (x + 63) & ~63
    with open(path, 'rb') as f:
        hsize, _t, _v, clen, tlen, tmdlen, _m = struct.unpack('<IHHIIII', f.read(0x18))
        tmd_off = al(al(al(hsize) + clen) + tlen)
        f.seek(tmd_off); tmd = f.read(tmdlen)
        SIG = {0x10000: 0x23C, 0x10001: 0x13C, 0x10002: 0x7C, 0x10003: 0x23C, 0x10004: 0x13C, 0x10005: 0x7C}
        body = 4 + SIG[struct.unpack_from('>I', tmd, 0)[0]]
        v = struct.unpack_from('>H', tmd, body + 0x9C)[0]
        count = struct.unpack_from('>H', tmd, body + 0x9E)[0]
        rec = body + 0x9C + 4 + 0x24 + 36 * 64
        off = al(tmd_off + tmdlen); out = []
        for i in range(count):
            cid, idx, ctype, size = struct.unpack_from('>IHHQ', tmd, rec + i * 0x30)
            if ctype & 1: raise SystemExit('암호화된 CIA 입니다.' + KEY_HELP)
            f.seek(off); n = f.read(0x200)
            if n[0x100:0x104] != b'NCCH' or not n[0x18F] & 0x04:
                raise SystemExit('암호화된 CIA 입니다.' + KEY_HELP)
            out.append((idx, cid, off, size)); off = al(off + size)
    return out, '%d.%d.%d' % (v >> 10, (v >> 4) & 63, v & 15)


# ---------------------------------------------------------------- 본체

def patch(src, dst, payload, bindir, work, key_extra=(), keep=False):
    """src(.cia/.3ds) → dst. 형식은 dst 확장자로 정한다(.cia / .3ds). 실패해도 작업 폴더는 지운다."""
    try:
        return _patch(src, dst, payload, bindir, work, key_extra)
    finally:
        if not keep: shutil.rmtree(work, ignore_errors=True)


def _patch(src, dst, payload, bindir, work, key_extra):
    man = json.load(open(os.path.join(payload, 'manifest.json'), encoding='utf-8'))
    titles = json.load(open(os.path.join(payload, 'titles.json'), encoding='utf-8'))
    bdir = os.path.join(payload, 'banner')
    logos = {os.path.splitext(f)[0]: open(os.path.join(bdir, f), 'rb').read() for f in os.listdir(bdir)}
    romfs_dir = os.path.join(payload, 'romfs')
    out_kind = os.path.splitext(dst)[1].lower()
    if out_kind not in ('.cia', '.3ds'): raise SystemExit('결과 파일 확장자는 .cia 또는 .3ds 여야 합니다.')

    dirs = key_dirs(key_extra)
    boot9 = find_key('boot9.bin', dirs); seeddb = find_key('seeddb.bin', dirs)
    # pyctr 는 키 경로를 환경 변수에서 읽는다(3DS 리더는 crypto 인자를 받지 않음)
    if boot9: os.environ['BOOT9_PATH'] = boot9
    if seeddb: os.environ['SEEDDB_PATH'] = seeddb
    from pyctr.crypto import CryptoEngine, load_seeddb
    from pyctr.type.ncch import NCCHSection
    if seeddb: load_seeddb(seeddb)

    if os.path.exists(work): shutil.rmtree(work)
    os.makedirs(work)
    T = Tools(bindir, work)
    W = lambda n: os.path.join(work, n)

    # 1) 읽기·복호화 → 작업 폴더에 평문 NCCH(p0 본편, p1 설명서 …)
    kind = os.path.splitext(src)[1].lower()
    if kind not in ('.cia', '.3ds', '.cci'): raise SystemExit('.cia 또는 .3ds 파일만 넣을 수 있습니다.')
    try:
        if kind == '.cia' and not boot9:
            rd = None; raw, ver = raw_cia_contents(src)
            recs = [(i, off, size) for i, _c, off, size in raw]; cids = {i: c for i, c, _o, _s in raw}
        elif kind == '.cia':
            from pyctr.type.cia import CIAReader
            rd = CIAReader(src, crypto=None if boot9 else CryptoEngine(setup_b9_keys=False))
            recs = [(r.cindex, int(r.id, 16)) for r in rd.tmd.chunk_records]
            ver = str(rd.tmd.title_version)
            parts = {idx: rd.contents[idx] for idx, _ in recs}
        elif boot9:
            from pyctr.type.cci import CCIReader
            rd = CCIReader(src)
            parts = {int(k): v for k, v in rd.contents.items()}
            recs = [(i, i) for i in sorted(parts)]; ver = None
        else:
            rd = None; recs = raw_cci_partitions(src); ver = None; cids = {}
        if rd is not None:
            pid = str(parts[0].program_id).lower() if 0 in parts else None
            if pid != TID: raise SystemExit('일본판 신 광신화 파르테나의 거울(%s) 파일이 아닙니다: %s' % (TID, pid))
            for idx, _ in recs:
                log('복호화: %s %d' % ('콘텐츠' if kind == '.cia' else '파티션', idx))
                with parts[idx].open_raw_section(NCCHSection.FullDecrypted) as f, open(W('p%d.ncch' % idx), 'wb') as o:
                    shutil.copyfileobj(f, o, 1 << 24)
            rd.close()
        else:
            for idx, off, size in recs:
                log('복사: %s %d (이미 복호화된 파일)' % ('콘텐츠' if kind == '.cia' else '파티션', idx))
                with open(src, 'rb') as f, open(W('p%d.ncch' % idx), 'wb') as o:
                    f.seek(off); left = size
                    while left:
                        b = f.read(min(left, 1 << 24)); o.write(b); left -= len(b)
            recs = [(i, cids[i] if kind == '.cia' else i) for i, _, _ in recs]
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(key_error(e))

    with open(W('p0.ncch'), 'rb') as f:
        h = f.read(0x200)
    if h[0x100:0x104] != b'NCCH' or '%016x' % struct.unpack_from('<Q', h, 0x118)[0] != TID:
        raise SystemExit('일본판 신 광신화 파르테나의 거울(%s) 본편이 아닙니다.' % TID)

    # 2) 본편 펼치기·교체
    cx = ['--header', 'hdr.bin', '--exh', 'exh.bin', '--plain', 'plain.bin',
          '--exefs', 'exefs.bin', '--romfs', 'romfs.bin']
    log('본편 펼치는 중...')
    T.run('3dstool', ['-xvtf', 'cxi', 'p0.ncch'] + cx + ['--logo', 'logo.bin'], 'xcxi')
    os.remove(W('p0.ncch'))
    ex = open(W('exefs.bin'), 'rb').read()
    ban = exefs_file(ex, 'banner'); ico = exefs_file(ex, 'icon')
    patches = {'banner': patch_banner(ban, logos), 'icon': patch_smdh(ico, titles['short'], titles['long'])}
    open(W('exefs.bin'), 'wb').write(rebuild_exefs(ex, patches))
    log('HOME 메뉴 배너·게임 이름 교체')

    T.run('3dstool', ['-xvtf', 'romfs', 'romfs.bin', '--romfs-dir', 'rx'], 'xromfs')
    log('원본 확인 중...')
    for rel, want in man['source_md5'].items():
        p = W(os.path.join('rx', *rel.split('/')))
        if not os.path.exists(p) or md5_file(p) != want:
            raise SystemExit('원본 파일이 다릅니다: %s. 이미 패치한 파일이거나 다른 버전입니다.' % rel)
    n = 0
    for root, _, files in os.walk(romfs_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), romfs_dir)
            d = W(os.path.join('rx', rel))
            if not os.path.exists(d): raise SystemExit('원본에 없는 파일: ' + rel)
            shutil.copyfile(os.path.join(root, f), d); n += 1
    log('게임 내 한글 파일 %d개 교체' % n)
    T.run('3dstool', ['-cvtf', 'romfs', 'romfs.bin', '--romfs-dir', 'rx'], 'cromfs')
    shutil.rmtree(W('rx'))
    log('다시 묶는 중...')
    if os.path.exists(W('logo.bin')):     # 이 게임(초기 타이틀)은 로고 영역이 없어 추출 때 logo.bin 이 안 생긴다
        cx += ['--logo', 'logo.bin']
    T.run('3dstool', ['-cvtf', 'cxi', 'p0.ncch'] + cx + ['--not-encrypt'], 'ccxi')

    # 3) CIA / 3DS 로 묶기
    args = ['-f', 'cia' if out_kind == '.cia' else 'cci', '-o', 'out' + out_kind, '-ignoresign']
    for idx, cid in recs:
        args += ['-content', 'p%d.ncch:%d:%d' % (idx, idx, cid)]     # 3DS(CCI)도 세 칸 형식이어야 한다
    T.run('makerom', args, 'makerom')
    if out_kind == '.cia' and ver:
        fix_tmd_version(W('out.cia'), ver)
    if os.path.exists(dst): os.remove(dst)
    shutil.move(W('out' + out_kind), dst)
    return dst


def fix_tmd_version(cia, ver):
    want = [int(x) for x in str(ver).split('.')]
    want = want[0] << 10 | want[1] << 4 | want[2]
    al = lambda x: (x + 63) & ~63
    with open(cia, 'r+b') as f:
        hsize, _t, _v, clen, tlen, tmdlen, _m = struct.unpack('<IHHIIII', f.read(0x18))
        off = al(al(al(hsize) + clen) + tlen)
        f.seek(off); sig = struct.unpack('>I', f.read(4))[0]
        SIG = {0x10000: 0x23C, 0x10001: 0x13C, 0x10002: 0x7C, 0x10003: 0x23C, 0x10004: 0x13C, 0x10005: 0x7C}
        o = off + 4 + SIG[sig] + 0x9C
        f.seek(o); cur = struct.unpack('>H', f.read(2))[0]
        if cur != want: f.seek(o); f.write(struct.pack('>H', want))
