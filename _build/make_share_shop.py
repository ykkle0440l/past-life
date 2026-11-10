"""상품 모음 공유 이미지(share-shop.png, 1200x600) 만들기

    python3 _build/make_share_shop.py

카카오톡 같은 곳에 /shop/ 링크를 붙였을 때 보이는 그림이에요. 문구를 바꿀 때만 다시 실행해요.
(Python Playwright, Chromium 필요)
"""
import os, pathlib, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build import SHOP_BAG

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = '/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None

nums = ''.join(f'<span class="n c{i % 4}"><b>{n}<small>번</small></b></span>' for i, n in enumerate([3, 12, 27]))

HTML = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1200px; height: 600px; overflow: hidden; display: flex; align-items: center; justify-content: center; gap: 70px;
  font-family: 'Noto Sans CJK KR', 'Noto Sans KR', sans-serif; color: #4A3A33;
  background: radial-gradient(circle at 8% 10%, #FFE3D6 0, rgba(255,227,214,0) 330px),
    radial-gradient(circle at 95% 18%, #E2F3EA 0, rgba(226,243,234,0) 300px),
    radial-gradient(circle at 75% 95%, #FFF0C9 0, rgba(255,240,201,0) 380px), #FFF7EF; }}
.bag svg {{ width: 300px; height: 300px; display: block; }}
h1 {{ font-size: 84px; font-weight: 900; letter-spacing: -2px; line-height: 1.15; }}
p {{ font-size: 36px; color: #8A776D; margin-top: 16px; font-weight: 500; }}
.row {{ display: flex; gap: 16px; margin-top: 34px; }}
.n {{ width: 104px; height: 104px; border-radius: 50%; display: grid; place-items: center; font-size: 42px; font-weight: 900; background: #FFE7A0; }}
.n small {{ font-size: 20px; }}
.c1 {{ background: #CDEBDD; }} .c2 {{ background: #FFD6DE; }} .c3 {{ background: #E3DAFA; }}
</style></head><body>
<div class="bag">{SHOP_BAG}</div>
<div><h1>영상 속<br>상품 모음</h1><p>영상에서 본 번호로 바로 찾기</p><div class="row">{nums}</div></div>
</body></html>'''

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1200, 'height': 600}, device_scale_factor=1)
    pg.set_content(HTML)
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(ROOT / 'share-shop.png'))
    b.close()
print('share-shop.png 만들었어요')
