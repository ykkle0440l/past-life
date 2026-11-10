#!/usr/bin/env python3
"""전생 거울 정적 페이지 만들기

python3 _build/build.py 로 실행하면
- 세 테스트 페이지 아래 설명글(guide)을 채우고
- 상단 메뉴와 아래 링크를 모든 페이지에 맞추고
- 타로 카드 의미 22장, 읽을거리, 소개, 개인정보처리방침, 404, sitemap 을 만들어요.
- 2027 신년 타로(tarot/2027/)에 카드 그림과 2027년 풀이(content_newyear.py)를 채워요.
- 숏폼 영상 속 상품 모음(shop/)을 만들어요. 상품 목록은 shop/items.txt 에서 고쳐요.
결과 데이터(전생, 인연, 카드)는 각 테스트 페이지의 스크립트에서 그대로 읽어 와요.
(_build 폴더는 밑줄로 시작해서 GitHub Pages 에는 올라가지 않아요.)
"""
import datetime
import hashlib
import html
import json
import pathlib
import re
import subprocess

from content_read import ARTICLES
from content_tarot import CARD_EXTRA
from content_newyear import NEWYEAR, YEAR, YEAR_NAME, YEAR_ANIMAL

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = 'https://pstlf.co.kr'
TODAY = datetime.date.today().isoformat()
ADS = ('<!-- 구글 애드센스 -->\n'
       '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8262915217195031"\n'
       '     crossorigin="anonymous"></script>')

NAV = [('/', '테스트'), ('/tarot/cards/', '카드 의미'), ('/read/', '읽을거리')]
FOOT_LINKS = ('<p class="foot-links"><a href="/about/">소개</a><a href="/about/#contact">문의</a>'
              '<a href="/privacy.html">개인정보처리방침</a></p>')


def esc(s):
    return html.escape(s, quote=True)


def has_batchim(word):
    c = ord(word[-1])
    return 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 != 0


def ieyo(word):
    """'희망이에요', '풍요예요'처럼 받침에 맞는 끝말"""
    return '이에요' if has_batchim(word) else '예요'


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


# ── 테스트 페이지 스크립트에서 데이터 읽기 ─────────────────────────
def extract_array(src, name):
    key = f'var {name} = '
    start = src.index(key) + len(key)
    depth, quote, escaped = 0, None, False
    for i in range(start, len(src)):
        ch = src[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in '\'"':
            quote = ch
        elif ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise ValueError(name)


def node_json(prelude, expr):
    code = prelude + '\nprocess.stdout.write(JSON.stringify(' + expr + '));'
    out = subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def load_data():
    pl = read('past-life/index.html')
    lives = node_json('const LIVES = ' + extract_array(pl, 'LIVES') + ';', 'LIVES')
    animals = node_json('const ANIMALS = ' + extract_array(pl, 'ANIMALS') + ';', 'ANIMALS')
    bd = read('bond/index.html')
    types = node_json('const TYPES = ' + extract_array(bd, 'TYPES') + ';', 'TYPES')
    tr = read('tarot/index.html')
    rays = re.search(r'function rays\(.*?\n  \}\n', tr, re.S).group(0)
    cards = node_json(rays + 'const CARDS = ' + extract_array(tr, 'CARDS') + ';',
                      "CARDS.map(c => Object.assign({}, c, {art: c.art + (c.artExtra ? c.artExtra() : '')}))")
    assert len(cards) == len(CARD_EXTRA) == len(NEWYEAR) == 22
    for c, extra, ny in zip(cards, CARD_EXTRA, NEWYEAR):
        c.update(extra)
        c['ny'] = ny
    return lives, animals, types, cards


# ── 공통 조각 ─────────────────────────────────────────────
def header(current=None):
    links = ''.join(
        f'<a href="{h}"' + (' aria-current="page"' if h == current else '') + f'>{t}</a>'
        for h, t in NAV)
    return ('<header class="site-head">\n'
            '    <a class="wordmark" href="/">전생 거울</a>\n'
            f'    <nav class="site-nav" aria-label="사이트 메뉴">{links}</nav>\n'
            '  </header>')


def page(path, title, desc, main, og='/share.png', current=None, kind='article',
         note='모든 결과와 해석은 재미로 즐겨 주세요.', ads=True):
    url = SITE + path
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)} | 전생 거울</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#18203A">
<link rel="canonical" href="{url}">

<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="전생 거울">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="600">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Song+Myung&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
{ADS if ads else ''}
</head>
<body>
<div class="page">
  {header(current)}

  <main class="prose">
{main}
  </main>

  <footer class="site-foot">
    <p>{note}</p>
    {FOOT_LINKS}
  </footer>
