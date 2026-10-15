# 신 광신화 파르테나의 거울 (3DS) 한글 패치

*新・光神話 パルテナの鏡* (닌텐도 3DS, 일본판 `CTR-P-AKDJ` / `0004000000030000`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

**제작: arqhive** · **최신 버전: [v0.4.3](../../releases/tag/v0.4.3)**

- 게임 안의 문장 8,218종(같은 문장이 쓰인 곳까지 합치면 메시지 25,422개)을 모두 번역했습니다. 공중전·지상전 대사, 게임 방법 영상 자막, 메뉴, 도감, 팁, 보물 상자 과제, 스태프롤이 들어 있습니다.
- 메뉴 버튼, 보스 이름, 챕터 제목, 조작 설명 등 그림 글씨 265장과 타이틀 로고, HOME 메뉴 배너를 한글로 바꿨습니다.
- 스태프롤 전용 폰트에 한글 147자를 넣었습니다.
- **본문 글자는 본체 시스템 폰트로 그려지므로 한국판 3DS 본체에서만 한글이 나옵니다.** Azahar용 한글 시스템 폰트를 함께 배포합니다.
- 배포본은 romfs 파일 243개를 덮어씌우는 LayeredFS 패치, 일본판 CIA 또는 3DS 파일을 한글판으로 바꾸는 패처, Azahar 한글 폰트 세 가지입니다. LayeredFS와 패처는 둘 중 하나만 쓰면 됩니다.

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판 소프트(타이틀 ID `0004000000030000`). 북미판·유럽판(*Kid Icarus: Uprising*)에는 적용할 수 없습니다.
- 3DS 실기에서는 **한국판 본체**와 Luma3DS, 에뮬레이터에서는 Azahar와 한글 폰트.
- 방법마다 필요한 것은 아래 비교표를 참고하세요.

### 적용 방법

게임 내 한글은 두 방법이 같습니다. [배포 페이지](../../releases/latest)에서 **둘 중 하나만** 골라 받으면 됩니다.

| | 방법 A. LayeredFS | 방법 B. 패처로 한글판 CIA·3DS 만들기 |
|---|---|---|
| 받는 파일 | `AKDJ_KPatch_v0.4.3_LayeredFS.zip` | `AKDJ_KPatch_v0.4.3_CIA.zip` |
| 게임 내 한글 | 적용 | 적용 |
| HOME 메뉴 게임 이름·배너 | 일본어 그대로 | 한글 |
| 필요한 것 | 이미 설치된 일본판, Luma3DS 게임 패치 설정 | 일본판 파일 하나(3DS 실기 설치용이면 `.cia`, 에뮬레이터·플래시카트용이면 `.3ds`), 윈도우 PC, 암호화된 원본이면 `boot9.bin` |
| 되돌리기 | SD 카드의 폴더만 지우면 원래대로 | 원본 CIA를 다시 설치 |
| 에뮬레이터 | Azahar 모드 폴더에 복사 | 만든 3DS·CIA를 바로 실행 |

Azahar로 실행한다면 두 방법 모두 `AKDJ_KPatch_v0.4.3_AzaharFont.zip`을 함께 받아 설치해야 합니다.

#### 방법 A. LayeredFS

1. 3DS 실기: ZIP 안의 `luma` 폴더를 SD 카드 루트에 복사합니다. 파일은 `sd:/luma/titles/0004000000030000/romfs/jp/...`에 놓입니다.
   Luma3DS 설정(본체를 켤 때 SELECT)에서 **Enable game patching**을 켜고 게임을 실행합니다.
2. Azahar: 게임을 오른쪽 클릭해 **Open → Mods Location**을 열고, ZIP 안의 `luma/titles/0004000000030000/romfs` 폴더를 그곳에 복사합니다.

#### 방법 B. 패처로 한글판 CIA·3DS 만들기

1. 쓰려는 곳에 맞는 일본판 파일 하나를 준비합니다. 3DS 실기에 설치하려면 `.cia`, 에뮬레이터나 플래시카트에서 쓰려면 `.3ds`입니다.
2. ZIP을 폴더째 풀고, 준비한 파일을 `패치하기.bat`에 끌어다 놓습니다.
3. 원본과 같은 폴더에 `원래 이름_KO.cia` 또는 `원래 이름_KO.3ds`가 생깁니다. 원본 파일은 바뀌지 않습니다.
4. 3DS 실기에는 만든 CIA를 설치합니다. 이미 설치된 일본판에 덮어 설치해도 세이브는 유지됩니다.

패처는 원본을 풀어 게임 내 한글 파일 243개와 HOME 메뉴 배너·게임 이름을 바꾼 뒤 다시 묶습니다. 넣은 파일이 일본판 본편인지, 바꿀 파일이 원본 그대로인지 먼저 확인합니다. 파이썬이 함께 들어 있어 따로 설치할 것은 없습니다.

#### Azahar 한글 폰트

`AKDJ_KPatch_v0.4.3_AzaharFont.zip` 안의 `nand` 폴더를 Azahar 사용자 폴더(**File → Open Azahar Folder**, 보통 `%APPDATA%\Azahar`)에 복사합니다.
Azahar 내장 대체 폰트에 한글 2,350자를 더한 것이라 Azahar로 실행하는 모든 게임에 적용됩니다. 원래대로 돌리려면 `nand/.../title/0004009b/00014002` 폴더를 지우면 됩니다.

자세한 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

### 실행 환경

- **확인함**: 한국판 3DS + 패처로 만든 CIA 설치, 한국판 3DS + Luma3DS(LayeredFS), Azahar(한글 폰트 설치).

### 알려진 문제

- 일본판·북미판·유럽판 3DS 본체에서는 한글이 나오지 않습니다. 이 게임은 본문을 본체 시스템 폰트로 그리는데, 한글이 든 시스템 폰트는 한국판 본체에만 있습니다.
- 게임 방법·광고 영상 속 화면 글자는 일본어 그대로입니다(영상을 다시 만들 수 있는 인코더가 없습니다). 영상 위에 뜨는 자막은 한글입니다.
- 음성은 일본어 그대로입니다.
- 가짜 파르테나의 이마에 쓰인 「オレ」(3D 모델 그림)는 일본어 그대로입니다.
- LayeredFS로는 HOME 메뉴의 제목과 배너가 바뀌지 않습니다. 패처로 만든 CIA를 설치하면 바뀝니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.10 이상과 [`requirements.txt`](requirements.txt)의 패키지(pyctr, Pillow, NumPy, etcpak).
- 일본판 CIA와 복호화용 `boot9.bin`. Azahar를 쓰면 `%APPDATA%\Azahar\sysdata\`에 있는 파일을 자동으로 씁니다. 영어판 CIA는 번역 참고용이라 없어도 됩니다.
- 외부 도구 `3dstool`, `makerom` → `tools/bin/`.
- 폰트: [Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR) 가변 폰트 → `tools/fonts/NotoSansKR-VF.ttf`(Azahar 폰트), [Song Myung](https://fonts.google.com/specimen/Song+Myung) → `tools/fonts/SongMyung-Regular.ttf`(스태프롤 폰트).
- Azahar 폰트를 만들 때 `azahar.exe`(내장 대체 폰트를 꺼냄). 기본 경로는 `~/az/azahar.exe`, 다르면 환경 변수 `AZAHAR_EXE`로 지정합니다.
- 그림 글씨(`images/GPT/…`)는 게임 그래픽을 고친 것이라 저장소에 넣지 않았습니다. 목록은 [`translation/graphics.csv`](translation/graphics.csv)에 있습니다.

### 빌드

```bash
python tools/prepare.py "일본판.cia" ["북미판.cia"]   # 추출 → darc 풀기 → 원문·화자 추출 → 번역 단위(translation/units.json)
python tools/build_sysfont.py                         # Azahar 한글 폰트 빌드·설치(--cfa-only: 배포 파일만)
python tools/build_all.py [--mod]                     # 텍스트·그림 글씨·타이틀 로고·스태프롤 폰트 → release/luma (--mod: Azahar 모드 폴더에도)
python tools/verify_build.py                          # 빌드 결과의 메시지 25,833개 전수 대조
python tools/build_cia.py [--cia 일본판.cia] [--out 한글판.cia]   # 전부 들어간 CIA (.3ds 도 가능)
python tools/make_patcher.py v0.4.3 --python <임베디드 파이썬 zip 또는 폴더>   # release/patcher·python 채우기
python tools/make_release.py v0.4.3                     # 배포 ZIP 세 개
```

CIA·3DS 처리는 `tools/kiupatch.py` 한 곳에 있고, `build_cia.py`와 배포 패처(`release/patcher/patch.py`)가 함께 씁니다(에버 오아시스 한글 패치의 방식).
pyctr로 콘텐츠를 복호화한 뒤 ExeFS의 배너·아이콘과 romfs 파일을 바꾸고, 3dstool로 CXI를 다시 싸서 makerom으로 CIA나 3DS를 묶습니다.

### 번역 수정

- 번역 원본은 [`translation/batches/`](translation/batches)의 묶음 JSON입니다. 키는 원문 단위(첫 메시지 ID), 값은 태그를 포함한 번역문입니다. `zz_`로 시작하는 파일은 검수 반영분이라 마지막에 적용됩니다.
- `python tools/tl.py check <묶음>`이 태그·줄 수·줄 폭·폰트에 없는 글자를 검사하고, `python tools/tl.py apply`가 모든 묶음을 [`translation/ko.json`](translation/ko.json)으로 합칩니다.
- `python tools/punct.py`가 마침표·쉼표 누락 후보를 뽑습니다.
- 용어는 [`translation/GLOSSARY.md`](translation/GLOSSARY.md)와 [`translation/names_ja_ko.json`](translation/names_ja_ko.json), 문체 규칙은 [`docs/STYLE_GUIDE.md`](docs/STYLE_GUIDE.md), 번역 중 판단 기록은 [`translation/NOTES.md`](translation/NOTES.md)에 있습니다.

### 폴더 구조

```
release/       사용자 설명서, 패처(패치하기.bat, patcher/patch.py). 빌드하면 luma/, python/, 배포 ZIP 이 생김
translation/   번역 묶음(batches/), 합친 번역(ko.json), 그림 글씨 목록, 용어집·이름 사전·번역 메모
tools/         추출(CIA·darc·MSBT·PSLB·CGFX), 번역 검사, 폰트·그림 글씨·타이틀 로고 빌드, CIA·배포 도구
docs/          기술 문서, 문체 규칙, 릴리즈 노트 사본(docs/releases/)
```

### 기술 문서

darc·MSBT·화자 판정·CGFX 텍스처·시스템 폰트·타이틀 로고 구조와 패치 방식은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).
- Azahar 한글 폰트의 한글 글리프는 [Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR)(SIL Open Font License 1.1)로, 스태프롤 한글은 [Song Myung](https://fonts.google.com/specimen/Song+Myung)(SIL Open Font License 1.1)으로 그렸습니다.
- 그림 글씨는 원본 디자인을 따라 새로 그렸습니다.

## 면책

비공식 팬 번역이며 Nintendo, Sora Ltd.와 관련이 없습니다. 「신 광신화 파르테나의 거울」 관련 상표·저작권은 Nintendo에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
