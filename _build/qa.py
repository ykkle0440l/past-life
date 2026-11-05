"""전생 거울 전체 점검

사이트를 고친 뒤에는 항상 이렇게 실행해요.
    python3 _build/build.py && python3 _build/qa.py
마지막 줄이 "문제 0건"이어야 올려요. 화면 사진은 임시 폴더(pstlf-qa)에 저장돼요.
"""
import os, pathlib, re, struct, subprocess, sys, tempfile, time
from urllib.parse import parse_qs, unquote, urlparse
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(tempfile.gettempdir()) / 'pstlf-qa'
OUT.mkdir(exist_ok=True)
CHROME = '/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
PORT = 8780
B = f'http://127.0.0.1:{PORT}'
SITE = 'https://pstlf.co.kr'
fails, notes = [], []

def b36(n):
    d = '0123456789abcdefghijklmnopqrstuvwxyz'; out = ''
    while True:
        n, r = divmod(n, 36); out = d[r] + out
        if n == 0: return out

def check(cond, msg):
    if not cond:
        fails.append(msg)
    return cond

# ── A. 파일 점검 ─────────────────────────────
html_files = sorted(p for p in ROOT.rglob('*.html') if '_build' not in p.parts and '.git' not in p.parts)
notes.append(f'HTML 페이지 {len(html_files)}개')

