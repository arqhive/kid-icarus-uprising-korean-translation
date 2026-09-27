# images/jp 후보 중 글자 있는 것만 images/게임내 로 분류, 목록 CSV 작성
import csv, os, re, shutil
rows = list(csv.reader(open('images/목록.csv', encoding='utf-8-sig')))
head, rows = rows[0], rows[1:]
EXCL_NAME = re.compile(r'^(FB_|FB_D\.)')
EXCL_FILE = {
    'info_a060_CI_000.png', 'info_a060_CI_001.png', 'info_a220_CI_002.png', 'info_a220_CI_003.png',
    'info_a260_SP_001.png', 'info_a260_SP_002.png', 'info_a260_SP_004.png', 'info_a260_SP_005.png',
    'info_a280_SP_000.png',                                   # 영어 캐스트 목록
    'menu_040_MenTopBtBg0100.png', 'menu_020_MenSelfileBt0002.png', 'menu_460_MenColViewerBt0008.png',
    'menu_120_MenEquipBtDynamic_04010.png',                   # 'ALL' 영어
    'doll_052_Palum_modoki.png', 'stage_b3001_b301_Bos_Modoki.png',
}
KEEP_STAGE = {'stage_g0501_g05m01_syounin01.png'}
def kind(fn, name):
    if fn.startswith('info_'):
        if '_CP_' in fn: return '챕터 제목 카드'
        if '_BL_' in fn or '_BR_' in fn: return '보스 이름 배너'
        if 'a700_SP' in fn: return '조작 설명(튜토리얼)'
        if '_SP_' in fn: return '연출 글자(격파·승리·정화·스태프롤)'
        if 'multi' in fn: return '대전 UI'
        if 'single' in fn: return '싱글 전투 UI'
        if 'common' in fn: return '전투 공용 UI'
        return '기타 info'
    if fn.startswith('menu_'): return '메뉴'
    if fn.startswith('resident'): return '공용 아이콘'
    return '스테이지'
out = []
dst = 'images/게임내'
if os.path.exists(dst): shutil.rmtree(dst)
for r in rows:
    fn, name = r[0], r[1]
    if EXCL_NAME.match(name) or fn in EXCL_FILE: continue
    if fn.startswith(('demo_', 'stage_')) and fn not in KEEP_STAGE: continue
    if fn.startswith('info_') and r[7] != 'Y' and '_SP_' not in fn: continue
    k = kind(fn, name)
    os.makedirs(os.path.join(dst, k), exist_ok=True)
    shutil.copy('images/jp/' + fn, os.path.join(dst, k, fn))
    us = 'images/us_ref/' + fn
    out.append([k, fn] + r[1:] + ['Y' if os.path.exists(us) else ''])
with open('images/게임내_글자이미지_목록.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['분류'] + head + ['북미판참고PNG'])
    w.writerows(sorted(out))
import collections
print(len(out), collections.Counter(o[0] for o in out))
print('사용처 합계', sum(int(o[6]) for o in out))
