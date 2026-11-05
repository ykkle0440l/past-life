"""2027 신년 타로 공유 이미지(share-2027.png, 1200x600) 만들기

    python3 _build/make_share_newyear.py

카카오톡, X 같은 곳에 링크를 붙였을 때 보이는 그림이에요. 한 번만 만들면 되고,
문구를 바꾸고 싶을 때만 다시 실행해요. (Python Playwright, Chromium 필요)
"""
import json, os, pathlib, re, subprocess
from playwright.sync_api import sync_playwright

from content_newyear import YEAR, YEAR_NAME, YEAR_ANIMAL

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = '/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None

# 가운데 카드 그림은 오늘의 타로 페이지의 '태양' 카드를 그대로 써요 (새해 첫 해돋이)
src = (ROOT / 'tarot/index.html').read_text(encoding='utf-8')
rays = re.search(r'function rays\(.*?\n  \}\n', src, re.S).group(0)
card_js = re.search(r"\{ num: 'XIX', ko: '태양'.*?artExtra: function \(\) \{ return (rays\([^)]*\)); \}", src, re.S)
art_base = re.search(r"art: '([^']*)'", card_js.group(0)).group(1)
art = art_base + json.loads(subprocess.run(['node', '-e', rays + f'process.stdout.write(JSON.stringify({card_js.group(1)}))'],
                                           capture_output=True, text=True, check=True).stdout)

stars = ''.join(
    f'<i style="left:{(i * 137) % 1200}px;top:{(i * 263) % 600}px;opacity:{0.25 + (i * 7 % 10) / 14:.2f};'
    f'width:{2 + i % 3}px;height:{2 + i % 3}px"></i>' for i in range(1, 70))

HTML = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1200px; height: 600px; overflow: hidden; position: relative;
  background: radial-gradient(ellipse 60% 70% at 50% 42%, #2b3a69 0%, #1b2547 55%, #141b35 100%);
  font-family: 'Noto Sans CJK KR', sans-serif; color: #E9E4D8; }}
.stars i {{ position: absolute; border-radius: 50%; background: #F4EFE3; }}
.spark {{ position: absolute; color: #C8A45E; font-size: 26px; line-height: 1; }}
.word {{ position: absolute; top: 38px; width: 100%; text-align: center; font-family: 'Noto Serif CJK KR', serif;
  font-size: 27px; letter-spacing: .32em; color: #C8A45E; }}
.cards {{ position: absolute; left: 50%; top: 92px; width: 0; height: 0; }}
.c {{ position: absolute; width: 150px; height: 256px; left: -75px; top: 0; border-radius: 12px; transform-origin: 50% 90%; }}
.back {{ border: 3px solid #C8A45E; background:
    repeating-linear-gradient(45deg, rgba(200,164,94,.13) 0 2px, transparent 2px 11px),
    repeating-linear-gradient(-45deg, rgba(200,164,94,.13) 0 2px, transparent 2px 11px), #1d2747;
  box-shadow: inset 0 0 0 6px #1d2747, inset 0 0 0 7.5px rgba(200,164,94,.55), 0 14px 30px rgba(0,0,0,.5); }}
.back::after {{ content: ''; position: absolute; left: 50%; top: 50%; width: 64px; height: 64px; margin: -32px;
  border-radius: 50%; background: radial-gradient(circle at 36% 30%, #4a5d93, #1d2747 75%);
  box-shadow: 0 0 0 3px #C8A45E, 0 0 0 7px #1d2747, 0 0 0 8.5px rgba(200,164,94,.5); }}
.l {{ transform: translate(-150px, 18px) rotate(-14deg); }}
.r {{ transform: translate(150px, 18px) rotate(14deg); }}
.face {{ z-index: 2; background: #EFE6D2; color: #2B2520; display: flex; flex-direction: column; align-items: center;
  padding: 14px 10px 12px; box-shadow: inset 0 0 0 6px #EFE6D2, inset 0 0 0 7.5px rgba(43,37,32,.55), 0 18px 36px rgba(0,0,0,.55); }}
.face .n {{ font-family: 'Noto Serif CJK KR', serif; color: #B23A2E; font-size: 19px; margin-top: 2px; }}
.face svg {{ flex: 1; width: 104px; fill: none; stroke: #2B2520; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }}
.face .k {{ font-family: 'Noto Serif CJK KR', serif; font-size: 24px; font-weight: 600; word-break: keep-all; }}
.face .e {{ font-size: 12px; color: #6B5E52; margin-top: 2px; }}
h1 {{ position: absolute; top: 392px; width: 100%; text-align: center; font-family: 'Noto Serif CJK KR', serif;
  font-weight: 600; font-size: 66px; letter-spacing: .04em; color: #F4EFE3; }}
p {{ position: absolute; top: 486px; width: 100%; text-align: center; font-size: 25px; color: #C9CEDD; letter-spacing: .02em; }}
p b {{ color: #C8A45E; font-weight: 400; }}
</style></head><body>
<div class="stars">{stars}</div>
<span class="spark" style="left:150px;top:118px">✦</span><span class="spark" style="left:1010px;top:140px;font-size:20px">✦</span>
<span class="spark" style="left:212px;top:430px;font-size:16px">✦</span><span class="spark" style="left:1050px;top:456px">✦</span>
<div class="word">전생 거울</div>
<div class="cards">
  <div class="c back l"></div><div class="c back r"></div>
  <div class="c face"><span class="n">XIX</span><svg viewBox="0 0 100 100">{art}</svg><span class="k">태양</span><span class="e">The Sun</span></div>
</div>
<h1>{YEAR}년 신년 타로</h1>
<p>카드 세 장으로 보는 나의 새해 · <b>{YEAR_NAME} {YEAR_ANIMAL}의 해</b></p>
</body></html>'''

out = ROOT / f'share-{YEAR}.png'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1200, 'height': 600})
    pg.set_content(HTML)
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(out))
    b.close()
print('saved', out)
