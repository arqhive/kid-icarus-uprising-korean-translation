# -*- coding: utf-8 -*-
"""마침표·쉼표 누락 검사 (번역문 translation/ko.json 대상, 원문과 대조).

  python tools/punct.py            → work/punct_report.json + 요약 출력

A. 마침표: 번역문 끝(또는 줄 끝)이 종결어미로 끝나는데 부호가 없음
B. 문장 수: 원문 종결 부호(。！？!? 와 ⋯ 끝) 개수보다 번역문 종결 부호가 적음
C. 쉼표: 원문이 부르는 말·감탄사 뒤에 「、」를 찍었는데 번역문 첫머리에 쉼표가 없음
이름·메뉴 같은 명사구(원문이 종결 부호 없이 끝나고 번역이 명사로 끝남)는 대상이 아니다.
"""
import sys, os, re, json, collections
sys.path.insert(0, os.path.dirname(__file__))
import tl

TAG = re.compile(r'\{[^}]*\}')
# 문장을 끝맺는 한국어 어미의 마지막 글자(명사와 겹치기 쉬운 글자는 뺌)
END = set('다요까죠네지야어아군나라자게걸래니데오세해봐돼줘마냐여소께쇼든담대구며렴')
NOUNY = re.compile(r'(필요|중요|이유|자유|요요|가게|나라|사자|의자|여자|남자|모자|과자|피자|바다|기지|이야|무지|영지|위치|편지|장치|도시|거지|바지|부자|하나|노다|판다|아바|그대|이마|우대|세대|시대|연대|부대|무대|상대|기대|반대|최대|절대|확대|강대|거대|방대|대|마녀|나무|구나)$')
VOC = ['피트', '파르테나 님', '파르테나', '나츄레', '하데스', '블랙피트', '브라피', '메두사', '마그나', '딘토스', '판도라',
       '타나토스', '포세이돈', '아론', '엘레카', '라즈', '로카', '가이나스', '피트 군', '파르테나 양', '나츄레 양',
       '대장님', '여러분', '이봐', '저기', '자', '아', '앗', '어', '오', '음', '흠', '네', '예', '응', '그래', '좋아', '이런',
       '뭐', '헤', '후후', '하하', '어라', '어이', '야', '에이', '와', '우와', '으음', '흐음', '에', '엇', '헉', '아하', '글쎄']
JP_END = re.compile(r'(。|！|？|!|\?|⋯⋯|⋯|…)+')
KO_END = re.compile(r'(\.(?!\.)|!|\?|！|？|……|…)+')


def plain(s):
    return TAG.sub('', s)


def last_word(line):
    w = re.split(r'\s+', line.strip())
    return w[-1] if w else ''


def ends_sentence(word):
    w = re.sub(r'["”’』」)\]]+$', '', word)
    if not w or not ('가' <= w[-1] <= '힣'):
        return False
    if NOUNY.search(w):
        return False
    return w[-1] in END


def main():
    units = tl.load_units()
    ko = json.load(open(os.path.join(tl.T, 'ko.json'), encoding='utf-8'))
    skip_cat = {'스태프롤'}
    out = collections.defaultdict(list)
    for u in units:
        k = u['key']
        if u['cat'] in skip_cat or k not in ko:
            continue
        jp, t = plain(u['jp']), plain(ko[k])
        lines = t.split('\n')
        # A. 줄 끝 종결어미 + 부호 없음
        jlast = jp.rstrip()
        jp_sentence = bool(jlast) and (jlast[-1] in '。' or 'ぁ' <= jlast[-1] <= 'ゖ')
        for i, line in enumerate(lines):
            s = line.rstrip()
            if not s or re.search(r'[.!?…,~」』)"”’\-:：！？]$', s):
                continue
            last = (i == len(lines) - 1)
            strong = re.search(r'(다|요|까|죠)$', re.sub(r'["”’』」)\]]+$', '', s)) and not re.search(r'(니까|으니까|테니까|다가|려다|라도)$', s)
            if (last and jp_sentence and ends_sentence(last_word(s))) or (not last and strong and ends_sentence(last_word(s))):
                # 마지막 줄이거나, 다음 줄이 새 문장으로 보이면 누락
                out['A'].append(dict(key=k, line=i + 1, text=s, jp=u['jp'], ko=ko[k], cat=u['cat']))
        # B. 문장 수
        nj = len(JP_END.findall(jp.rstrip()))
        nk = len(KO_END.findall(t.rstrip()))
        if nj and nk < nj and not any(x['key'] == k for x in out['A']):
            out['B'].append(dict(key=k, jp_n=nj, ko_n=nk, jp=u['jp'], ko=ko[k], cat=u['cat']))
        # C. 부르는 말·감탄사 뒤 쉼표
        for jl, kl in zip(jp.split('\n'), t.split('\n')):
            m = re.match(r'^([^、。！？!?\s]{1,8})、', jl)
            if not m:
                continue
            for v in sorted(VOC, key=len, reverse=True):
                if not kl.startswith(v):
                    continue
                nxt = kl[len(v):len(v) + 1]
                if nxt == ' ' or nxt == '':
                    out['C'].append(dict(key=k, text=kl, jp=u['jp'], ko=ko[k], cat=u['cat']))
                if nxt in (' ', '', ',', '!', '?', '…', '.'):
                    break   # 가장 긴 호칭에서 판정 끝(이미 쉼표가 있으면 통과)
    json.dump(out, open(os.path.join(tl.ROOT, 'work', 'punct_report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    for g, name in (('A', '줄 끝 마침표 누락 의심'), ('B', '문장 수 대비 종결 부호 부족'), ('C', '부르는 말 뒤 쉼표 누락 의심')):
        print('%s %s: %d' % (g, name, len(out[g])))
        c = collections.Counter(x['cat'] for x in out[g])
        print('   ', dict(c))


if __name__ == '__main__':
    main()