</div>
</body>
</html>
'''


def card_face(c, small=False):
    cls = 'card-face sm' if small else 'card-face'
    return (f'<div class="{cls}" role="img" aria-label="{esc(c["ko"])} 카드 그림">'
            f'<span class="num">{c["num"]}</span>'
            f'<span class="art"><svg viewBox="0 0 100 100" aria-hidden="true">{c["art"]}</svg></span>'
            f'<span class="name">{esc(c["ko"])}</span><span class="en">{esc(c["en"])}</span></div>')


def read_list(items):
    return '<ul class="read-list">' + ''.join(
        f'<li><a href="/read/{a["slug"]}/">{esc(a["title"])}<small>{esc(a["summary"])}</small></a></li>'
        for a in items) + '</ul>'


def article(slug):
    return next(a for a in ARTICLES if a['slug'] == slug)


def faq(items):
    return ''.join(f'<details><summary>{esc(q)}</summary><div><p>{a}</p></div></details>' for q, a in items)


# ── 테스트 페이지 아래 설명글 ─────────────────────────────────
def guide_pastlife(lives, animals):
    n_roles = sum(len(l['roles']) for l in lives)
    eras = ''.join(
        f'<details><summary>{esc(l["era"])}, {esc(l["place"])}</summary><div><ul>'
        + ''.join(f'<li><strong>{esc(r["t"])}</strong><br>{esc(r["d"])}</li>' for r in l['roles'])
        + '</ul></div></details>'
        for l in lives)
    eras += ('<details><summary>드물게 나오는 동물 전생</summary><div><ul>'
             + ''.join(f'<li><strong>{esc(a["t"])}</strong> ({esc(a["era"])}, {esc(a["place"])})<br>{esc(a["d"])}</li>'
                       for a in animals)
             + '</ul></div></details>')
    return f'''    <section class="guide" aria-labelledby="guideTitle">
      <h2 id="guideTitle">전생 체험은 이렇게 봐요</h2>
      <p>전생 거울은 입력한 이름과 생년월일을 하나의 숫자로 바꾼 뒤, 그 숫자에 맞는 전생 이야기를 골라 보여 줘요. 그래서 같은 이름과 생년월일을 넣으면 언제 해도 같은 결과가 나와요. 결과에는 그 생을 살았던 시대와 장소, 그 생의 이야기와 마지막 순간, 그리고 이번 생까지 이어진 흔적과 인연이 담겨 있어요.</p>
      <p>거울에 비치는 전생은 사람의 삶 {n_roles}가지와 동물의 삶 {len(animals)}가지예요. 고려의 포구부터 1920년대 파리의 카페까지, 실제 역사 속 장소와 직업을 바탕으로 한 사람 한 사람의 이야기를 직접 썼어요. 동물 전생은 열 명 가운데 한 명꼴로 나오는 드문 결과예요.</p>

      <h2>거울에 비치는 전생들</h2>
      <p>시대를 누르면 그 시대에 나올 수 있는 전생을 미리 볼 수 있어요. 결과에는 여기에 더해 그 생의 성격과 마지막 순간, 이번 생에 남은 흔적이 함께 나와요.</p>
      {eras}

      <h2>자주 묻는 질문</h2>
      {faq([
          ('같은 이름이면 결과가 모두 같나요?', '이름과 생년월일을 함께 보기 때문에, 이름이 같아도 생년월일이 다르면 다른 전생이 나와요. 반대로 같은 이름과 생년월일을 넣으면 언제나 같은 결과가 나와요.'),
          ('생년월일은 어떻게 입력하나요?', '1998년 4월 17일생이라면 19980417처럼 숫자 8자리로 입력하면 돼요. 980417처럼 6자리로 입력해도 알아서 읽어요.'),
          ('입력한 이름과 생년월일은 저장되나요?', '아니요. 계산은 지금 쓰고 있는 휴대폰이나 컴퓨터 안에서만 이루어지고, 서버로 보내거나 저장하지 않아요. 결과를 공유하면 링크에 이름과 결과 번호만 담기고, 생년월일은 담기지 않아요.'),
          ('결과는 믿어도 되나요?', '전생 체험은 재미로 즐기는 놀이예요. 결과에 나온 이야기는 지난 삶을 증명하는 것이 아니라, 다른 시대의 나를 상상해 보는 작은 이야기로 봐 주세요.'),
      ])}

      <h2>더 읽어 보기</h2>
      {read_list([article('mirror-of-karma'), article('past-life-jobs'), article('reincarnation')])}
    </section>'''


def guide_bond(types):
    def anon(s):
        return s.replace('{X}님', '한 사람').replace('{Y}님', '다른 한 사람')
    items = ''.join(
        f'<details><summary>{esc(t["t"])}</summary><div>'
        f'<p>{esc(t["era"])}, {esc(t["place"])}. 인연의 깊이 {t["min"]}~{t["max"]}%, 한 단어로는 ‘{esc(t["word"])}’.</p>'
        f'<p>{esc(anon(t["story"]))}</p></div></details>'
        for t in types)
    return f'''    <section class="guide" aria-labelledby="guideTitle">
      <h2 id="guideTitle">전생의 인연 궁합은 이렇게 봐요</h2>
      <p>두 사람의 이름을 거울에 비추면, 두 사람이 전생에 어떤 사이였는지와 인연의 깊이를 보여 드려요. 결과에는 그 생의 이야기, 이번 생에 다시 만난 이유, 잘 맞는 점과 조심할 점, 그리고 두 사람에게 건네는 한마디가 담겨 있어요.</p>
      <p>이름 순서를 바꿔 넣어도 결과는 같아요. 생년월일은 넣지 않아도 되지만, 같은 이름이 많을 때 넣으면 두 사람만의 결과를 볼 수 있어요. 연인뿐 아니라 친구, 가족, 동료와의 인연도 볼 수 있어요.</p>

      <h2>붉은 실 이야기</h2>
      <p>옛이야기 속 월하노인은 인연이 닿을 두 사람의 발목을 보이지 않는 붉은 실로 묶어 둔다고 해요. 이 실은 멀리 떨어져 있어도, 생이 바뀌어도 끊어지지 않는다고 전해져요. 결과 화면에서 두 이름 사이를 잇는 붉은 실도 이 이야기에서 가져왔어요. <a href="/read/red-thread/">월하노인 이야기 더 읽기</a></p>

      <h2>나올 수 있는 인연 {len(types)}가지</h2>
      <p>화랑 동무부터 앙숙 가게 주인까지, 두 사람의 전생 인연은 이 가운데 하나로 나와요.</p>
      {items}

      <h2>자주 묻는 질문</h2>
      {faq([
          ('이름 순서를 바꾸면 결과가 달라지나요?', '아니요. 누구 이름을 먼저 쓰든 같은 결과가 나와요. 다만 스승과 제자처럼 역할이 있는 인연에서는 누가 어떤 역할이었는지도 함께 알려 드려요.'),
          ('인연의 깊이가 낮으면 안 맞는 사이인가요?', '그렇지 않아요. 맞수나 앙숙처럼 서로 부딪히는 인연은 숫자가 조금 낮게 나오지만, 그만큼 서로를 자극하고 키워 주는 사이라는 뜻이기도 해요.'),
          ('생년월일은 어떻게 입력하나요?', '19980417처럼 숫자 8자리로 입력하면 돼요. 몰라도 괜찮아요. 이름만으로도 결과를 볼 수 있어요.'),
          ('입력한 정보는 저장되나요?', '아니요. 계산은 지금 쓰고 있는 기기 안에서만 이루어지고, 서버로 보내거나 저장하지 않아요. 공유 링크에는 두 사람의 이름과 결과 번호만 담겨요.'),
      ])}

      <h2>더 읽어 보기</h2>
      {read_list([article('red-thread'), article('reincarnation')])}
    </section>'''


def guide_tarot(cards):
    grid = ''.join(
        f'<a href="/tarot/cards/{c["slug"]}/">{card_face(c, small=True)}<small>{esc(c["kw"])}</small></a>'
        for c in cards)
    return f'''    <section class="guide" aria-labelledby="guideTitle">
      <h2 id="guideTitle">오늘의 타로는 이렇게 봐요</h2>
      <p>타로 78장 가운데 삶의 큰 흐름을 보여 주는 메이저 아르카나 22장으로 하루의 기운을 읽어요. 22장 가운데 7장을 섞어 펼쳐 두면, 그중 마음이 가는 카드 한 장을 고르면 돼요. 카드를 뒤집으면 키워드와 행운의 색, 행운의 시간, 그리고 오늘의 흐름과 사랑, 일과 돈에 관한 이야기가 나와요.</p>
      <p>카드는 하루에 한 장만 뽑을 수 있고, 자정이 지나면 새 카드를 뽑을 수 있어요. 뽑기 전에 숨을 한 번 고르고, ‘오늘 하루는 어떨까’처럼 짧은 질문을 마음속으로 떠올려 보세요. 같은 카드라도 어떤 질문을 품었는지에 따라 다르게 읽혀요.</p>
      <p>하루가 아니라 한 해의 흐름이 궁금하다면 카드 세 장으로 상반기, 하반기, 올해의 열쇠를 보는 <a href="/tarot/{YEAR}/">{YEAR}년 신년 타로</a>도 뽑아 보세요.</p>

      <h2>메이저 아르카나 22장</h2>
      <p>카드를 누르면 그림 속 이야기와 자세한 뜻, 거꾸로 나왔을 때의 의미까지 볼 수 있어요.</p>
      <div class="card-grid">{grid}</div>

      <h2>자주 묻는 질문</h2>
      {faq([
          ('하루에 한 장만 뽑을 수 있나요?', '네. 하루 한 장의 의미를 지키려고, 뽑은 카드는 지금 쓰는 기기에 그날 하루만 저장해 두었다가 자정이 지나면 새로 뽑을 수 있게 했어요. 저장된 카드는 서버로 보내지 않아요.'),
          ('거꾸로 나온 카드는 없나요?', '오늘의 타로는 카드를 정방향으로만 읽어요. 카드별로 거꾸로 나왔을 때의 뜻이 궁금하다면 위의 카드를 눌러 확인해 보세요.'),
          ('무서운 이름의 카드가 나왔어요.', '죽음이나 탑, 악마처럼 이름이 무서운 카드도 실제로는 끝과 새로운 시작, 깨달음, 나를 묶고 있던 습관 같은 뜻을 담고 있어요. 카드는 겁을 주려는 게 아니라 하루를 돌아볼 질문을 건네는 도구예요.'),
      ])}

      <h2>더 읽어 보기</h2>
      {read_list([article('tarot-basics')])}
    </section>'''


def guide_newyear(cards):
    grid = ''.join(
        f'<a href="/tarot/cards/{c["slug"]}/#y{YEAR}">{card_face(c, small=True)}<small>{esc(c["ny"]["word"])}</small></a>'
        for c in cards)
    questions = faq([
        ('언제 뽑는 게 좋나요?',
         '새해를 앞두고 미리 봐도 좋고, 1월 1일이나 설날처럼 마음을 새로 다잡는 날에 봐도 좋아요. 날짜보다 중요한 건 마음이에요. 조용한 곳에서 한 해를 떠올릴 수 있을 때 뽑아 보세요.'),
        ('다시 뽑을 수 있나요?',
         '뽑은 세 장은 지금 쓰는 기기에 저장돼서, 다시 들어와도 같은 카드가 보여요. 가족이나 친구와 한 휴대폰으로 함께 본다면 결과 아래의 ‘다른 사람도 뽑아 보기’를 눌러 새로 뽑을 수 있어요. 지금 결과를 남겨 두고 싶다면 먼저 공유하기로 링크를 저장해 두세요.'),
        ('행운의 달은 어떻게 정해지나요?',
         '뽑은 세 장의 조합에 따라 정해져요. 같은 세 장을 같은 순서로 뽑으면 언제나 같은 달이 나와요.'),
        ('양띠 해는 언제부터인가요?',
         f'보통은 음력 설날인 {YEAR}년 2월 7일부터 양띠 해로 봐요. 사주에서는 입춘인 {YEAR}년 2월 4일을 기준으로 해요.'),
        ('입력한 정보가 저장되나요?',
         '신년 타로는 이름이나 생년월일을 받지 않아요. 뽑은 카드 번호만 지금 쓰는 기기에 저장되고, 서버로 보내지 않아요.'),
    ])
    return f"""    <section class="guide" aria-labelledby="guideTitle">
      <h2 id="guideTitle">{YEAR}년 신년 타로는 이렇게 봐요</h2>
      <p>타로 78장 가운데 삶의 큰 흐름을 보여 주는 메이저 아르카나 22장으로 한 해를 읽어요. 22장 가운데 7장을 섞어 펼쳐 두면, 마음이 가는 카드를 세 장 차례로 고르면 돼요. 첫 번째 카드는 상반기, 두 번째 카드는 하반기, 세 번째 카드는 한 해 전체를 여는 열쇠 자리에 놓여요.</p>
      <p>세 장을 모두 고르면 카드가 차례로 뒤집히고, 한 해를 한 줄로 담은 문장과 올해의 키워드, 행운의 색과 행운의 달, 그리고 자리마다의 풀이가 나와요. 뽑기 전에 숨을 한 번 고르고 ‘새해에는 어떤 일이 생길까’, ‘올해 꼭 이루고 싶은 것’처럼 새해에 품은 질문을 하나 떠올려 보세요.</p>

      <h2>세 자리는 이렇게 읽어요</h2>
      <ul>
        <li><strong>상반기 (1~6월)</strong><br>새해를 여는 여섯 달의 분위기예요. 무엇을 시작하고 어디에 힘을 쓰면 좋은지 알려 줘요.</li>
        <li><strong>하반기 (7~12월)</strong><br>상반기에 뿌린 것이 한 해의 후반에 어떻게 이어지는지 보여 줘요. 결과 맨 위의 한 줄은 상반기 카드에서 하반기 카드로 흘러가는 한 해를 담았어요.</li>
        <li><strong>올해의 열쇠</strong><br>한 해 내내 품고 다닐 태도나 조언이에요. 행운의 색도 이 카드에서 나와요. 일이 잘 안 풀릴 때 이 자리의 풀이를 다시 꺼내 읽어 보세요.</li>
      </ul>

      <h2>{YEAR}년은 {YEAR_NAME}, {YEAR_ANIMAL}의 해</h2>
      <p>{YEAR}년은 육십갑자로 {YEAR_NAME}(丁未年)이에요. 앞 글자 정(丁)은 오행에서 불에 속해 붉은색과 이어지고, 흔히 촛불이나 등불처럼 은은하게 오래 타는 불에 빗대요. 뒤 글자 미(未)는 열두 띠 가운데 양을 뜻해요. 그래서 {YEAR}년을 ‘{YEAR_ANIMAL}의 해’라고 불러요.</p>
      <p>양은 무리를 지어 함께 지내는 온순한 동물이라, 예부터 화합과 평화, 따뜻한 마음을 떠올리게 하는 동물로 여겨져 왔어요. 크게 타오르기보다 곁을 오래 밝혀 주는 등불처럼, 서두르지 않고 주변과 함께 나아가는 한 해를 그려 보면 어떨까요.</p>
      <p>띠가 바뀌는 날은 보통 음력 설날을 기준으로 봐요. 한국천문연구원 자료를 보면 {YEAR}년 설날은 양력 2월 7일이에요. 사주에서는 절기상 봄이 시작되는 입춘을 기준으로 보는데, {YEAR}년 입춘은 2월 4일이에요.</p>

      <h2>카드별 {YEAR}년 한 단어</h2>
      <p>카드마다 {YEAR}년에 담긴 한 단어예요. 카드를 누르면 상반기, 하반기, 올해의 열쇠 자리에 나왔을 때의 풀이를 볼 수 있어요.</p>
      <div class="card-grid">{grid}</div>

      <h2>자주 묻는 질문</h2>
      {questions}

      <h2>더 읽어 보기</h2>
      {read_list([article('tarot-basics')])}
    </section>"""


def newyear_data(cards):
    """신년 타로 페이지가 쓰는 카드 그림과 2027년 풀이"""
    data = [dict(num=c['num'], ko=c['ko'], en=c['en'], slug=c['slug'], color=c['color'], art=c['art']) for c in cards]
    text = [dict(word=c['ny']['word'], h1=c['ny']['h1'], h2=c['ny']['h2'], key=c['ny']['key']) for c in cards]
    dump = lambda v: json.dumps(v, ensure_ascii=False).replace('</', '<\\/')
    return f'window.NY_CARDS = {dump(data)};\nwindow.NY_TEXT = {dump(text)};'


def inject_data(rel, js):
    s = read(rel)
    a = s.index('/* data:start */') + len('/* data:start */')
    b = s.index('/* data:end */')
    write(rel, s[:a] + '\n' + js + '\n' + s[b:])


def inject_guide(rel, block):
    s = read(rel)
    a = s.index('<!-- guide:start -->') + len('<!-- guide:start -->')
    b = s.index('<!-- guide:end -->')
    write(rel, s[:a] + '\n' + block + '\n    ' + s[b:])


def fix_chrome(rel, current):
    s = read(rel)
    s = re.sub(r'<header class="site-head">.*?</header>', lambda m: header(current), s, count=1, flags=re.S)
    s = re.sub(r'<p class="foot-links">.*?</p>|<p>(?:<a href="/">전체 테스트</a> &nbsp; )?<a href="/privacy.html">개인정보처리방침</a></p>',
               FOOT_LINKS, s)
    write(rel, s)


# ── 거울 ─────────────────────────────────────────────
STARS = [(22, 30, .9), (35, 17, .6), (78, 36, .7), (18, 56, .7), (48, 40, .5), (58, 63, .8),
         (73, 71, .6), (85, 55, .9), (42, 85, .6), (63, 87, .7), (27, 43, .4), (53, 13, .5), (88, 43, .4),
         (38, 61, .5)]
SPARKS = [(65, 23, 3.2), (30, 73, 2.6), (80, 79, 1.8)]


def mirror_markup(main=True):
    gems = []
    for k in range(8):
        big = k % 2 == 0
        d = 'M150 1L154.5 8L150 15L145.5 8Z' if big else 'M150 4L152.6 8L150 12L147.4 8Z'
        gems.append(f'<path class="rim-gem{"" if big else " sm"}" fill="#C8A45E" d="{d}" transform="rotate({k * 45} 150 150)"/>')
        gems.append(f'<circle class="rim-gem sm" fill="#C8A45E" cx="150" cy="8" r="1.3" transform="rotate({k * 45 + 22.5} 150 150)"/>')
    line = 'fill="none" stroke="#C8A45E" stroke-opacity=".5" stroke-width=".8"'
    rim = ('<svg class="mirror-rim" viewBox="0 0 300 300" width="0" height="0">'
           f'<circle class="rim-line" {line} cx="150" cy="150" r="128"/>'
           '<circle class="rim-ticks" fill="none" stroke="#C8A45E" stroke-opacity=".55" stroke-width="5" '
           'cx="150" cy="150" r="135" stroke-dasharray="1.3 10.48"/>'
           f'<circle class="rim-line" {line} cx="150" cy="150" r="142"/>' + ''.join(gems) + '</svg>')
    stars = ''.join(f'<circle class="star" fill="#F4EFE3" cx="{x}" cy="{y}" r="{r}" style="animation-delay:{(i * 0.53) % 3.6:.2f}s"/>'
                    for i, (x, y, r) in enumerate(STARS))
    sparks = ''.join(
        f'<path class="spark" fill="#F6DFA6" d="M{x} {y - s}Q{x} {y} {x + s} {y}Q{x} {y} {x} {y + s}Q{x} {y} {x - s} {y}Q{x} {y} {x} {y - s}Z" '
        f'style="animation-delay:{i * 1.4:.1f}s"/>'
        for i, (x, y, s) in enumerate(SPARKS))
    sky = ('<svg class="mirror-sky" viewBox="0 0 100 100" width="0" height="0">'
           '<circle class="ring" fill="none" stroke="#E9E4D8" stroke-opacity=".16" stroke-width=".35" cx="50" cy="50" r="44"/>'
           f'{stars}{sparks}</svg>')
    ripples = '<span class="ripple"></span>' * 3 if main else ''
    mid = ' id="mirror"' if main else ''
    return (f'      <div class="mirror-wrap" aria-hidden="true">\n'
            f'        {rim}\n'
            f'        <div class="mirror"{mid}>{ripples}{sky}<span class="sheen"></span></div>\n'
            f'      </div>')


def fix_mirror(rel, main):
    s = read(rel)
    if '<!-- mirror:start -->' not in s:
        s, n = re.subn(r'<div class="mirror"[^>]*>(?:\s*<span class="ripple"></span>)*\s*</div>',
                       '<!-- mirror:start -->\n      <!-- mirror:end -->', s, count=1)
        assert n == 1, rel
    a = s.index('<!-- mirror:start -->') + len('<!-- mirror:start -->')
    b = s.index('<!-- mirror:end -->')
    write(rel, s[:a] + '\n' + mirror_markup(main) + '\n      ' + s[b:])


# ── 새 페이지들 ─────────────────────────────────────────────
def build_cards(cards):
    for i, c in enumerate(cards):
        prev_c, next_c = cards[i - 1], cards[(i + 1) % len(cards)]
        main = f'''    <p class="crumb"><a href="/tarot/cards/">메이저 아르카나 22장</a></p>
    <h1>{esc(c["ko"])} 카드의 의미</h1>
    <p class="summary">타로 메이저 아르카나 {c["num"]}번 카드, {esc(c["en"])}</p>
    {card_face(c)}
    <dl class="facts">
      <dt>키워드</dt><dd>{esc(c["kw"])}</dd>
      <dt>행운의 색</dt><dd><i class="swatch" style="background:{c["color"]["c"]}"></i>{esc(c["color"]["n"])}</dd>
      <dt>순서</dt><dd>22장 가운데 {i + 1}번째 카드</dd>
    </dl>

    <h2>그림 속 이야기</h2>
    <p>{esc(c["symbol"])}</p>

    <h2>이 카드의 뜻</h2>
    <p>{esc(c["meaning"])}</p>

    <h2>오늘의 카드로 나왔다면</h2>
    <p>{esc(c["msg"])}</p>

    <h2>사랑</h2>
    <p>{esc(c["love"])}</p>

    <h2>일과 돈</h2>
    <p>{esc(c["work"])}</p>

    <h2>거꾸로 나왔을 때</h2>
    <p>{esc(c["reversed"])}</p>

    <h2>오늘 스스로에게 물어볼 것</h2>
    <blockquote>{esc(c["question"])}</blockquote>
    <p>{esc(c["ko"])} 카드가 건네는 한마디는 이거예요. {esc(c["advice"])}</p>

    <h2 id="y{YEAR}">{YEAR}년 신년 타로에서 나왔다면</h2>
    <p>{esc(c["ko"])} 카드가 담은 {YEAR}년의 한 단어는 ‘{esc(c["ny"]["word"])}’{ieyo(c["ny"]["word"])}. 신년 타로에서는 카드가 놓인 자리에 따라 이렇게 읽어요.</p>
    <dl class="facts">
      <dt>상반기</dt><dd>{esc(c["ny"]["h1"])}</dd>
      <dt>하반기</dt><dd>{esc(c["ny"]["h2"])}</dd>
      <dt>올해의 열쇠</dt><dd>{esc(c["ny"]["key"])}</dd>
    </dl>
    <p><a href="/tarot/{YEAR}/">{YEAR}년 신년 타로 세 장 뽑기</a></p>

    <div class="cta"><a class="btn btn-primary" href="/tarot/">오늘의 타로 한 장 뽑기</a></div>
    <nav class="pager" aria-label="다른 카드">
      <a href="/tarot/cards/{prev_c["slug"]}/">이전 카드: {esc(prev_c["ko"])}</a>
      <a href="/tarot/cards/{next_c["slug"]}/">다음 카드: {esc(next_c["ko"])}</a>
    </nav>'''
        desc = f'타로 {c["ko"]}({c["en"]}) 카드의 뜻을 정리했어요. 키워드는 {c["kw"]}. 그림 속 상징, 사랑과 일, 거꾸로 나왔을 때의 의미까지 확인해 보세요.'
        write(f'tarot/cards/{c["slug"]}/index.html',
              page(f'/tarot/cards/{c["slug"]}/', f'타로 {c["ko"]} 카드 의미 ({c["en"]})', desc, main,
                   og='/share-tarot.png', current='/tarot/cards/',
                   note='카드의 뜻은 재미와 하루를 돌아보는 용도로 즐겨 주세요.'))

    grid = ''.join(
        f'<a href="/tarot/cards/{c["slug"]}/">{card_face(c, small=True)}<small>{esc(c["kw"])}</small></a>'
        for c in cards)
    main = f'''    <h1>메이저 아르카나 22장의 의미</h1>
    <p class="summary">타로 78장 가운데 삶의 큰 흐름을 보여 주는 22장이에요. 카드를 누르면 그림 속 이야기와 뜻, 사랑과 일, 거꾸로 나왔을 때의 의미를 볼 수 있어요.</p>
    <p>메이저 아르카나는 0번 바보에서 시작해 21번 세계로 끝나요. 아무것도 모른 채 길을 떠난 바보가 마법사와 여사제, 황제와 교황을 만나 배우고, 사랑과 선택, 시련과 깨달음을 지나 마침내 세계에 이르는 하나의 긴 여행으로 읽기도 해요. 그래서 카드 한 장 한 장을 볼 때, 이 카드가 여행의 어느 지점에 있는지 떠올려 보면 뜻이 더 잘 보여요.</p>
    <p>앞쪽 카드들은 새로운 시작과 배움, 관계를 이야기하고, 가운데 카드들은 기다림과 변화, 내면의 시험을 이야기해요. 마지막 카드들은 희망과 깨어남, 완성을 이야기하지요.</p>
    <div class="card-grid">{grid}</div>

    <h2>카드를 읽는 작은 팁</h2>
    <p>타로 카드를 정답이 적힌 종이로 보기보다, 오늘 하루를 돌아보게 하는 질문으로 써 보세요. 카드 페이지마다 ‘오늘 스스로에게 물어볼 것’을 하나씩 적어 두었어요. 카드가 처음이라면 <a href="/read/tarot-basics/">타로 처음 보는 법</a>을 먼저 읽어 보는 것도 좋아요.</p>
    <div class="cta"><a class="btn btn-primary" href="/tarot/">오늘의 타로 한 장 뽑기</a></div>'''
    write('tarot/cards/index.html',
          page('/tarot/cards/', '타로 메이저 아르카나 22장 의미 총정리',
               '타로 메이저 아르카나 22장의 뜻을 한눈에 정리했어요. 바보부터 세계까지 카드별 그림 속 상징, 사랑과 일, 거꾸로 나왔을 때의 의미를 확인해 보세요.',
               main, og='/share-tarot.png', current='/tarot/cards/', kind='website'))


def build_reads():
    for i, a in enumerate(ARTICLES):
        others = [x for x in ARTICLES if x['slug'] != a['slug']][:3]
        main = f'''    <p class="crumb"><a href="/read/">읽을거리</a></p>
    <h1>{esc(a["title"])}</h1>
    <p class="summary">{esc(a["summary"])}</p>
{a["body"].strip()}

    <div class="cta"><a class="btn btn-primary" href="{a["cta"][0]}">{esc(a["cta"][1])}</a></div>

    <h2>함께 읽으면 좋은 글</h2>
    {read_list(others)}'''
        write(f'read/{a["slug"]}/index.html',
              page(f'/read/{a["slug"]}/', a['title'], a['summary'], main,
                   og=a.get('og', '/share.png'), current='/read/'))

    main = f'''    <h1>읽을거리</h1>
    <p class="summary">전생과 인연, 타로에 얽힌 옛이야기와 역사를 모았어요. 테스트 결과를 더 재미있게 즐기고 싶다면 읽어 보세요.</p>
    {read_list(ARTICLES)}
    <h2>타로 카드 의미</h2>
    <p>메이저 아르카나 22장의 그림 속 이야기와 뜻은 <a href="/tarot/cards/">카드 의미</a>에 따로 정리해 두었어요.</p>'''
    write('read/index.html',
          page('/read/', '읽을거리', '전생, 윤회, 붉은 실, 타로에 얽힌 옛이야기와 역사를 소개하는 전생 거울의 읽을거리 모음이에요.',
               main, current='/read/', kind='website'))


def build_about():
    main = '''    <h1>전생 거울을 소개해요</h1>
    <p class="summary">이름과 생년월일, 카드 한 장으로 전생과 인연, 오늘의 흐름을 재미로 들여다보는 작은 사이트예요.</p>

    <h2>이름에 담긴 이야기</h2>
    <p>전생 거울이라는 이름은 옛이야기 속 업경대에서 빌려 왔어요. 업경대는 저승 재판정에 놓여 지나온 삶을 그대로 비춰 준다는 거울이에요. 전생 거울은 누군가를 심판하는 대신, 다른 시대의 나를 상상해 보는 즐거운 거울이 되고 싶어요. <a href="/read/mirror-of-karma/">업경대 이야기 읽기</a></p>

    <h2>만든 사람</h2>
    <p>코딩을 따로 배운 적 없는 한 사람이 휴대폰 하나로, AI의 도움을 받아 가며 만들고 있어요. 2026년 11월에 첫 테스트인 전생 체험을 열었고, 이어서 전생의 인연 궁합과 오늘의 타로 한 장, 2027년 신년 타로를 더했어요. 새로운 테스트와 읽을거리를 조금씩 늘려 갈 예정이에요.</p>

    <h2>결과는 이렇게 만들어져요</h2>
    <p>전생 체험과 인연 궁합은 입력한 이름과 생년월일을 하나의 숫자로 바꾼 뒤, 그 숫자에 맞는 이야기를 미리 써 둔 이야기들 가운데서 골라 보여 줘요. 그래서 같은 정보를 넣으면 언제나 같은 결과가 나와요. 결과에 나오는 시대와 직업은 실제 역사 속 장소와 직업을 바탕으로 직접 썼어요.</p>
    <p>오늘의 타로 한 장은 메이저 아르카나 22장 가운데 한 장을, 신년 타로는 세 장을 고르는 방식이에요. 카드마다 오늘의 흐름과 사랑, 일과 돈, 한마디, 그리고 2027년 풀이를 따로 정리했고, 카드별 자세한 뜻은 <a href="/tarot/cards/">카드 의미</a>에서 볼 수 있어요.</p>

    <h2>이용할 때 알아 두세요</h2>
    <p>모든 결과는 재미로 즐기기 위한 것이에요. 건강, 돈, 진로처럼 중요한 결정은 결과에 기대기보다 충분히 알아보고 전문가와 상의해 주세요. 입력한 이름과 생년월일은 서버로 보내거나 저장하지 않아요. 자세한 내용은 <a href="/privacy.html">개인정보처리방침</a>에서 볼 수 있어요.</p>

    <h2 id="contact">문의</h2>
    <p>사이트에 관한 의견이나 오류 제보, 제휴 문의는 <a href="https://github.com/ykkle0440l/past-life/issues" rel="noopener">GitHub 문의 게시판</a>에 남겨 주세요. 남겨 주신 의견은 하나하나 읽고 사이트에 반영할게요.</p>'''
    write('about/index.html',
          page('/about/', '전생 거울 소개', '전생 거울은 이름과 생년월일, 카드 한 장으로 전생과 인연, 오늘의 흐름을 재미로 들여다보는 작은 사이트예요.',
               main, kind='website'))


def build_privacy():
    main = '''    <h1>개인정보처리방침</h1>
    <p class="summary">시행일: 2026년 11월 1일 (2026년 11월 5일 고침)</p>

    <h2>입력한 정보</h2>
    <p>전생 거울은 이름과 생년월일을 입력받아 결과를 보여 줍니다. 이 정보는 이용자의 기기(브라우저) 안에서만 계산에 쓰이며, 서버로 보내거나 저장하지 않습니다.</p>

    <h2>기기에 저장되는 정보</h2>
    <p>오늘의 타로는 하루에 한 장만 뽑을 수 있도록, 신년 타로는 뽑은 세 장을 다시 보여 드리기 위해, 뽑은 카드 번호와 날짜를 이용자 기기의 브라우저에 저장합니다. 이 정보는 서버로 보내지 않으며, 브라우저의 사이트 데이터를 지우면 함께 삭제됩니다.</p>

    <h2>결과 공유</h2>
    <p>결과를 공유하면 링크에 이름(인연 궁합은 두 사람의 이름)과 결과 번호가 들어갑니다. 타로와 신년 타로는 카드 번호만 들어갑니다. 생년월일은 링크에 들어가지 않습니다. 링크를 받은 사람은 링크에 담긴 이름을 볼 수 있으니, 공유 전에 참고해 주세요.</p>
    <p>공유 창에서 카카오톡, X, 스레드, 페이스북, 메시지를 고르면 해당 서비스나 앱으로 이동하며, 그 이후에는 각 서비스의 개인정보처리방침이 적용됩니다.</p>

    <h2>광고와 쿠키</h2>
    <p>이 사이트에는 쿠팡 파트너스, Google 애드센스 등 제3자 광고가 표시될 수 있습니다. 이런 광고 서비스는 맞춤 광고를 위해 쿠키를 사용할 수 있으며, Google의 광고 쿠키 사용은 <a href="https://policies.google.com/technologies/ads?hl=ko" rel="noopener">Google 광고 정책</a>에서 확인할 수 있습니다. 쿠키는 브라우저 설정에서 거부하거나 삭제할 수 있습니다.</p>

    <h2>문의</h2>
    <p>개인정보와 관련된 문의는 <a href="/about/#contact">문의 안내</a>를 참고해 주세요.</p>'''
    write('privacy.html',
          page('/privacy.html', '개인정보처리방침', '전생 거울의 개인정보처리방침이에요.', main,
               kind='website', ads=False, note='전생 거울'))


def build_404():
    main = '''    <h1>찾는 페이지가 없어요</h1>
    <p class="summary">주소가 바뀌었거나 잘못 입력된 것 같아요.</p>
    <div class="cta"><a class="btn btn-primary" href="/">전생 거울 첫 화면으로 가기</a></div>'''
    s = page('/404.html', '페이지를 찾을 수 없어요', '찾는 페이지가 없어요.', main, kind='website', ads=False, note='전생 거울')
    write('404.html', s.replace('<link rel="canonical" href="https://pstlf.co.kr/404.html">', '<meta name="robots" content="noindex">'))


def build_hub():
    rel = 'index.html'
    s = read(rel)
    block = f'''    <section class="guide" aria-labelledby="readsTitle">
      <h2 id="readsTitle">타로 카드 의미</h2>
      <p>오늘 뽑은 카드가 더 궁금하다면, 메이저 아르카나 22장의 그림 속 이야기와 뜻, 거꾸로 나왔을 때의 의미를 정리한 <a href="/tarot/cards/">카드 의미</a>를 읽어 보세요.</p>
      <h2>읽을거리</h2>
      {read_list(ARTICLES)}
    </section>'''
    if '<!-- reads:start -->' not in s:
        s = s.replace('    <section class="about">', '    <!-- reads:start -->\n    <!-- reads:end -->\n\n    <section class="about">', 1)
    a = s.index('<!-- reads:start -->') + len('<!-- reads:start -->')
    b = s.index('<!-- reads:end -->')
    write(rel, s[:a] + '\n' + block + '\n    ' + s[b:])
    fix_chrome(rel, '/')


SHOP_NOTICE = '이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.'

SHOP_ITEMS_TEMPLATE = '''# 영상 속 상품 목록 (https://pstlf.co.kr/shop/ 에 나와요)
#
# 한 줄에 상품 하나씩 쓰고, 칸은 | 로 나눠요.
#   번호 | 상품명 | 쿠팡 파트너스 링크 | 한 줄 소개 | 분야 | 상품 사진 주소
#
# - 번호: 영상에서 "프로필 링크에서 ○번" 이라고 안내할 숫자예요. 같은 번호는 한 번만 써요.
# - 쿠팡 파트너스 링크: https:// 로 시작하는 링크만 나와요.
# - 한 줄 소개, 분야, 상품 사진 주소는 비워 둬도 돼요.
# - 맨 앞에 # 이 있는 줄은 사이트에 나오지 않아요.
#
# 예시 (맨 앞 # 을 지우면 사이트에 나와요)
# 1 | 접이식 실리콘 냄비 | https://link.coupang.com/a/xxxxxx | 접으면 손바닥만 해지는 캠핑 냄비 | 캠핑
'''

SHOP_STYLE = '''<style>
:root {
  --cream: #FFF7EF; --card: #FFFFFF; --ink: #4A3A33; --ink-soft: #7A665C; --line: #F3E3D6;
  --peach: #FFB9A3; --peach-deep: #F2937A; --butter: #FFE7A0; --mint: #CDEBDD; --pink: #FFD6DE; --lilac: #E3DAFA;
  --round: 'Jua', 'Gowun Dodum', 'Noto Sans KR', 'Noto Sans CJK KR', sans-serif;
  --body: 'Gowun Dodum', 'Noto Sans KR', 'Noto Sans CJK KR', 'Apple SD Gothic Neo', sans-serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
html { background: var(--cream); }
body { margin: 0; color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.7; word-break: keep-all;
  -webkit-text-size-adjust: 100%;
  background: radial-gradient(circle at 12% 4%, #FFE3D6 0, rgba(255,227,214,0) 210px),
    radial-gradient(circle at 92% 14%, #E2F3EA 0, rgba(226,243,234,0) 190px),
    radial-gradient(circle at 80% 70%, #FFF0C9 0, rgba(255,240,201,0) 260px), var(--cream);
  background-attachment: fixed; }
[hidden] { display: none !important; }
:focus-visible { outline: 3px solid var(--peach-deep); outline-offset: 3px; }
.shop-page { max-width: 460px; margin: 0 auto; padding: 18px 18px 28px; min-height: 100svh; display: flex; flex-direction: column; }
.shop-page main { flex: 1; }
.shop-notice { display: flex; gap: 8px; align-items: flex-start; margin: 0 0 22px; padding: 10px 14px; border-radius: 14px;
  background: #FFEDE6; border: 1px dashed #F5B8A6; color: #6B4436; font-size: .86rem; line-height: 1.6; }
.shop-notice::before { content: 'AD'; flex: none; margin-top: 2px; padding: 0 6px; border-radius: 6px; background: #C9583F; color: #fff;
  font-size: .7rem; font-weight: 700; line-height: 1.7; letter-spacing: .04em; }
.shop-hero { text-align: center; margin: 4px 0 22px; }
.shop-hero svg { display: block; width: 74px; height: 74px; margin: 0 auto 6px; }
h1 { font-family: var(--round); font-weight: 400; font-size: 2rem; line-height: 1.3; margin: 0 0 8px; color: var(--ink); }
.summary { color: var(--ink-soft); margin: 0; font-size: .96rem; }
.shop-search { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end; padding: 14px; border-radius: 22px;
  background: var(--card); box-shadow: 0 6px 18px rgba(242,147,122,.14); }
.shop-search label { display: block; font-family: var(--round); font-size: 1rem; color: var(--ink); margin: 0 0 6px 4px; }
.shop-search input { display: block; width: 100%; height: 52px; padding: 0 18px; font: inherit; font-family: var(--round); font-size: 19px;
  color: var(--ink); background: #FFF9F4; border: 2px solid var(--line); border-radius: 999px; -webkit-appearance: none; appearance: none; }
.shop-search input::placeholder { color: #C7B3A8; }
.shop-search input:focus { outline: none; border-color: var(--peach); box-shadow: 0 0 0 4px rgba(255,185,163,.3); }
.btn { display: flex; align-items: center; justify-content: center; border: 0; font: inherit; cursor: pointer; text-decoration: none;
  -webkit-tap-highlight-color: transparent; }
.btn:active { transform: translateY(1px); }
.shop-search .btn { height: 52px; min-width: 78px; padding: 0 20px; border-radius: 999px; background: var(--peach-deep); color: #3E2219;
  font-family: var(--round); font-size: 1.1rem; box-shadow: 0 3px 0 #D9775F; }
.shop-status { color: var(--ink-soft); font-size: .92rem; margin: 16px 4px 10px; min-height: 1.6em; }
.shop-all { background: none; padding: 0 4px; min-height: 44px; margin: -6px 0 8px; color: #B5523B; font-family: var(--round);
  font-size: 1rem; text-decoration: underline; text-underline-offset: 4px; }
.shop-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
.shop-list li { margin: 0; }
.shop-link { display: grid; grid-template-columns: 64px 1fr; gap: 8px 14px; align-items: center; padding: 14px; border-radius: 22px;
  background: var(--card); color: var(--ink); text-decoration: none; box-shadow: 0 6px 18px rgba(242,147,122,.12);
  border: 2px solid transparent; -webkit-tap-highlight-color: transparent; }
.shop-link:active { transform: scale(.99); }
.shop-item.is-hit .shop-link { border-color: var(--peach); box-shadow: 0 0 0 4px rgba(255,185,163,.28), 0 6px 18px rgba(242,147,122,.14); }
.shop-media { position: relative; width: 64px; height: 64px; border-radius: 50%; overflow: hidden; display: grid; place-items: center;
  background: var(--butter); }
.shop-media.c1 { background: var(--mint); } .shop-media.c2 { background: var(--pink); } .shop-media.c3 { background: var(--lilac); }
.shop-media.has-img { border-radius: 18px; background: #fff; border: 2px solid var(--line); }
.shop-media img { width: 100%; height: 100%; object-fit: cover; }
.shop-num { font-family: var(--round); color: var(--ink); font-size: 1.55rem; line-height: 1; }
.shop-num small { font-size: .8rem; margin-left: 1px; }
.shop-media.has-img .shop-num { position: absolute; left: 0; top: 0; padding: 3px 7px; font-size: .84rem; background: var(--butter);
  border-bottom-right-radius: 12px; }
.shop-media.has-img .shop-num small { font-size: .7rem; }
.shop-body { min-width: 0; }
.shop-body strong { display: block; font-family: var(--round); font-weight: 400; font-size: 1.08rem; line-height: 1.45; overflow-wrap: anywhere; }
.shop-body small { display: block; color: var(--ink-soft); font-size: .88rem; line-height: 1.55; margin-top: 2px; }
.shop-cat { display: inline-block; margin-top: 6px; padding: 1px 10px; border-radius: 999px; font-size: .76rem; color: #3F6B57; background: var(--mint); }
.shop-go { grid-column: 1 / -1; display: flex; align-items: center; justify-content: center; min-height: 46px; margin-top: 4px;
  border-radius: 999px; background: var(--peach); color: #4A2A20; font-family: var(--round); font-size: 1.02rem; }
.shop-foot { margin-top: 44px; text-align: center; color: var(--ink-soft); font-size: .82rem; line-height: 1.6; }
.shop-foot p { margin: 0 0 6px; }
.shop-foot a { color: var(--ink-soft); text-underline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { .btn:active, .shop-link:active { transform: none; } }
</style>'''

SHOP_SCRIPT = r'''<script>
(function () {
  'use strict';
  var list = document.getElementById('shopList');
  var statusEl = document.getElementById('shopStatus');
  var form = document.getElementById('shopSearch');
  var input = document.getElementById('shopNum');
  var allBtn = document.getElementById('shopAll');
  var items = [];
  var ready = false;
  var LINK = /^https:\/\/[^\s"'<>\\]+$/i;

  function parse(text) {
    var byNum = {};
    text.split(/\r?\n/).forEach(function (line) {
      line = line.trim();
      if (!line || line.charAt(0) === '#') return;
      var f = line.split('|').map(function (s) { return s.trim(); });
      var m = /^(\d{1,6})\s*번?$/.exec(f[0] || '');
      var num = m ? parseInt(m[1], 10) : 0;
      var name = f[1] || '', url = f[2] || '', img = f[5] || '';
      if (!num || !name || !LINK.test(url)) return;
      byNum[num] = { num: num, name: name, url: url, desc: f[3] || '', cat: f[4] || '', img: LINK.test(img) ? img : '' };
    });
    return Object.keys(byNum).map(function (k) { return byNum[k]; }).sort(function (a, b) { return b.num - a.num; });
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  function card(it, hit) {
    var li = el('li', 'shop-item' + (hit ? ' is-hit' : ''));
    li.id = 'item-' + it.num;
    var a = el('a', 'shop-link');
    a.href = it.url;
    a.target = '_blank';
    a.rel = 'sponsored nofollow noopener';
    a.setAttribute('aria-label', it.num + '번 ' + it.name + ', 쿠팡에서 보기 (새 창)');
    var tone = ' c' + (it.num % 4);
    var media = el('span', 'shop-media' + tone);
    var num = el('span', 'shop-num', String(it.num));
    num.appendChild(el('small', '', '번'));
    if (it.img) {
      var img = document.createElement('img');
      img.src = it.img;
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      img.referrerPolicy = 'no-referrer';
      img.onerror = function () { img.remove(); media.className = 'shop-media' + tone; };
      media.className = 'shop-media has-img';
      media.appendChild(img);
    }
    media.appendChild(num);
    var body = el('span', 'shop-body');
    body.appendChild(el('strong', '', it.name));
    if (it.desc) body.appendChild(el('small', '', it.desc));
    if (it.cat) body.appendChild(el('span', 'shop-cat', it.cat));
    a.appendChild(media);
    a.appendChild(body);
    a.appendChild(el('span', 'shop-go', '쿠팡에서 보기 ›'));
    li.appendChild(a);
    return li;
  }

  function render(arr, hit) {
    list.textContent = '';
    arr.forEach(function (it) { list.appendChild(card(it, hit)); });
  }

  function setUrl(n) {
    try { history.replaceState(null, '', location.pathname + (n ? '?n=' + n : '')); } catch (e) {}
  }

  function show(q) {
    if (!ready) return;
    var digits = String(q || '').replace(/[^0-9]/g, '').slice(0, 6);
    var n = digits ? parseInt(digits, 10) : 0;
    if (!n) {
      render(items, false);
      statusEl.textContent = items.length ? '상품 ' + items.length + '개가 있어요. 최근에 올라온 순서예요.'
        : '아직 올라온 상품이 없어요. 영상이 올라오면 여기에 하나씩 채워져요.';
      allBtn.hidden = true;
      setUrl('');
      return;
    }
    var hit = items.filter(function (it) { return it.num === n; });
    render(hit, true);
    statusEl.textContent = hit.length ? n + '번 상품이에요.' : n + '번 상품을 찾지 못했어요. 영상 속 번호를 다시 확인해 주세요.';
    allBtn.hidden = !items.length;
    setUrl(String(n));
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    show(input.value);
    input.blur();
  });
  input.addEventListener('input', function () {
    var v = input.value.replace(/[^0-9]/g, '').slice(0, 6);
    if (v !== input.value) input.value = v;
    show(v);
  });
  allBtn.addEventListener('click', function () {
    input.value = '';
    show('');
    input.focus();
  });

  var start = new URLSearchParams(location.search).get('n') || '';
  statusEl.textContent = '상품 목록을 불러오는 중이에요.';
  fetch('/shop/items.txt', { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
    .then(function (text) {
      items = parse(text);
      ready = true;
      input.value = start.replace(/[^0-9]/g, '').slice(0, 6);
      show(input.value);
    })
    .catch(function () {
      statusEl.textContent = '상품 목록을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.';
    });
})();
</script>'''


SHOP_BAG = ('<svg viewBox="0 0 80 80" aria-hidden="true">'
            '<circle cx="40" cy="42" r="34" fill="#FFE7A0"/>'
            '<path d="M29 32v-4a11 11 0 0 1 22 0v4" fill="none" stroke="#4A3A33" stroke-width="3.2" stroke-linecap="round"/>'
            '<rect x="20" y="30" width="40" height="34" rx="9" fill="#FFB9A3" stroke="#4A3A33" stroke-width="3.2"/>'
            '<circle cx="33" cy="45" r="2.4" fill="#4A3A33"/><circle cx="47" cy="45" r="2.4" fill="#4A3A33"/>'
            '<path d="M35 51q5 4 10 0" fill="none" stroke="#4A3A33" stroke-width="2.6" stroke-linecap="round"/>'
            '<circle cx="28.5" cy="50" r="3" fill="#F2937A" opacity=".55"/><circle cx="51.5" cy="50" r="3" fill="#F2937A" opacity=".55"/>'
            '</svg>')


def build_shop():
    """숏폼 영상 속 상품 모음 (/shop/). 상품은 shop/items.txt 한 파일만 고치면 돼요.
    전생 거울과 분위기를 다르게(밝은 파스텔) 하려고 공통 틀(page) 대신 따로 만든 틀을 써요.
    검색에 나올 필요가 없는 링크 페이지라 noindex, 사이트맵·메뉴에서 빠지고, 애드센스도 넣지 않아요."""
    if not (ROOT / 'shop/items.txt').exists():
        write('shop/items.txt', SHOP_ITEMS_TEMPLATE)
    url = SITE + '/shop/'
    title = '영상 속 상품 모음'
    desc = '숏폼 영상에 나온 상품을 번호로 찾아보는 페이지예요.'
    write('shop/index.html', f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#FFF7EF">
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{title}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/share-shop.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="600">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Jua&display=swap" rel="stylesheet">
{SHOP_STYLE}
</head>
<body>
<div class="shop-page">
  <main>
    <p class="shop-notice" role="note">{SHOP_NOTICE}</p>
    <header class="shop-hero">
      {SHOP_BAG}
      <h1>{title}</h1>
      <p class="summary">영상에서 본 번호를 넣으면 그 상품이 바로 나와요.<br>상품을 누르면 쿠팡 페이지가 새 창으로 열려요.</p>
    </header>

    <form class="shop-search" id="shopSearch" role="search" novalidate>
      <div>
        <label for="shopNum">상품 번호</label>
        <input id="shopNum" name="n" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="off" placeholder="예: 12">
      </div>
      <button class="btn" type="submit">찾기</button>
    </form>
    <p class="shop-status" id="shopStatus" aria-live="polite"></p>
    <button class="btn shop-all" id="shopAll" type="button" hidden>‹ 전체 상품 보기</button>
    <ol class="shop-list" id="shopList"></ol>
    <noscript><p>상품 목록을 보려면 브라우저의 자바스크립트를 켜 주세요.</p></noscript>
  </main>

  <footer class="shop-foot">
    <p>가격과 재고는 쿠팡에서 바뀔 수 있어요. 구매 전에 상품 페이지에서 꼭 확인해 주세요.</p>
    <p><a href="/privacy.html">개인정보처리방침</a></p>
  </footer>
</div>
{SHOP_SCRIPT}
</body>
</html>
''')


def build_sitemap(cards):
    paths = ['/', '/past-life/', '/bond/', '/tarot/', f'/tarot/{YEAR}/', '/tarot/cards/']
    paths += [f'/tarot/cards/{c["slug"]}/' for c in cards]
    paths += ['/read/'] + [f'/read/{a["slug"]}/' for a in ARTICLES]
    paths += ['/about/', '/privacy.html']
    urls = ''.join(f'  <url><loc>{SITE}{p}</loc><lastmod>{TODAY}</lastmod></url>\n' for p in paths)
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n')
    write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    return len(paths)


def stamp_assets():
    """site.css, site.js 주소 뒤에 ?v=내용해시 를 붙여요. 파일이 바뀌면 주소도 바뀌어 캐시 문제가 없어요."""
    versions = {name: hashlib.sha1(read(f'assets/{name}').encode('utf-8')).hexdigest()[:10]
                for name in ('site.css', 'site.js')}
    count = 0
    for path in ROOT.rglob('*.html'):
        if '_build' in path.parts or '.git' in path.parts:
            continue
        s = path.read_text(encoding='utf-8')
        new = s
        for name, v in versions.items():
            new = re.sub(r'/assets/' + re.escape(name) + r'(\?v=[0-9a-f]+)?"', f'/assets/{name}?v={v}"', new)
        if new != s:
            path.write_text(new, encoding='utf-8')
        count += 1
    return versions, count


def main():
    lives, animals, types, cards = load_data()
    inject_guide('past-life/index.html', guide_pastlife(lives, animals))
    inject_guide('bond/index.html', guide_bond(types))
    inject_guide('tarot/index.html', guide_tarot(cards))
    ny_rel = f'tarot/{YEAR}/index.html'
    inject_guide(ny_rel, guide_newyear(cards))
    inject_data(ny_rel, newyear_data(cards))
    for rel in ['past-life/index.html', 'bond/index.html', 'tarot/index.html', ny_rel]:
        fix_chrome(rel, '/')
    build_hub()
    fix_mirror('past-life/index.html', main=True)
    fix_mirror('index.html', main=False)
    build_cards(cards)
    build_reads()
    build_about()
    build_privacy()
    build_404()
    build_shop()
    n = build_sitemap(cards)
    versions, pages = stamp_assets()
    print('assets', versions, 'pages', pages)
    print(f'ok: lives={sum(len(l["roles"]) for l in lives)} animals={len(animals)} bonds={len(types)} cards={len(cards)} '
          f'articles={len(ARTICLES)} newyear={len(NEWYEAR)} sitemap={n}')


if __name__ == '__main__':
    main()