class TagCheck(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','source','track','wbr','path','circle','rect','ellipse','line','polyline','polygon','stop'}
    def __init__(self):
        super().__init__(); self.stack = []; self.errors = []
    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID: self.stack.append(tag)
    def handle_startendtag(self, tag, attrs): pass
    def handle_endtag(self, tag):
        if tag in self.VOID: return
        if self.stack and self.stack[-1] == tag: self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag: self.errors.append('닫히지 않은 <%s>' % self.stack.pop())
            self.stack.pop()
        else: self.errors.append('짝 없는 </%s>' % tag)

versions = set()
for f in html_files:
    rel = str(f.relative_to(ROOT)); s = f.read_text(encoding='utf-8')
    check(s.count('<title>') == 1, f'{rel}: title 개수')
    check('<html lang="ko">' in s, f'{rel}: lang')
    check(len(re.findall(r'<h1[ >]', s)) == 1, f'{rel}: h1 개수 {len(re.findall(r"<h1[ >]", s))}')
    check('name="description"' in s, f'{rel}: description 없음')
    if rel != '404.html':
        check('rel="canonical"' in s, f'{rel}: canonical 없음')
    for img in re.findall(r'og:image" content="https://pstlf\.co\.kr(/[^"]+)"', s):
        check((ROOT / img.lstrip('/')).exists(), f'{rel}: og:image 파일 없음 {img}')
    check('og.png' not in s and 'og-bond.png' not in s and 'og-tarot.png' not in s, f'{rel}: 예전 공유 이미지 참조')
    for m in re.findall(r'/assets/site\.(?:css|js)\?v=[0-9a-f]+', s): versions.add(m)
    check(not re.search(r'/assets/site\.(css|js)"', s), f'{rel}: 버전 없는 assets 주소')
    has_ads = 'ca-pub-8262915217195031' in s
    if rel in ('privacy.html', '404.html'):
        check(not has_ads, f'{rel}: 광고 코드가 있으면 안 됨')
    else:
        check(has_ads, f'{rel}: 애드센스 코드 없음')
    tc = TagCheck(); tc.feed(s)
    real = [e for e in tc.errors if not any(x in e for x in ('<p>', '</p>', 'svg', 'g>'))]
    check(not real and not [t for t in tc.stack if t not in ('html','body')], f'{rel}: 태그 짝 오류 {real[:3]} 남은 {tc.stack[-3:]}')
    for href in re.findall(r'href="(/[^"#?]*)', s):
        t = ROOT / href.lstrip('/')
        if href.endswith('/'): t = t / 'index.html'
        check(t.exists(), f'{rel}: 깨진 링크 {href}')
check(len({v.split('?')[0] + v.split('?')[1] for v in versions}) == 2, f'assets 버전이 여러 개: {versions}')
for tp in ['past-life/index.html', 'bond/index.html', 'tarot/index.html', 'tarot/2027/index.html']:
    check('PartnersCoupang.G' in (ROOT / tp).read_text(encoding='utf-8'), f'{tp}: 쿠팡 배너 없음')
for need in ['CNAME', 'ads.txt', 'robots.txt', 'sitemap.xml', 'favicon.svg', 'apple-touch-icon.png', 'share.png', 'share-bond.png', 'share-tarot.png', 'share-2027.png']:
    check((ROOT / need).exists(), f'파일 없음: {need}')
check((ROOT / 'CNAME').read_text().strip() == 'pstlf.co.kr', 'CNAME 내용')
for tp in ['index.html', 'past-life/index.html']:
    t = (ROOT / tp).read_text(encoding='utf-8')
    m = re.search(r'<svg class="mirror-rim".*?</svg>', t, re.S)
    check(m and 'width="0"' in m.group(0) and 'fill="none"' in m.group(0) and 'fill="#C8A45E"' in m.group(0), f'{tp}: 거울 테두리 기본 색')
    m = re.search(r'<svg class="mirror-sky".*?</svg>', t, re.S)
    check(m and 'width="0"' in m.group(0) and 'class="ring" fill="none"' in m.group(0), f'{tp}: 거울 속 기본 색')
check('pub-8262915217195031' in (ROOT / 'ads.txt').read_text(), 'ads.txt 내용')
for loc in re.findall(r'<loc>https://pstlf\.co\.kr(/[^<]*)</loc>', (ROOT / 'sitemap.xml').read_text()):
    t = ROOT / loc.lstrip('/')
    if loc.endswith('/'): t = t / 'index.html'
    check(t.exists(), f'sitemap 주소 없음: {loc}')
check("kakaoKey: '9c80b443d515192669720d8220b878d5'" in (ROOT / 'assets/site.js').read_text(), '카카오 키')
r = subprocess.run(['node', '-e', "new Function(require('fs').readFileSync(process.argv[1],'utf8'))", str(ROOT / 'assets/site.js')], capture_output=True)
check(r.returncode == 0, 'site.js 문법 오류')
for tp in ['past-life/index.html', 'bond/index.html', 'tarot/index.html', 'tarot/2027/index.html', 'index.html']:
    for i, js in enumerate(re.findall(r'<script>(.*?)</script>', (ROOT / tp).read_text(encoding='utf-8'), re.S)):
        r = subprocess.run(['node', '-e', 'new Function(process.argv[1])', js], capture_output=True, text=True)
        check(r.returncode == 0, f'{tp} 스크립트 {i} 문법 오류 {r.stderr[:200]}')

ny_src = (ROOT / 'tarot/2027/index.html').read_text(encoding='utf-8')
check(ny_src.count('window.NY_CARDS = [') == 1 and ny_src.count('window.NY_TEXT = [') == 1, '신년 타로: 카드 데이터가 채워지지 않음')
check('<loc>https://pstlf.co.kr/tarot/2027/</loc>' in (ROOT / 'sitemap.xml').read_text(), 'sitemap: 신년 타로 없음')
for f in sorted((ROOT / 'tarot/cards').glob('*/index.html')):
    t = f.read_text(encoding='utf-8')
    check('id="y2027"' in t and t.count('<dt>상반기</dt>') == 1 and 'href="/tarot/2027/"' in t, f'{f.parent.name}: 2027년 풀이 없음')
for tp in ['index.html', 'past-life/index.html', 'bond/index.html', 'tarot/index.html']:
    check('href="/tarot/2027/"' in (ROOT / tp).read_text(encoding='utf-8'), f'{tp}: 신년 타로 링크 없음')

for f in html_files:
    rel = str(f.relative_to(ROOT)); s = f.read_text(encoding='utf-8')
    meta = dict(re.findall(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"', s))
    for k in ['og:title', 'og:description', 'og:site_name', 'og:url', 'og:image', 'twitter:card']:
        check(meta.get(k), f'{rel}: 공유 정보 {k} 없음')
    img = ROOT / meta.get('og:image', '').replace('https://pstlf.co.kr/', '')
    if check(meta.get('og:image', '').startswith('https://pstlf.co.kr/') and img.is_file(), f'{rel}: 공유 그림 {meta.get("og:image")}'):
        w, h = struct.unpack('>II', img.read_bytes()[16:24])
        check((str(w), str(h)) == (meta.get('og:image:width'), meta.get('og:image:height')), f'{rel}: 공유 그림 크기 {w}x{h}가 적힌 크기와 다름')
        check(img.stat().st_size < 1_000_000, f'{rel}: 공유 그림이 1MB를 넘음')
    if rel != '404.html':
        want = SITE + '/' + rel.replace('index.html', '')
        check(meta.get('og:url') == want and f'rel="canonical" href="{want}"' in s, f'{rel}: 공유 주소 {meta.get("og:url")} (기대 {want})')
notes.append(f'공유 미리보기 정보 {len(html_files)}개 페이지 확인')

# ── B·C. 브라우저 점검 ─────────────────────────────
srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
BLOCK = ['**/fonts.g*/**', '**/ads-partners.coupang.com/**', '**/pagead2.googlesyndication.com/**', '**/kakaocdn.net/**']
page_errors = []

def make_ctx(b, w, h, mobile=True):
    ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if mobile else 1,
                        is_mobile=mobile, has_touch=mobile, permissions=['clipboard-read', 'clipboard-write'])
    for pat in BLOCK: ctx.route(pat, lambda r: r.abort())
    return ctx

def open_page(ctx, url, label=None):
    pg = ctx.new_page()
    label = label or url
    pg.on('pageerror', lambda e: page_errors.append(f'{label}: {e}'))
    pg.on('console', lambda m: m.type == 'error' and 'net::ERR' not in m.text and 'Failed to load resource' not in m.text
          and page_errors.append(f'{label} console: {m.text}'))
    pg.goto(B + url)
    return pg

def visible_text_ok(pg, label):
    t = pg.inner_text('body')
    for bad in ['undefined', 'NaN', '{X}', '{Y}', '{m}', 'null']:
        check(bad not in t, f'{label}: 화면에 "{bad}" 표시')

def wait_result(pg, ms=5200):
    pg.wait_for_selector('#result:not([hidden])', timeout=ms)
    pg.wait_for_timeout(300)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])

        # B. 모든 페이지 × 화면 크기: 오류·가로 넘침
        urls = ['/' + str(f.relative_to(ROOT)).replace('index.html', '') for f in html_files]
        for (w, h, mobile, tag) in [(320, 640, True, '320'), (390, 844, True, '390'), (1280, 800, False, 'pc')]:
            ctx = make_ctx(b, w, h, mobile)
            for u in urls:
                pg = open_page(ctx, u, f'[{tag}] {u}')
                pg.wait_for_timeout(150)
                sw = pg.evaluate('document.documentElement.scrollWidth'); cw = pg.evaluate('document.documentElement.clientWidth')
                check(sw <= cw + 1, f'[{tag}] {u}: 가로로 넘침 {sw}>{cw}')
                if u in ('/tarot/', '/tarot/2027/'):
                    widths = pg.evaluate("""() => { document.getElementById('deck').scrollIntoView({block: 'center'}); const d = document.getElementById('deck').getBoundingClientRect(); const span = {};
                      for (let x = Math.max(0, d.left); x < Math.min(innerWidth, d.right); x += 2) for (let y = d.top; y < d.bottom; y += 4) {
                        const el = document.elementFromPoint(x, y); const c = el && el.closest('.tcard'); if (!c) continue;
                        const k = c.dataset.card; span[k] = span[k] || [1e9, -1e9]; span[k][0] = Math.min(span[k][0], x); span[k][1] = Math.max(span[k][1], x); }
                      return Object.values(span).map(s => Math.round(s[1] - s[0])); }""")
                    need = {'320': 26, '390': 36, 'pc': 40}[tag]
                    check(len(widths) == 7 and min(widths) >= need, f'[{tag}] {u}: 카드별 누를 수 있는 폭 {sorted(widths)} (최소 {need}px)')
                    notes.append(f'[{tag}] {u} 카드별 누를 수 있는 폭 {sorted(widths)}')
                hd = pg.evaluate("(() => { const h = document.querySelector('.site-head'); return h ? h.getBoundingClientRect().height : 0 })()")
                check(hd < 70, f'[{tag}] {u}: 상단 메뉴가 두 줄로 깨짐 ({hd:.0f}px)')
                pg.close()
            ctx.close()
        notes.append(f'페이지 {len(urls)}개 × 화면 3종 열기 완료')

        ctx = make_ctx(b, 390, 844)

        # 홈
        pg = open_page(ctx, '/', 'hub')
        check(pg.locator('.test').count() == 4, 'hub: 테스트 4개')
        check(pg.locator('.test').first.get_attribute('href') == '/tarot/2027/', 'hub: 신년 타로가 맨 위')
        check(pg.locator('.read-list li').count() == 5, 'hub: 읽을거리 5개')
        check(pg.locator('.mirror-rim').is_visible(), 'hub: 거울 테두리')
        pg.goto(B + '/?n=%EA%B9%80%ED%95%98%EB%8A%98&s=1yv0xfq'); pg.wait_for_url('**/past-life/**'); wait_result(pg)
        check(pg.inner_text('#rTitle').startswith('탐정 소설을 쓰던 무명 작가'), 'hub: 예전 공유 링크 이동')
        pg.close()

        # 전생 체험
        pg = open_page(ctx, '/past-life/', 'past-life')
        box = pg.locator('.mirror').bounding_box(); rim = pg.locator('.mirror-rim').bounding_box()
        check(rim['width'] > box['width'] * 1.2 and abs((rim['x'] + rim['width'] / 2) - (box['x'] + box['width'] / 2)) < 2, 'past-life: 테두리 위치')
        cases = [('', '19980417', '이름을 입력해 주세요.'), ('김하늘', '', '생년월일을 입력해 주세요. 예: 19980417'),
                 ('김하늘', '1998041', '생년월일을 숫자 8자리로 입력해 주세요. 예: 19980417'),
                 ('김하늘', '19980230', '없는 날짜예요. 생년월일을 다시 확인해 주세요.'),
                 ('김하늘', '18991231', '없는 날짜예요. 생년월일을 다시 확인해 주세요.'),
                 ('김하늘', '20991231', '생년월일은 오늘 이전 날짜로 입력해 주세요.')]
        for name, birth, msg in cases:
            pg.fill('#name', name); pg.fill('#birth', ''); pg.type('#birth', birth); pg.click('button[type=submit]')
            pg.wait_for_timeout(100)
            check(pg.inner_text('#error') == msg, f'past-life: "{name}/{birth}" 오류 문구 → {pg.inner_text("#error")!r}')
            check(not pg.is_visible('#gazing'), f'past-life: 잘못된 입력인데 진행됨 {birth}')
        pg.fill('#birth', ''); pg.type('#birth', '1998-04-17'); check(pg.input_value('#birth') == '1998.04.17', 'past-life: 하이픈 입력 정리')
        pg.fill('#birth', ''); pg.type('#birth', '19980417123'); check(pg.input_value('#birth') == '1998.04.17', 'past-life: 8자리 초과 자르기')
        pg.fill('#name', '김하늘'); pg.click('button[type=submit]')
        pg.wait_for_selector('#gazing:not([hidden])', timeout=1000)
        wait_result(pg)
        check(pg.inner_text('#rTitle').startswith('탐정 소설을 쓰던 무명 작가'), 'past-life: 기존 결과 유지')
        for fid in ['rOwner', 'rEra', 'rPlace', 'rCount', 'rRare', 'rStory', 'rEnd', 'rTrace', 'rBond', 'rColor', 'rNumber', 'rSign']:
            check(pg.inner_text('#' + fid).strip() != '', f'past-life: {fid} 비어 있음')
        visible_text_ok(pg, 'past-life 결과')
        check('?n=' in pg.url and '&s=' in pg.url, 'past-life: 주소에 결과 담기')
        shared_url = pg.url
        # 공유 창
        pg.click('#shareBtn'); pg.wait_for_timeout(350)
        check(pg.is_visible('.share-panel'), '공유 창 열림')
        kinds = pg.evaluate("[...document.querySelectorAll('.share-item')].filter(e=>!e.hidden).map(e=>e.dataset.kind)")
        check(kinds[:6] == ['kakao', 'sms', 'x', 'threads', 'facebook', 'copy'], f'공유 버튼 구성 {kinds}')
        hrefs = pg.evaluate("Object.fromEntries([...document.querySelectorAll('a.share-item')].map(e=>[e.dataset.kind, e.href]))")
        enc = re.escape('n%3D')
        check(hrefs['sms'].startswith('sms:?&body=') and '%3Fn%3D' in hrefs['sms'], f'공유 sms 링크 {hrefs["sms"][:80]}')
        check(hrefs['x'].startswith('https://twitter.com/intent/tweet?text=') and '&url=' in hrefs['x'], '공유 X 링크')
        check(hrefs['threads'].startswith('https://www.threads.net/intent/post?text='), '공유 스레드 링크')
        check(hrefs['facebook'].startswith('https://www.facebook.com/sharer/sharer.php?u='), '공유 페이스북 링크')
        check(pg.evaluate("document.querySelector('[data-kind=sms]').target") == '', '공유 sms는 새 탭 없이')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
        check(not pg.is_visible('.share-panel'), '공유 창 ESC로 닫힘')
        pg.click('#shareBtn'); pg.wait_for_timeout(300); pg.mouse.click(195, 60); pg.wait_for_timeout(150)
        check(not pg.is_visible('.share-panel'), '공유 창 바깥 눌러 닫힘')
        pg.click('#shareBtn'); pg.wait_for_timeout(300); pg.click('[data-kind=copy]'); pg.wait_for_timeout(400)
        clip = pg.evaluate('navigator.clipboard.readText()')
        check('탐정 소설을 쓰던 무명 작가' in clip and '?n=' in clip, f'복사하기 내용 {clip[:60]!r}')
        check(pg.is_visible('#toast.is-on'), '복사 알림 표시')
        check(pg.evaluate("document.documentElement.style.overflow") == '', '공유 창 닫힌 뒤 스크롤 복구')
        pg.click('#shareBtn'); pg.wait_for_timeout(300); pg.click('[data-kind=kakao]'); pg.wait_for_timeout(300)
        check(pg.is_visible('#toast.is-on'), '카카오 SDK 못 불러올 때 안내 문구')
        pg.click('#againBtn'); pg.wait_for_timeout(200)
        check(pg.is_visible('#intro') and '?' not in pg.url and pg.input_value('#name') == '', 'past-life: 다시 하기 초기화')
        pg.fill('#name', '김하늘'); pg.type('#birth', '980417'); pg.click('button[type=submit]'); wait_result(pg)
        check(pg.inner_text('#rTitle').startswith('탐정 소설을 쓰던 무명 작가'), 'past-life: 6자리 입력 같은 결과')
        pg.close()
        # 친구가 받은 링크
        ctx2 = make_ctx(b, 390, 844)
        pg = open_page(ctx2, shared_url.replace(B, ''), 'past-life shared')
        wait_result(pg, 3000)
        check(pg.is_visible('#sharedNote') and pg.is_visible('#sharedActions') and not pg.is_visible('#ownActions'), 'past-life: 친구 화면 구성')
        check(pg.inner_text('#rLead') == '김하늘님은 전생에', 'past-life: 친구 화면 문구')
        pg.click('#mineBtn'); pg.wait_for_timeout(200)
        check(pg.is_visible('#intro'), 'past-life: 내 전생도 보기')
        for bad in ['?n=%EA%B9%80&s=ZZZ', '?s=abc', '?n=x&s=zzzzzzzzz', '?n=<b>x</b>&s=abc']:
            pg.goto(B + '/past-life/' + bad); pg.wait_for_timeout(250)
            if '<b>' in bad:
                check(pg.locator('#rOwner b').count() == 0, 'past-life: 이름에 태그 넣어도 글자로만 표시')
            else:
                check(pg.is_visible('#intro'), f'past-life: 잘못된 링크 {bad} 처리')
        pg.close(); ctx2.close()
        # 결과 다양성
        pg = open_page(ctx, '/past-life/', 'past-life many')
        titles = set()
        seeds = pg.evaluate("""() => { const out = []; for (let i = 0; i < 120; i++) out.push(window.Site.hash('사람' + i + '|1990-01-' + String(i % 28 + 1).padStart(2,'0')).toString(36)); return out; }""")
        for sd in seeds:
            pg.goto(B + '/past-life/?n=test&s=' + sd)
            pg.wait_for_selector('#result:not([hidden])', timeout=3000)
            titles.add(pg.inner_text('#rTitle'))
            visible_text_ok(pg, 'past-life 여러 결과')
        notes.append(f'전생 결과 120번 중 서로 다른 전생 {len(titles)}가지')
        pg.close()

        # 인연 궁합
        pg = open_page(ctx, '/bond/', 'bond')
        for a, da, bb, db, msg in [('', '', '이바다', '', '내 이름을 입력해 주세요.'), ('김하늘', '', '', '', '상대 이름을 입력해 주세요.'),
                                   ('김하늘', '1998', '이바다', '', '내 생년월일을 숫자 8자리로 입력해 주세요. 예: 19980417'),
                                   ('김하늘', '', '이바다', '20991231', '상대 생년월일은 오늘 이전 날짜로 입력해 주세요.')]:
            pg.fill('#nameA', a); pg.fill('#birthA', ''); pg.type('#birthA', da) if da else None
            pg.fill('#nameB', bb); pg.fill('#birthB', ''); pg.type('#birthB', db) if db else None
            pg.click('button[type=submit]'); pg.wait_for_timeout(100)
            check(pg.inner_text('#error') == msg, f'bond: 오류 문구 → {pg.inner_text("#error")!r} (기대 {msg})')
        pg.fill('#nameA', '김하늘'); pg.fill('#birthA', ''); pg.fill('#nameB', '이바다'); pg.fill('#birthB', '')
        check(pg.inner_text('#bubbleA') == '김하늘' and pg.inner_text('#bubbleB') == '이바다', 'bond: 이름이 원 안에 표시')
        pg.click('button[type=submit]'); wait_result(pg)
        t1, s1 = pg.inner_text('#rTitle'), pg.inner_text('#rScore')
        check(t1.startswith('함께 산천을 누비던 화랑 동무') and s1 == '94%', f'bond: 기존 결과 유지 {t1} {s1}')
        pg.wait_for_timeout(1000)
        check(pg.inner_text('#knot').replace('\n', '') == '94%', f'bond: 매듭 숫자 {pg.inner_text("#knot")!r}')
        visible_text_ok(pg, 'bond 결과')
        bond_url = pg.url
        pg.click('#againBtn'); pg.fill('#nameA', '이바다'); pg.fill('#nameB', '김하늘'); pg.click('button[type=submit]'); wait_result(pg)
        check(pg.inner_text('#rTitle') == t1 and pg.inner_text('#rScore') == s1, 'bond: 순서 바꿔도 같은 결과')
        pg.click('#againBtn'); pg.fill('#nameA', '김하늘'); pg.type('#birthA', '19980417'); pg.fill('#nameB', '이바다'); pg.type('#birthB', '19970101')
        pg.click('button[type=submit]'); wait_result(pg); visible_text_ok(pg, 'bond 생일 포함')
        # 14가지 인연이 모두 나오는지, 역할 표시가 맞는지
        seen = {}
        for i in range(160):
            pg.goto(B + f'/bond/?a=A{i}&b=B{i}&s={b36((i * 2654435761) % 4294967296)}')
            pg.wait_for_selector('#result:not([hidden])', timeout=3000)
            t = pg.inner_text('#rTitle'); roles_vis = pg.is_visible('#rRoles')
            seen.setdefault(t, roles_vis)
            visible_text_ok(pg, f'bond {t}')
            if len(seen) == 14: break
        check(len(seen) == 14, f'bond: 나온 인연 종류 {len(seen)}/14')
        role_titles = [t for t, v in seen.items() if v]
        check(len(role_titles) == 4, f'bond: 역할 표시 인연 수 {len(role_titles)} (기대 4)')
        pg.close()
        ctx2 = make_ctx(b, 390, 844)
        pg = open_page(ctx2, bond_url.replace(B, ''), 'bond shared'); wait_result(pg, 3000)
        check(pg.is_visible('#sharedNote') and pg.inner_text('#rTitle') == t1, 'bond: 친구 화면')
        pg.click('#mineBtn'); pg.wait_for_timeout(200); check(pg.is_visible('#form'), 'bond: 우리 인연도 보기')
        check(not pg.is_visible('#sharedNote'), 'bond: 우리 인연도 보기를 누르면 친구 안내가 사라짐')
        pg.close(); ctx2.close()

        # 타로
        ctx3 = make_ctx(b, 390, 844)
        pg = open_page(ctx3, '/tarot/', 'tarot')
        check(pg.locator('.tcard').count() == 7, 'tarot: 카드 7장 펼침')
        ids = pg.evaluate("[...document.querySelectorAll('.tcard')].map(e=>e.dataset.card)")
        check(len(set(ids)) == 7, 'tarot: 겹치지 않는 7장')
        hit = pg.evaluate("""() => { const d = document.getElementById('deck').getBoundingClientRect(); const got = new Set();
            for (let x = d.left; x < d.right; x += 4) for (let y = d.top; y < d.bottom; y += 6) {
              const el = document.elementFromPoint(x, y); const c = el && el.closest('.tcard'); if (c) got.add(c.dataset.card); }
            return got.size; }""")
        check(hit == 7, f'tarot: 손가락으로 누를 수 있는 카드 {hit}/7')
        pg.locator('.tcard').nth(6).click(); pg.wait_for_selector('#result:not([hidden])', timeout=4000)
        card_title = pg.inner_text('#rTitle'); visible_text_ok(pg, 'tarot 결과')
        check('남았어요' in pg.inner_text('#nextNote'), 'tarot: 남은 시간 안내')
        check(re.search(r'\?card=\d+$', pg.url), 'tarot: 주소에 카드 번호')
        tarot_url = pg.url
        pg.reload(); pg.wait_for_timeout(800)
        check(pg.inner_text('#rTitle') == card_title and not pg.is_visible('#sharedNote'), 'tarot: 새로고침해도 내 카드')
        pg.goto(B + '/tarot/'); pg.wait_for_timeout(800)
        check(pg.locator('.tcard').count() == 1 and pg.inner_text('#rTitle') == card_title, 'tarot: 오늘 다시 와도 같은 카드')
        pg.evaluate("localStorage.setItem('pstlf-tarot', JSON.stringify({date:'2000-01-01', card:0}))")
        pg.goto(B + '/tarot/'); pg.wait_for_timeout(500)
        check(pg.locator('.tcard').count() == 7 and not pg.is_visible('#result'), 'tarot: 다음 날 새 카드')
        pg.goto(B + '/tarot/?card=99'); pg.wait_for_timeout(400)
        check(pg.locator('.tcard').count() == 7, 'tarot: 잘못된 카드 번호 처리')
        pg.close(); ctx3.close()
        ctx4 = make_ctx(b, 390, 844)
        pg = open_page(ctx4, tarot_url.replace(B, ''), 'tarot shared'); pg.wait_for_timeout(900)
        check(pg.is_visible('#sharedNote') and pg.inner_text('#rLead') == '친구에게 온 카드는', 'tarot: 친구 화면')
        pg.click('#mineBtn'); pg.wait_for_timeout(400)
        check(pg.locator('.tcard').count() == 7, 'tarot: 친구가 나도 뽑기')
        pg.close(); ctx4.close()
        # 22장 모두 결과 화면
        ctx5 = make_ctx(b, 390, 844); pg = open_page(ctx5, '/tarot/', 'tarot all')
        for i in range(22):
            pg.goto(B + f'/tarot/?card={i}'); pg.wait_for_selector('#result:not([hidden])', timeout=3000)
            visible_text_ok(pg, f'tarot card {i}')
            check(pg.locator('.tcard .tface svg *').count() > 0, f'tarot: {i}번 카드 그림')
        pg.close(); ctx5.close()

        # 신년 타로
        def ny_title(ids):
            def ro(w):
                c = ord(w[-1]); j = (c - 0xAC00) % 28
                return '로' if j in (0, 8) else '으로'
            return f'{words[ids[0]]}에서 {words[ids[1]]}{ro(words[ids[1]])} 가는 해'
        ctx7 = make_ctx(b, 390, 844)
        pg = open_page(ctx7, '/tarot/2027/', 'newyear')
        words = pg.evaluate("window.NY_TEXT.map(t => t.word)")
        check(len(words) == 22 and len(set(words)) == 22, f'newyear: 한 단어 22개가 서로 달라야 함 {len(set(words))}')
        check(pg.locator('.tcard').count() == 7, 'newyear: 카드 7장 펼침')
        ids = pg.evaluate("[...document.querySelectorAll('.tcard')].map(e=>Number(e.dataset.card))")
        check(len(set(ids)) == 7, 'newyear: 겹치지 않는 7장')
        check(pg.locator('.slot.is-next').count() == 1 and pg.locator('.slot').nth(0).evaluate("e => e.classList.contains('is-next')"), 'newyear: 첫 자리 안내')
        check('상반기' in pg.inner_text('#hint'), f'newyear: 첫 안내 문구 {pg.inner_text("#hint")!r}')
        picked = []
        for k, nth in enumerate([6, 5, 4]):
            picked.append(ids[nth]); pg.locator('.tcard').nth(nth).click(); pg.wait_for_timeout(120)
            check(pg.locator('.slot.is-filled').count() == k + 1, f'newyear: {k + 1}번째 카드가 자리에 놓임')
            if k < 2:
                check(pg.locator('.slot').nth(k + 1).evaluate("e => e.classList.contains('is-next')"), f'newyear: {k + 2}번째 자리 안내')
                check(pg.evaluate(f"document.querySelectorAll('.tcard')[{nth}].disabled"), 'newyear: 고른 카드는 다시 못 고름')
        pg.wait_for_selector('#result:not([hidden])', timeout=5000); pg.wait_for_timeout(300)
        check(pg.locator('.scard.is-flipped').count() == 3, 'newyear: 세 장 모두 뒤집힘')
        check(pg.url.endswith('?c=' + '-'.join(map(str, picked))), f'newyear: 주소에 고른 순서 {pg.url}')
        check(pg.inner_text('#rTitle').replace('\n', ' ') == ny_title(picked), f'newyear: 제목 {pg.inner_text("#rTitle")!r} 기대 {ny_title(picked)!r}')
        check(pg.inner_text('#rWords') == ' · '.join(words[i] for i in picked), 'newyear: 키워드 세 개')
        check(re.fullmatch(r'([1-9]|1[0-2])월', pg.inner_text('#rMonth')) is not None, f'newyear: 행운의 달 {pg.inner_text("#rMonth")!r}')
        for k in range(3):
            check(len(pg.inner_text(f'#rText{k}')) > 30 and pg.inner_text(f'#rCard{k}').endswith('카드'), f'newyear: {k}번째 풀이')
        check(pg.locator('#rLinks a').count() == 3, 'newyear: 카드 뜻 링크 3개')
        for href in pg.evaluate("[...document.querySelectorAll('#rLinks a')].map(a=>a.getAttribute('href'))"):
            check((ROOT / href.lstrip('/') / 'index.html').exists(), f'newyear: 깨진 카드 링크 {href}')
        visible_text_ok(pg, 'newyear 결과')
        title_mine = pg.inner_text('#rTitle'); ny_url = pg.url
        pg.click('#shareBtn'); pg.wait_for_timeout(300); pg.click('[data-kind=copy]'); pg.wait_for_timeout(400)
        clip = pg.evaluate('navigator.clipboard.readText()')
        check(ny_title(picked) in clip and '/tarot/2027/?c=' in clip, f'newyear: 복사하기 내용 {clip[:80]!r}')
        pg.reload(); pg.wait_for_timeout(700)
        check(pg.inner_text('#rTitle') == title_mine and not pg.is_visible('#sharedNote'), 'newyear: 새로고침해도 내 카드')
        pg.goto(B + '/tarot/2027/'); pg.wait_for_timeout(700)
        check(pg.locator('.tcard').count() == 0 and pg.inner_text('#rTitle') == title_mine, 'newyear: 다시 와도 같은 세 장')
        pg.click('#againBtn'); pg.wait_for_timeout(300)
        check(pg.locator('.tcard').count() == 7 and not pg.is_visible('#result') and '?' not in pg.url
              and pg.locator('.slot.is-filled').count() == 0, 'newyear: 다른 사람도 뽑아 보기')
        check(pg.evaluate("localStorage.getItem('pstlf-newyear-2027')") in (None, 'null'), 'newyear: 다시 뽑으면 저장 지움')
        pg.close(); ctx7.close()
        ctx8 = make_ctx(b, 390, 844)
        pg = open_page(ctx8, ny_url.replace(B, ''), 'newyear shared'); pg.wait_for_timeout(700)
        check(pg.is_visible('#sharedNote') and pg.inner_text('#rLead') == '친구의 2027년은' and pg.is_visible('#sharedActions'), 'newyear: 친구 화면')
        check(pg.inner_text('#rTitle') == title_mine, 'newyear: 친구도 같은 결과')
        pg.click('#mineBtn'); pg.wait_for_timeout(400)
        check(pg.locator('.tcard').count() == 7, 'newyear: 친구가 나도 뽑기')
        for bad in ['?c=1-1-2', '?c=1-2-99', '?c=abc', '?c=1-2', '?c=<b>1</b>']:
            pg.goto(B + '/tarot/2027/' + bad); pg.wait_for_timeout(300)
            check(pg.locator('.tcard').count() == 7 and not pg.is_visible('#result'), f'newyear: 잘못된 링크 {bad} 처리')
        pg.close(); ctx8.close()
        # 22장 모두 세 자리에 한 번씩, 좁은 화면에서 제목이 넘치지 않는지
        ctx9 = make_ctx(b, 320, 640); pg = open_page(ctx9, '/tarot/2027/', 'newyear all')
        longest = sorted(range(22), key=lambda i: -len(words[i]))
        combos = [(i, (i + 7) % 22, (i + 15) % 22) for i in range(22)] + [(longest[0], longest[1], longest[2]), (longest[1], longest[0], longest[3])]
        for ids3 in combos:
            pg.goto(B + '/tarot/2027/?c=' + '-'.join(map(str, ids3))); pg.wait_for_selector('#result:not([hidden])', timeout=3000)
            visible_text_ok(pg, f'newyear {ids3}')
            check(pg.inner_text('#rTitle').replace('\n', ' ') == ny_title(ids3), f'newyear {ids3}: 제목')
            check(pg.locator('.scard .tface svg *').count() >= 3, f'newyear {ids3}: 카드 그림')
            over = pg.evaluate("(() => { const t = document.getElementById('rTitle'); return [...t.querySelectorAll('.nw')].some(s => s.getBoundingClientRect().right > t.getBoundingClientRect().right + 1); })()")
            check(not over, f'newyear {ids3}: 320px에서 제목이 넘침')
            sw = pg.evaluate('document.documentElement.scrollWidth'); check(sw <= 321, f'newyear {ids3}: 가로로 넘침 {sw}')
        notes.append(f'신년 타로 조합 {len(combos)}가지 확인')
        pg.close(); ctx9.close()

        # 카드 의미 페이지
        pg = open_page(ctx, '/tarot/cards/', 'cards')
        check(pg.locator('.card-grid a').count() == 22, 'cards: 22장 목록')
        for slug in re.findall(r'href="/tarot/cards/([a-z-]+)/"', pg.content())[:22]:
            pg.goto(B + f'/tarot/cards/{slug}/'); pg.wait_for_timeout(80)
            check(pg.locator('.pager a').count() == 2 and pg.locator('.card-face svg *').count() > 0, f'card {slug}: 구성')
            check(len(pg.inner_text('main')) > 700, f'card {slug}: 글 분량 {len(pg.inner_text("main"))}')
            visible_text_ok(pg, f'card {slug}')
        pg.close()
        # 읽을거리
        pg = open_page(ctx, '/read/', 'read'); links = re.findall(r'href="(/read/[a-z-]+/)"', pg.content())
        check(len(set(links)) == 5, 'read: 글 5편')
        for l in sorted(set(links)):
            pg.goto(B + l); pg.wait_for_timeout(80)
            n = len(pg.inner_text('main')); check(n > 1200, f'{l}: 글 분량 {n}')
        pg.close()

        # 공유 창: 버튼마다 담기는 글과 주소, 카카오톡 카드, 친구가 링크를 눌렀을 때
        MOCK = """
        window.__kakao = []; window.__navshare = [];
        window.Kakao = { _i: false, isInitialized: function () { return this._i; }, init: function (k) { this._i = true; window.__kakaoKey = k; },
          Share: { sendDefault: function (o) { window.__kakao.push(o); } } };
        Object.defineProperty(navigator, 'share', { configurable: true, value: function (d) { window.__navshare.push(d); return Promise.resolve(); } });
        """
        def bar_on(pg):
            return pg.evaluate("(() => { const e = document.querySelector('.cta-bar'); return !!e && e.classList.contains('is-on') && getComputedStyle(e).visibility === 'visible'; })()")

        def share_ctx():
            c = make_ctx(b, 390, 844); c.add_init_script(MOCK); return c

        def open_sheet(pg):
            pg.click('#shareBtn' if pg.is_visible('#shareBtn') else '#shareBtn2'); pg.wait_for_timeout(300)
            return pg.evaluate("Object.fromEntries([...document.querySelectorAll('.share-item')].filter(e => !e.hidden).map(e => [e.dataset.kind, e.href || '']))")

        def inspect_share(pg, path, img, label):
            items = open_sheet(pg)
            check(list(items) == ['kakao', 'sms', 'x', 'threads', 'facebook', 'copy', 'more'], f'{label}: 공유 버튼 {list(items)}')
            text, url = unquote(items['sms'].split('body=', 1)[1]).rsplit('\n', 1)
            check(url == pg.url and url.startswith(B + path + '?'), f'{label}: 공유 주소 {url}')
            xq = parse_qs(urlparse(items['x']).query); tq = parse_qs(urlparse(items['threads']).query); fq = parse_qs(urlparse(items['facebook']).query)
            check(xq.get('text') == [text] and xq.get('url') == [url], f'{label}: X 글과 주소')
            check(tq.get('text') == [text + ' ' + url], f'{label}: 스레드 글과 주소')
            check(fq.get('u') == [url], f'{label}: 페이스북 주소')
            check(not any(bad in text for bad in ['undefined', 'null', 'NaN', '{X}', '{Y}']), f'{label}: 공유 글 {text!r}')
            pg.click('[data-kind=kakao]'); pg.wait_for_timeout(200)
            k = pg.evaluate('window.__kakao.pop()')
            if check(k, f'{label}: 카카오톡 공유가 열리지 않음'):
                c = k['content']; bt = k['buttons']
                check(c['description'] == text and c['title'] and c['imageUrl'] == f'{SITE}/{img}' and (c['imageWidth'], c['imageHeight']) == (1200, 600),
                      f'{label}: 카카오톡 카드 {c["title"]} {c["imageUrl"]}')
                check(c['link']['webUrl'] == url == c['link']['mobileWebUrl'] and bt[0]['link']['webUrl'] == url == bt[0]['link']['mobileWebUrl'],
                      f'{label}: 카카오톡 카드와 결과 보기 버튼 주소')
                check([x['title'] for x in bt] == ['결과 보기', '나도 해 보기'] and bt[1]['link']['webUrl'] == B + path == bt[1]['link']['mobileWebUrl'],
                      f'{label}: 카카오톡 나도 해 보기 버튼 {bt[1]["link"]["webUrl"]}')
            check(not pg.is_visible('.share-panel'), f'{label}: 카카오톡 누른 뒤 공유 창 닫힘')
            open_sheet(pg); pg.click('[data-kind=copy]'); pg.wait_for_timeout(300)
            check(pg.evaluate('navigator.clipboard.readText()') == text + '\n' + url, f'{label}: 복사하기 내용')
            open_sheet(pg); pg.click('[data-kind=more]'); pg.wait_for_timeout(200)
            d = pg.evaluate('window.__navshare.pop()')
            check(d and d['url'] == url and d['text'] == text and d['title'], f'{label}: 더보기 공유')
            return text, url

        def run_past(pg):
            pg.fill('#name', '김하늘'); pg.type('#birth', '19980417'); pg.click('button[type=submit]'); wait_result(pg)
        def run_bond(pg):
            pg.fill('#nameA', '김하늘'); pg.fill('#nameB', '이바다'); pg.click('button[type=submit]'); wait_result(pg)
        def run_tarot(pg):
            pg.locator('.tcard').nth(6).click(); pg.wait_for_selector('#result:not([hidden])', timeout=5000); pg.wait_for_timeout(300)
        def run_ny(pg):
            for n in (6, 5, 4): pg.locator('.tcard').nth(n).click(); pg.wait_for_timeout(150)
            pg.wait_for_selector('#result:not([hidden])', timeout=6000); pg.wait_for_timeout(300)
        for path, run, img in [('/past-life/', run_past, 'share.png'), ('/bond/', run_bond, 'share-bond.png'),
                               ('/tarot/', run_tarot, 'share-tarot.png'), ('/tarot/2027/', run_ny, 'share-2027.png')]:
            c1 = share_ctx(); pg = open_page(c1, path, f'share {path}'); pg.wait_for_timeout(300); run(pg)
            title = pg.inner_text('#rTitle')
            check(not pg.is_visible('#sharedNote') and not pg.is_visible('#mineTopBtn'), f'공유 {path}: 내 결과에는 친구 안내 없음')
            for y in (300, 700, 1100):
                pg.evaluate(f'window.scrollTo(0, {y})'); pg.wait_for_timeout(120)
                check(not bar_on(pg), f'공유 {path}: 내 결과에서 아래 버튼이 뜸 ({y}px)')
            pg.evaluate('window.scrollTo(0, 0)')
            text, url = inspect_share(pg, path, img, f'공유 {path}')
            check(pg.evaluate('window.__kakaoKey') == '9c80b443d515192669720d8220b878d5', f'공유 {path}: 카카오 키')
            pg.close(); c1.close()
            c2 = share_ctx(); pg = open_page(c2, url.replace(B, ''), f'share friend {path}')
            pg.wait_for_selector('#result:not([hidden])', timeout=6000); pg.wait_for_timeout(500)
            check(pg.inner_text('#rTitle') == title and pg.is_visible('#sharedNote') and pg.is_visible('#mineBtn'), f'공유 {path}: 친구가 링크를 열면 같은 결과')
            text2, url2 = inspect_share(pg, path, img, f'공유 {path} 친구 화면')
            check(url2 == url, f'공유 {path}: 친구가 다시 공유한 주소가 다름')
            check(not text2.startswith('오늘 내 '), f'공유 {path}: 친구 카드를 내 카드라고 공유함 {text2!r}')
            pg.close(); c2.close()
            # 친구 화면: 첫 화면의 '나도 해 보기', 읽는 동안 아래에 뜨는 버튼, 누르면 내 테스트 시작
            c3 = share_ctx(); pg = open_page(c3, url.replace(B, ''), f'friend cta {path}')
            pg.wait_for_selector('#result:not([hidden])', timeout=6000); pg.wait_for_timeout(500)
            tb = pg.locator('#mineTopBtn').bounding_box()
            check(pg.is_visible('#mineTopBtn') and tb['y'] + tb['height'] <= 844, f'공유 {path}: 맨 위 나도 하기 버튼이 첫 화면에 없음')
            check(not bar_on(pg), f'공유 {path}: 처음부터 아래 버튼이 뜸')
            top_bottom = pg.evaluate("document.getElementById('sharedNote').getBoundingClientRect().bottom + scrollY")
            pg.evaluate(f'window.scrollTo(0, {top_bottom + 40})'); pg.wait_for_timeout(400)
            bar_label = pg.evaluate("document.querySelector('.cta-bar button').textContent")
            check(bar_on(pg) and bar_label == pg.inner_text('#mineBtn'), f'공유 {path}: 읽는 동안 아래 버튼 {bar_on(pg)} {bar_label!r}')
            check(pg.evaluate("document.body.classList.contains('has-cta-bar')"), f'공유 {path}: 알림 위치 조정 안 됨')
            pg.evaluate("document.getElementById('sharedActions').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(400)
            check(not bar_on(pg), f'공유 {path}: 결과 아래 버튼과 겹쳐 뜸')
            pg.evaluate(f'window.scrollTo(0, {top_bottom + 40})'); pg.wait_for_timeout(400)
            pg.click('.cta-bar button'); pg.wait_for_timeout(500)
            started = {'/past-life/': "!document.getElementById('intro').hidden",
                       '/bond/': "!document.getElementById('form').hidden",
                       '/tarot/': "document.querySelectorAll('.tcard').length === 7",
                       '/tarot/2027/': "document.querySelectorAll('.tcard').length === 7"}[path]
            check(pg.evaluate(started) and not pg.is_visible('#sharedNote') and '?' not in pg.url, f'공유 {path}: 아래 버튼을 누르면 내 테스트 시작')
            check(not bar_on(pg) and pg.evaluate('scrollY') < 5, f'공유 {path}: 누른 뒤 맨 위로, 아래 버튼 사라짐')
            pg.close(); c3.close()
            c4 = make_ctx(b, 320, 640); pg = open_page(c4, url.replace(B, ''), f'friend 320 {path}')
            pg.wait_for_selector('#result:not([hidden])', timeout=6000); pg.wait_for_timeout(400)
            tb = pg.locator('#mineTopBtn').bounding_box()
            check(tb['y'] + tb['height'] <= 640 and tb['x'] + tb['width'] <= 320 - 19, f'공유 {path}: 320px 맨 위 버튼 위치 {tb}')
            check(pg.evaluate('document.documentElement.scrollWidth') <= 321, f'공유 {path}: 320px 친구 화면 가로로 넘침')
            pg.click('#mineTopBtn'); pg.wait_for_timeout(500)
            check(pg.evaluate(started) and not pg.is_visible('#sharedNote'), f'공유 {path}: 맨 위 버튼을 누르면 내 테스트 시작')
            pg.close(); c4.close()
            notes.append(f'공유 {path}: {text}  →  {url.replace(B, SITE)}')

        # 화면 사진
        ctx6 = make_ctx(b, 390, 844)
        for u, name in [('/', 'hub'), ('/past-life/', 'past'), ('/bond/', 'bond'), ('/tarot/', 'tarot'), ('/tarot/2027/', 'newyear'), ('/about/', 'about'), ('/404.html', '404')]:
            pg = open_page(ctx6, u, name); pg.wait_for_timeout(500)
            pg.screenshot(path=str(OUT / f'{name}.png')); pg.close()
        ctx6.close()
        ctxp = make_ctx(b, 320, 640)
        for u, name in [('/past-life/', 'past-320'), ('/bond/', 'bond-320')]:
            pg = open_page(ctxp, u, name); pg.wait_for_timeout(500); pg.screenshot(path=str(OUT / f'{name}.png'), full_page=False); pg.close()
        ctxd = make_ctx(b, 1280, 800, mobile=False)
        pg = open_page(ctxd, '/past-life/', 'pc'); pg.wait_for_timeout(500); pg.screenshot(path=str(OUT / 'pc.png')); pg.close()
        b.close()
finally:
    srv.terminate()

fails.extend(page_errors)
print('\n'.join(notes))
print(f'문제 {len(fails)}건')
for f in fails: print(' -', f)
