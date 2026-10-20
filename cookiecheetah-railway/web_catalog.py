"""หน้าเว็บแคตตาล็อกร้านคุกกี้ — บอทเปิดเองใน service เดิมบน Railway (ไม่ต้อง host เพิ่ม)

GET /            หน้าร้าน (อ่านอย่างเดียว กดแลกในดิสคอร์ด)
GET /img/<ไฟล์>  รูปของ (เก็บใน Volume)
GET /health      ให้ Railway เช็คว่าบอทยังอยู่
"""
import html
import re
from datetime import datetime
from pathlib import Path

from aiohttp import web

IMAGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,40}\.(png|jpe?g|webp|gif)$", re.IGNORECASE)
THAI_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")


def thai_date(dt: datetime) -> str:
    return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.strftime('%H:%M')}"


CSS = """
:root{--bg:#fff8ef;--card:#ffffff;--ink:#3b2a20;--muted:#8a7464;--line:#f0e2d2;--brown:#8b5a2b;
--pink:#f06292;--pink-soft:#fde4ec;--mint:#2fbf8f;--amber:#e6a23c;--grey:#b9aa9c;--chip:#f7ecdf;
--spot:rgba(139,90,43,.07)}
@media (prefers-color-scheme:dark){:root{--bg:#1d1714;--card:#28201b;--ink:#f6ebe0;--muted:#bfa995;
--line:#3a2e26;--brown:#e0a96d;--pink:#ff8ab0;--pink-soft:#3e2430;--chip:#352a22;--spot:rgba(224,169,109,.06)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "IBM Plex Sans Thai","Sarabun",system-ui,sans-serif}
header{position:relative;overflow:hidden;padding:44px 20px 36px;text-align:center;border-bottom:1px solid var(--line);
background-image:radial-gradient(var(--spot) 18%,transparent 19%),radial-gradient(var(--spot) 12%,transparent 13%);
background-size:46px 46px,46px 46px;background-position:0 0,23px 23px}
h1{margin:0;font:600 clamp(28px,6vw,44px)/1.1 "Mitr",sans-serif;color:var(--brown);letter-spacing:.5px}
h1 span{display:inline-block;transform:rotate(-8deg)}
.sub{margin:10px auto 0;max-width:560px;color:var(--muted)}
.cta{display:inline-flex;gap:8px;align-items:center;margin-top:20px;padding:11px 20px;border-radius:999px;
background:var(--pink);color:#fff;text-decoration:none;font-weight:600;box-shadow:0 6px 18px rgba(240,98,146,.28)}
.cta:hover{filter:brightness(1.05)}
nav{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;padding:18px 16px 4px}
nav button{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px 14px;border-radius:999px;
font:inherit;font-size:14px;cursor:pointer}
nav button[aria-pressed=true]{background:var(--brown);border-color:var(--brown);color:#fff}
main{max-width:1120px;margin:0 auto;padding:16px 16px 56px;display:grid;gap:18px;
grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.item{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;display:flex;flex-direction:column}
.pic{aspect-ratio:1/1;background:var(--chip);display:grid;place-items:center;position:relative}
.pic img{width:100%;height:100%;object-fit:contain;image-rendering:auto}
.pic .ph{font-size:64px;opacity:.55}
.state{position:absolute;top:10px;left:10px;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.state.soon{background:var(--amber)}.state.ended,.state.soldout{background:var(--grey)}.state.hot{background:var(--pink)}
.body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:8px;flex:1}
.cat{align-self:flex-start;font-size:12px;color:var(--muted);background:var(--chip);padding:2px 9px;border-radius:999px}
h2{margin:0;font:600 18px/1.3 "Mitr",sans-serif}
.desc{margin:0;color:var(--muted);font-size:14px;white-space:pre-line}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto;padding-top:6px}
.meta span{font-size:12px;border:1px dashed var(--line);padding:2px 8px;border-radius:8px;color:var(--muted)}
.price{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--line);padding:12px 16px}
.price b{font:600 20px "Mitr",sans-serif;color:var(--brown)}
.price small{color:var(--muted);font-size:12px}
.item.off{opacity:.62}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:60px 0}
footer{text-align:center;color:var(--muted);font-size:13px;padding:0 16px 32px}
"""

