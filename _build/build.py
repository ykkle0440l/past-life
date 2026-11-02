#!/usr/bin/env python3
"""전생 거울 정적 페이지 만들기

python3 _build/build.py 로 실행하면
- 세 테스트 페이지 아래 설명글(guide)을 채우고
- 상단 메뉴와 아래 링크를 모든 페이지에 맞추고
- 타로 카드 의미 22장, 읽을거리, 소개, 개인정보처리방침, 404, sitemap 을 만들어요.
결과 데이터(전생, 인연, 카드)는 각 테스트 페이지의 스크립트에서 그대로 읽어 와요.
(_build 폴더는 밑줄로 시작해서 GitHub Pages 에는 올라가지 않아요.)
"""
import datetime
import html
import json
import pathlib
import re
import subprocess

from content_read import ARTICLES
from content_tarot import CARD_EXTRA

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
    assert len(cards) == len(CARD_EXTRA) == 22
    for c, extra in zip(cards, CARD_EXTRA):
        c.update(extra)
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
        gems.append(f'<path class="rim-gem{"" if big else " sm"}" d="{d}" transform="rotate({k * 45} 150 150)"/>')
        gems.append(f'<circle class="rim-gem sm" cx="150" cy="8" r="1.3" transform="rotate({k * 45 + 22.5} 150 150)"/>')
    rim = ('<svg class="mirror-rim" viewBox="0 0 300 300">'
           '<circle class="rim-line" cx="150" cy="150" r="128"/>'
           '<circle class="rim-ticks" cx="150" cy="150" r="135" stroke-dasharray="1.3 10.48"/>'
           '<circle class="rim-line" cx="150" cy="150" r="142"/>' + ''.join(gems) + '</svg>')
    stars = ''.join(f'<circle class="star" cx="{x}" cy="{y}" r="{r}" style="animation-delay:{(i * 0.53) % 3.6:.2f}s"/>'
                    for i, (x, y, r) in enumerate(STARS))
    sparks = ''.join(
        f'<path class="spark" d="M{x} {y - s}Q{x} {y} {x + s} {y}Q{x} {y} {x} {y + s}Q{x} {y} {x - s} {y}Q{x} {y} {x} {y - s}Z" '
        f'style="animation-delay:{i * 1.4:.1f}s"/>'
        for i, (x, y, s) in enumerate(SPARKS))
    sky = f'<svg class="mirror-sky" viewBox="0 0 100 100"><circle class="ring" cx="50" cy="50" r="44"/>{stars}{sparks}</svg>'
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
    <p>코딩을 따로 배운 적 없는 한 사람이 휴대폰 하나로, AI의 도움을 받아 가며 만들고 있어요. 2026년 11월에 첫 테스트인 전생 체험을 열었고, 이어서 전생의 인연 궁합과 오늘의 타로 한 장을 더했어요. 새로운 테스트와 읽을거리를 조금씩 늘려 갈 예정이에요.</p>

    <h2>결과는 이렇게 만들어져요</h2>
    <p>전생 체험과 인연 궁합은 입력한 이름과 생년월일을 하나의 숫자로 바꾼 뒤, 그 숫자에 맞는 이야기를 미리 써 둔 이야기들 가운데서 골라 보여 줘요. 그래서 같은 정보를 넣으면 언제나 같은 결과가 나와요. 결과에 나오는 시대와 직업은 실제 역사 속 장소와 직업을 바탕으로 직접 썼어요.</p>
    <p>오늘의 타로 한 장은 메이저 아르카나 22장 가운데 한 장을 고르는 방식이에요. 카드마다 오늘의 흐름과 사랑, 일과 돈, 한마디를 따로 정리했고, 카드별 자세한 뜻은 <a href="/tarot/cards/">카드 의미</a>에서 볼 수 있어요.</p>

    <h2>이용할 때 알아 두세요</h2>
    <p>모든 결과는 재미로 즐기기 위한 것이에요. 건강, 돈, 진로처럼 중요한 결정은 결과에 기대기보다 충분히 알아보고 전문가와 상의해 주세요. 입력한 이름과 생년월일은 서버로 보내거나 저장하지 않아요. 자세한 내용은 <a href="/privacy.html">개인정보처리방침</a>에서 볼 수 있어요.</p>

    <h2 id="contact">문의</h2>
    <p>사이트에 관한 의견이나 오류 제보, 제휴 문의는 <a href="https://github.com/ykkle0440l/past-life/issues" rel="noopener">GitHub 문의 게시판</a>에 남겨 주세요. 남겨 주신 의견은 하나하나 읽고 사이트에 반영할게요.</p>'''
    write('about/index.html',
          page('/about/', '전생 거울 소개', '전생 거울은 이름과 생년월일, 카드 한 장으로 전생과 인연, 오늘의 흐름을 재미로 들여다보는 작은 사이트예요.',
               main, kind='website'))


def build_privacy():
    main = '''    <h1>개인정보처리방침</h1>
    <p class="summary">시행일: 2026년 11월 1일 (2026년 11월 2일 고침)</p>

    <h2>입력한 정보</h2>
    <p>전생 거울은 이름과 생년월일을 입력받아 결과를 보여 줍니다. 이 정보는 이용자의 기기(브라우저) 안에서만 계산에 쓰이며, 서버로 보내거나 저장하지 않습니다.</p>

    <h2>기기에 저장되는 정보</h2>
    <p>오늘의 타로는 하루에 한 장만 뽑을 수 있도록, 뽑은 카드 번호와 날짜를 이용자 기기의 브라우저에 저장합니다. 이 정보는 서버로 보내지 않으며, 브라우저의 사이트 데이터를 지우면 함께 삭제됩니다.</p>

    <h2>결과 공유</h2>
    <p>결과를 공유하면 링크에 이름(인연 궁합은 두 사람의 이름)과 결과 번호가 들어갑니다. 생년월일은 링크에 들어가지 않습니다. 링크를 받은 사람은 링크에 담긴 이름을 볼 수 있으니, 공유 전에 참고해 주세요.</p>
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


def build_sitemap(cards):
    paths = ['/', '/past-life/', '/bond/', '/tarot/', '/tarot/cards/']
    paths += [f'/tarot/cards/{c["slug"]}/' for c in cards]
    paths += ['/read/'] + [f'/read/{a["slug"]}/' for a in ARTICLES]
    paths += ['/about/', '/privacy.html']
    urls = ''.join(f'  <url><loc>{SITE}{p}</loc><lastmod>{TODAY}</lastmod></url>\n' for p in paths)
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n')
    write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    return len(paths)


def main():
    lives, animals, types, cards = load_data()
    inject_guide('past-life/index.html', guide_pastlife(lives, animals))
    inject_guide('bond/index.html', guide_bond(types))
    inject_guide('tarot/index.html', guide_tarot(cards))
    for rel in ['past-life/index.html', 'bond/index.html', 'tarot/index.html']:
        fix_chrome(rel, '/')
    build_hub()
    fix_mirror('past-life/index.html', main=True)
    fix_mirror('index.html', main=False)
    build_cards(cards)
    build_reads()
    build_about()
    build_privacy()
    build_404()
    n = build_sitemap(cards)
    print(f'ok: lives={sum(len(l["roles"]) for l in lives)} animals={len(animals)} bonds={len(types)} cards={len(cards)} '
          f'articles={len(ARTICLES)} sitemap={n}')


if __name__ == '__main__':
    main()
