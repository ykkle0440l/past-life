# 전생 거울 (pstlf.co.kr)

재미로 보는 전생·인연·타로 사이트.

- `/` 첫 화면 (테스트 목록, 읽을거리)
- `/past-life/` 전생 체험
- `/bond/` 전생의 인연 궁합
- `/tarot/` 오늘의 타로 한 장
- `/tarot/2027/` 2027년 신년 타로 (카드 세 장: 상반기, 하반기, 올해의 열쇠)
- `/tarot/cards/` 메이저 아르카나 22장 의미
- `/read/` 읽을거리
- `/about/` 소개, 문의
- `/assets/` 공통 스타일(site.css)과 기능(site.js: 공유 창, 생년월일 입력)

## 페이지 다시 만들기

사이트를 고친 뒤에는 항상 아래 두 줄을 실행하고, 마지막 줄이 `문제 0건`일 때만 올려요.

```
python3 _build/build.py
python3 _build/qa.py
```

`qa.py` 는 모든 페이지를 휴대폰(320px, 390px)과 PC 크기로 열어 오류, 깨진 링크, 화면 넘침을 보고,
세 테스트의 입력·결과·공유 링크·공유 창, 타로 하루 한 장과 카드별 누를 수 있는 폭까지 확인해요.
(Python Playwright, Chromium 필요)

`build.py` 를 실행하면
테스트 아래 설명글, 카드 의미, 읽을거리, 소개, 개인정보처리방침, 404, sitemap 이 다시 만들어져요.
신년 타로의 카드별 2027년 풀이는 `_build/content_newyear.py` 에 있고, build.py 가 신년 타로 페이지와 카드 의미 페이지에 채워 넣어요.
(Node.js 필요. `_build` 폴더는 사이트에 올라가지 않아요.)

## 신년 타로 공유 이미지

`share-2027.png` 는 `python3 _build/make_share_newyear.py` 로 만들었어요. 문구를 바꿀 때만 다시 실행하면 돼요.

## 설정

- 카카오톡 공유: `assets/site.js` 의 `kakaoKey` 에 카카오 JavaScript 키를 넣어요.
- 광고: 쿠팡 배너는 각 테스트의 `쿠팡 파트너스 배너 코드` 주석 사이, 애드센스는 `<head>` 안에 있어요.