JS = """
const btns=[...document.querySelectorAll('nav button')];
btns.forEach(b=>b.addEventListener('click',()=>{
  btns.forEach(x=>x.setAttribute('aria-pressed',x===b));
  const c=b.dataset.cat;
  document.querySelectorAll('.item').forEach(el=>{el.hidden=!(c==='*'||el.dataset.cat===c)});
}));
"""

STATE_TEXT = {"soon": "เร็วๆ นี้", "ended": "หมดเวลา", "soldout": "หมดแล้ว", "hot": "ใกล้หมดเวลา"}


def render_page(items: list, meta: dict) -> str:
    """items: dict (code name description price category image_url limit stock start end state)"""
    e = html.escape
    cats = sorted({i["category"] for i in items if i.get("category")})
    nav = ""
    if cats:
        nav = "<nav aria-label='หมวด'><button data-cat='*' aria-pressed='true'>ทั้งหมด</button>" + "".join(
            f"<button data-cat='{e(c)}' aria-pressed='false'>{e(c)}</button>" for c in cats) + "</nav>"
    cards = []
    for i in items:
        state = i.get("state") or "open"
        pic = (f"<img src='{e(i['image_url'])}' alt='{e(i['name'])}' loading='lazy'>" if i.get("image_url")
               else "<div class='ph' aria-hidden='true'>🍪</div>")
        badge = f"<span class='state {state}'>{STATE_TEXT[state]}</span>" if state in STATE_TEXT else ""
        chips = []
        if i.get("limit"):
            chips.append(f"แลกได้ {i['limit']} ครั้ง/คน")
        if i.get("stock") is not None and i["stock"] >= 0:
            chips.append(f"เหลือ {i['stock']} ชิ้น")
        if i.get("start") and state == "soon":
            chips.append(f"เริ่ม {thai_date(i['start'])}")
        if i.get("end") and state in ("open", "hot"):
            chips.append(f"ถึง {thai_date(i['end'])}")
        meta_html = "".join(f"<span>{e(c)}</span>" for c in chips)
        cat = f"<span class='cat'>{e(i['category'])}</span>" if i.get("category") else ""
        desc = f"<p class='desc'>{e(i['description'])}</p>" if i.get("description") else ""
        off = " off" if state in ("ended", "soldout") else ""
        cards.append(
            f"<article class='item{off}' data-cat='{e(i.get('category') or '')}'>"
            f"<div class='pic'>{pic}{badge}</div>"
            f"<div class='body'>{cat}<h2>{e(i['name'])}</h2>{desc}<div class='meta'>{meta_html}</div></div>"
            f"<div class='price'><b>{i['price']:,} 🍪</b><small>รหัส {e(i['code'])}</small></div></article>")
    if not cards:
        cards.append("<p class='empty'>ยังไม่มีของในร้าน รอแอดมินเติมของก่อนนะ 🍪</p>")
    cta = (f"<a class='cta' href='{e(meta['redeem_url'])}'>🛍️ ไปแลกใน Discord</a>" if meta.get("redeem_url") else "")
    title = e(meta.get("title") or "Cookie Shop")
    return (
        "<!doctype html><html lang='th'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link href='https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;600&family=Mitr:wght@500;600"
        "&display=swap' rel='stylesheet'>"
        f"<style>{CSS}</style></head><body>"
        f"<header><h1>{title} <span>🍪</span></h1>"
        f"<p class='sub'>{e(meta.get('subtitle') or '')}</p>{cta}</header>"
        f"{nav}<main>{''.join(cards)}</main>"
        f"<footer>{e(meta.get('footer') or '')}</footer>"
        f"<script>{JS}</script></body></html>")


def create_app(get_page, images_dir: Path) -> web.Application:
    """get_page() → (items, meta)"""
    images_dir = Path(images_dir)

    async def index(request):
        items, meta = get_page()
        return web.Response(text=render_page(items, meta), content_type="text/html", charset="utf-8",
                            headers={"Cache-Control": "no-cache"})

    async def image(request):
        name = request.match_info["name"]
        if not IMAGE_RE.match(name):
            raise web.HTTPNotFound()
        path = images_dir / name
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})

    async def health(request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/img/{name}", image)
    app.router.add_get("/health", health)
    return app
