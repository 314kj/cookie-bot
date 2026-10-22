"""หน้าร้านคุกกี้บนเว็บ — บอทเปิดเองใน service เดิมบน Railway (ไม่ต้อง host เพิ่ม)

GET  /               หน้าร้าน · ล็อกอินด้วย Discord แล้วใส่ตะกร้า กดแลกได้เลย
GET  /login          ไปหน้าอนุญาตของ Discord (ขอแค่ identify)
GET  /auth/callback  Discord ส่งกลับมา → เช็คว่าอยู่ในเซิฟ → ตั้ง session
GET  /logout
GET  /api/me         ยอดคุกกี้ · แลกได้กี่ชิ้นต่อของ · ประวัติล่าสุด
POST /api/checkout   แลกทั้งตะกร้า (ผ่านทุกชิ้นหรือไม่ได้สักชิ้น)
POST /api/admin/item         เพิ่ม/แก้ของ (multipart + รูป) — คนแก้ร้านเท่านั้น
POST /api/admin/item/delete  ลบของ — คนแก้ร้านเท่านั้น
POST /api/admin/page         ข้อความหน้าเว็บ — คนแก้ร้านเท่านั้น
POST /api/admin/category     คำอธิบายหมวด — คนแก้ร้านเท่านั้น
POST /api/admin/site         แก้หน้าเว็บ: โลโก้ ปุ่มลัด แบนเนอร์ โปรโมต รูปหมวด ของตกแต่ง สีธีม (multipart + รูป)
POST /api/admin/donate-item          เพิ่ม/แก้รายการ Donate (multipart + รูป) — แทน /item add · /item edit
POST /api/admin/donate-item/delete   ลบรายการ Donate
GET  /donate         หน้า Donate (จ่ายบนเว็บ · บอทโพสต์สรุป/สถานะในห้อง Donate บน Discord ให้)
GET  /api/donate     ออเดอร์ Donate ของฉัน + รายการ
POST /api/donate/checkout   สั่ง Donate ทั้งตะกร้า → ลิงก์จ่ายเงิน (nonce เดิม = ออเดอร์เดิม ไม่สร้างบิลซ้ำ)
POST /api/donate/pay        ยืนยัน / จ่ายต่อ / สร้างบิลใหม่ ของออเดอร์ตัวเอง
POST /api/donate/check      เช็คกับ Stripe ว่าจ่ายแล้วหรือยัง
POST /api/donate/cancel     ยกเลิกออเดอร์ตัวเอง (ปิดบิลที่ Stripe ก่อน)
GET  /img/<ไฟล์>     รูปของ / รูปที่อัปบนเว็บ (เก็บใน Volume)
GET  /a/<ไฟล์>       รูปประกอบในตัว (โลโก้ ไทล์ สติกเกอร์ แบนเนอร์ — assets/web)
GET  /health         ให้ Railway เช็คว่าบอทยังอยู่

ไฟล์นี้ไม่แตะ Discord / ฐานข้อมูลเอง — ทุกอย่างผ่าน backend ที่ bot.py ส่งมา (ทดสอบแยกได้)
backend ต้องมี: login_enabled() client_id() client_secret redirect_uri() secure public_url secret()
               catalog() page_meta() item_map() admin_catalog() session_version(uid) end_sessions(uid)
               async oauth_user(code) async me(uid) async checkout(uid, data)
               async admin_save(uid, data, image, remove_image) async admin_delete(uid, data) async admin_page(uid, data)
               donate_enabled() donate_catalog() donate_meta() donate_orders(uid)
               async donate_checkout/donate_pay/donate_check/donate_cancel(uid, data)
หน้าตา (HTML/CSS/JS) อยู่ใน web_ui.py
"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from aiohttp import web

from web_donate import render_donate
from web_ui import render_page

log = logging.getLogger("cookiebot.web")

IMAGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,40}\.(png|jpe?g|webp|gif)$", re.IGNORECASE)
# บอก Content-Type เอง (python:slim ไม่มี /etc/mime.types → .webp กลายเป็น octet-stream + nosniff = บางเบราว์เซอร์ไม่โชว์รูป)
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def image_headers(name: str, max_age: int) -> dict:
    return {"Cache-Control": f"public, max-age={max_age}", "X-Content-Type-Options": "nosniff",
            "Content-Type": IMAGE_TYPES[name.rsplit(".", 1)[1].lower()]}
STATIC_DIR = Path(__file__).resolve().parent / "assets" / "web"
MAX_UPLOAD = 9 * 1024 * 1024  # รูปของ ≤ 8 MB + ช่องอื่นในฟอร์ม (เฉพาะ /api/admin/item หลังเช็คว่าเป็นคนแก้ร้าน)
MAX_SITE_UPLOAD = 26 * 1024 * 1024  # ของตกแต่งมีได้ 3 รูป (พื้นหลัง + มุมซ้าย + มุมขวา) รูปละ ≤ 8 MB
MAX_BODY = 64 * 1024          # ทุก request อื่น
SITE_IMAGES = ("img", "bg", "art", "left", "right")
SITE_FIELDS = ("slot", "action", "text", "label", "link", "color", "title", "sub", "btn", "preset", "accent", "accent2",
               "intro", "rate", "rate_loaded", "rev")
SESSION_COOKIE = "cc_sess"
OAUTH_COOKIE = "cc_oauth"
SESSION_DAYS = 7
AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
NEXT_PAGES = ("/", "/donate")  # ล็อกอินเสร็จกลับหน้าเดิม (เฉพาะหน้าในนี้ กันพาไปเว็บอื่น)
LOGIN_NOTICE = {
    "denied": "ยกเลิกการล็อกอินแล้ว",
    "failed": "ล็อกอินไม่สำเร็จ ลองใหม่อีกครั้ง",
    "notmember": "บัญชี Discord นี้ไม่ได้อยู่ในเซิฟของเรา — เข้าดิสก่อนแล้วค่อยล็อกอินใหม่",
    "left": "บัญชีนี้ไม่ได้อยู่ในเซิฟ Discord แล้ว ล็อกอินใหม่อีกครั้ง",
}


# ---------------------------------------------------------------- cookie ที่เซ็นแล้ว (แก้เองไม่ได้)

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def same(a, b) -> bool:
    """เทียบแบบเวลาคงที่ (รับภาษาไทย/อักษรแปลกได้ ไม่ throw)"""
    return hmac.compare_digest(str(a).encode("utf-8", "replace"), str(b).encode("utf-8", "replace"))


def sign(secret: bytes, payload: dict) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def unsign(secret: bytes, token: str, kind: str):
    """คืน dict ถ้าลายเซ็นถูก ชนิดตรง และยังไม่หมดอายุ — ไม่งั้น None"""
    if not token or token.count(".") != 1 or len(token) > 2048:
        return None
    body, sig = token.split(".")
    good = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    if not same(sig, good):
        return None
    try:
        data = json.loads(_unb64(body))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("t") != kind or float(data.get("exp", 0)) < time.time():
        return None
    return data


# ---------------------------------------------------------------- เว็บแอป

def create_app(backend, images_dir: Path, static_dir: Path = None) -> web.Application:
    images_dir = Path(images_dir)
    static_dir = Path(static_dir or STATIC_DIR)

    def cookie_opts(max_age):
        return {"max_age": max_age, "httponly": True, "secure": bool(backend.secure), "samesite": "Lax", "path": "/"}

    def session_of(request):
        if not backend.login_enabled():
            return None
        data = unsign(backend.secret(), request.cookies.get(SESSION_COOKIE, ""), "s")
        if (data and str(data.get("u", "")).isdigit() and data.get("c")
                and data.get("v") == backend.session_version(int(data["u"]))):
            return data
        return None

    def redirect(location):
        return web.Response(status=302, headers={"Location": location, "Cache-Control": "no-store"})

    def no_store(resp):
        resp.headers["Cache-Control"] = "no-store"
        return resp

    async def current_user(request):
        """(session, user, notice, drop) ของหน้า HTML"""
        sess = session_of(request)
        user, notice, drop = None, LOGIN_NOTICE.get(request.query.get("login", ""), ""), False
        if sess:
            try:
                st = await backend.me(int(sess["u"]))
            except Exception:  # noqa: BLE001 — Discord ล่มชั่วคราว: ให้ดูร้านแบบยังไม่ล็อกอินไปก่อน
                log.exception("โหลดข้อมูลผู้ใช้เว็บไม่ได้")
                st, notice = None, "ดึงข้อมูลบัญชีไม่ได้ชั่วคราว ลองรีเฟรชอีกครั้ง"
            if st and st.get("member"):
                user = st
            elif st is not None:
                notice, drop = LOGIN_NOTICE["left"], True
        return sess, user, notice, drop

    def html_page(page, nonce, drop):
        resp = web.Response(text=page, content_type="text/html", charset="utf-8")
        resp.headers.update({
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; img-src 'self' data: blob: https://cdn.discordapp.com https://media.discordapp.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                f"script-src 'nonce-{nonce}'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
                "form-action 'self'"),
            "Referrer-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff"})
        if drop:
            resp.del_cookie(SESSION_COOKIE, path="/")
        return resp

    async def index(request):
        sess, user, notice, drop = await current_user(request)
        nonce = secrets.token_urlsafe(12)
        admin_items = backend.admin_catalog() if user and user.get("editor") else None
        meta = dict(backend.page_meta(), donate_on=backend.donate_enabled())
        page = render_page(backend.catalog(), meta, user=user, csrf=sess["c"] if user else "",
                           login=backend.login_enabled(), notice=notice, nonce=nonce, admin_items=admin_items)
        return html_page(page, nonce, drop)

    async def donate_page(request):
        sess, user, notice, drop = await current_user(request)
        nonce = secrets.token_urlsafe(12)
        orders = backend.donate_orders(int(user["id"])) if user else []
        admin_items = backend.donate_admin_catalog() if user and user.get("editor") else None
        page = render_donate(backend.donate_catalog(), backend.donate_meta(), user=user,
                             csrf=sess["c"] if user else "", login=backend.login_enabled(), notice=notice,
                             nonce=nonce, orders=orders, enabled=backend.donate_enabled(), admin_items=admin_items)
        return html_page(page, nonce, drop)

    async def login(request):
        if not backend.login_enabled():
            return redirect("/")
        state = secrets.token_urlsafe(24)
        url = AUTHORIZE_URL + "?" + urlencode({
            "client_id": backend.client_id(), "response_type": "code", "redirect_uri": backend.redirect_uri(),
            "scope": "identify", "state": state})
        resp = redirect(url)
        back = request.query.get("next", "/")
        resp.set_cookie(OAUTH_COOKIE, sign(backend.secret(), {"t": "o", "s": state, "exp": time.time() + 600,
                                                              "n": back if back in NEXT_PAGES else "/"}),
                        **cookie_opts(600))
        return resp

    async def callback(request):
        if not backend.login_enabled():
            return redirect("/")
        q = request.query
        saved = unsign(backend.secret(), request.cookies.get(OAUTH_COOKIE, ""), "o")
        if not saved or not q.get("state") or not same(saved.get("s", ""), q["state"]):
            return redirect("/?login=failed")
        back = saved.get("n") if saved.get("n") in NEXT_PAGES else "/"
        if q.get("error") or not q.get("code"):
            return redirect(back + "?login=denied")
        try:
            user = await backend.oauth_user(q["code"])
            uid = int(user["id"])
            st = await backend.me(uid)
        except Exception:  # noqa: BLE001
            log.exception("ล็อกอิน Discord ไม่สำเร็จ")
            return redirect(back + "?login=failed")
        if not st.get("member"):
            resp = redirect(back + "?login=notmember")
            resp.del_cookie(OAUTH_COOKIE, path="/")
            return resp
        resp = redirect(back)
        resp.del_cookie(OAUTH_COOKIE, path="/")
        resp.set_cookie(SESSION_COOKIE, sign(backend.secret(), {
            "t": "s", "u": str(uid), "c": secrets.token_urlsafe(18), "v": backend.session_version(uid),
            "exp": time.time() + SESSION_DAYS * 86400}),
                        **cookie_opts(SESSION_DAYS * 86400))
        log.info("เว็บ: %s ล็อกอิน", uid)
        return resp

    async def logout(request):
        sess = session_of(request)
        if sess:  # cookie ที่ก๊อปไปไว้ที่อื่นก็ใช้ไม่ได้แล้ว
            backend.end_sessions(int(sess["u"]))
        resp = redirect("/")
        resp.del_cookie(SESSION_COOKIE, path="/")
        return resp

    async def api_me(request):
        sess = session_of(request)
        if not sess:
            return no_store(web.json_response({"error": "login"}, status=401))
        st = await backend.me(int(sess["u"]))
        if not st.get("member"):
            resp = no_store(web.json_response({"error": "login"}, status=401))
            resp.del_cookie(SESSION_COOKIE, path="/")
            return resp
        return no_store(web.json_response({"user": st, "items": backend.item_map()}))

    async def api_checkout(request):
        sess = session_of(request)
        if not sess:
            return no_store(web.json_response({"error": "ล็อกอินใหม่อีกครั้ง"}, status=401))
        origin = request.headers.get("Origin")
        if origin and backend.public_url and origin.rstrip("/") != backend.public_url.rstrip("/"):
            return no_store(web.json_response({"error": "forbidden"}, status=403))
        if not same(request.headers.get("X-CSRF-Token", ""), sess["c"]):
            return no_store(web.json_response({"error": "หน้าเว็บเก่าไป รีเฟรชแล้วลองใหม่"}, status=403))
        if request.content_type != "application/json":
            return no_store(web.json_response({"error": "bad request"}, status=415))
        try:
            data = json.loads(await request.text())
        except web.HTTPRequestEntityTooLarge:
            return no_store(web.json_response({"ok": False, "error": "ข้อมูลใหญ่เกิน"}, status=413))
        except (ValueError, RecursionError):
            return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        try:
            status, body = await backend.checkout(int(sess["u"]), data)
        except Exception:  # noqa: BLE001 — ไม่รู้ว่าแลกไปแล้วหรือยัง → ให้กดใหม่ด้วย nonce เดิม (ไม่หักซ้ำ)
            log.exception("แลกตะกร้าพัง")
            status, body = 503, {"ok": False, "code": "retry",
                                 "error": "ระบบสะดุดชั่วคราว กดยืนยันอีกครั้ง (ไม่โดนหักซ้ำ)"}
        resp = no_store(web.json_response(body, status=status))
        if status == 401:
            resp.del_cookie(SESSION_COOKIE, path="/")
        return resp

    def guard(request):
        """session + Origin + CSRF (เหมือน checkout) — คืน (session, None) หรือ (None, response)"""
        sess = session_of(request)
        if not sess:
            return None, no_store(web.json_response({"ok": False, "error": "ล็อกอินใหม่อีกครั้ง"}, status=401))
        origin = request.headers.get("Origin")
        if origin and backend.public_url and origin.rstrip("/") != backend.public_url.rstrip("/"):
            return None, no_store(web.json_response({"ok": False, "error": "forbidden"}, status=403))
        if not same(request.headers.get("X-CSRF-Token", ""), sess["c"]):
            return None, no_store(web.json_response({"ok": False, "error": "หน้าเว็บเก่าไป รีเฟรชแล้วลองใหม่"},
                                                    status=403))
        return sess, None

    async def run_admin(call):
        try:
            status, body = await call
        except Exception:  # noqa: BLE001
            log.exception("แก้ร้านบนเว็บพัง")
            status, body = 500, {"ok": False, "error": "บันทึกไม่สำเร็จ ลองใหม่อีกครั้ง"}
        return no_store(web.json_response(body, status=status))

    async def read_json(request):
        if request.content_type != "application/json" or (request.content_length or 0) > 16 * 1024:
            return None
        try:
            data = json.loads(await request.text())
        except (ValueError, RecursionError, web.HTTPRequestEntityTooLarge):
            return None
        return data if isinstance(data, dict) else None

    async def editor_form(request, limit, fields, files, too_big="รูปใหญ่เกิน 8 MB"):
        """ฟอร์ม multipart ของคนแก้ร้าน — เช็คสิทธิ์ก่อนอ่านไฟล์ที่อัปมา · คืน (uid, data, {ไฟล์: bytes}, None) หรือ response"""
        sess, bad = guard(request)
        if bad:
            return None, None, None, bad
        if request.content_type not in ("multipart/form-data", "application/x-www-form-urlencoded"):
            return None, None, None, no_store(web.json_response({"ok": False, "error": "bad request"}, status=415))
        if not await backend.is_editor_uid(int(sess["u"])):
            return None, None, None, no_store(web.json_response({"ok": False, "error": "บัญชีนี้แก้ร้านไม่ได้"},
                                                                status=403))
        try:
            form = await request.clone(client_max_size=limit).post()
        except web.HTTPRequestEntityTooLarge:
            return None, None, None, no_store(web.json_response({"ok": False, "error": too_big}, status=413))
        except ValueError:
            return None, None, None, no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        data, blobs = {}, {}
        for key in fields:
            value = form.get(key)
            if isinstance(value, str):
                data[key] = value[:2000]
        for key in files:
            upload = form.get(key)
            if upload is not None and not isinstance(upload, str):
                try:
                    blob = await asyncio.get_running_loop().run_in_executor(None, upload.file.read, MAX_UPLOAD + 1)
                finally:
                    upload.file.close()
                if blob:
                    blobs[key] = blob
        return int(sess["u"]), data, blobs, None

    async def admin_item(request):
        uid, data, blobs, bad = await editor_form(
            request, MAX_UPLOAD, ("original", "code", "name", "price", "ckx", "description", "category", "limit",
                                  "stock", "stock_loaded", "start", "end", "active", "sort", "remove_image"), ("image",))
        if bad:
            return bad
        remove = str(data.pop("remove_image", "")).lower() in ("1", "true", "on")
        return await run_admin(backend.admin_save(uid, data, blobs.get("image"), remove))

    async def admin_site(request):
        uid, data, blobs, bad = await editor_form(
            request, MAX_SITE_UPLOAD, SITE_FIELDS + tuple(f"rm_{k}" for k in SITE_IMAGES), SITE_IMAGES,
            "ไฟล์รวมใหญ่เกิน 25 MB (รูปละไม่เกิน 8 MB)")
        if bad:
            return bad
        removes = {k for k in SITE_IMAGES if str(data.pop(f"rm_{k}", "")).lower() in ("1", "true", "on")}
        return await run_admin(backend.admin_site(uid, data, blobs, removes))

    async def admin_donate_item(request):
        uid, data, blobs, bad = await editor_form(
            request, MAX_UPLOAD, ("original", "code", "name", "price", "cookies", "ckx", "description", "active",
                                  "sort", "remove_image"), ("image",))
        if bad:
            return bad
        remove = str(data.pop("remove_image", "")).lower() in ("1", "true", "on")
        return await run_admin(backend.admin_donate_item(uid, data, blobs.get("image"), remove))

    async def admin_donate_delete(request):
        sess, bad = guard(request)
        if bad:
            return bad
        data = await read_json(request)
        if data is None:
            return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        return await run_admin(backend.admin_donate_delete(int(sess["u"]), data))

    async def admin_item_delete(request):
        sess, bad = guard(request)
        if bad:
            return bad
        data = await read_json(request)
        if data is None:
            return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        return await run_admin(backend.admin_delete(int(sess["u"]), data))

    async def admin_page(request):
        sess, bad = guard(request)
        if bad:
            return bad
        data = await read_json(request)
        if data is None:
            return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        return await run_admin(backend.admin_page(int(sess["u"]), data))

    async def admin_category(request):
        sess, bad = guard(request)
        if bad:
            return bad
        data = await read_json(request)
        if data is None:
            return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
        return await run_admin(backend.admin_category(int(sess["u"]), data))

    async def api_donate(request):
        sess = session_of(request)
        if not sess:
            return no_store(web.json_response({"error": "login"}, status=401))
        uid = int(sess["u"])
        return no_store(web.json_response({"orders": backend.donate_orders(uid), "catalog": backend.donate_catalog()}))

    def donate_action(method):
        async def handler(request):
            sess, bad = guard(request)
            if bad:
                return bad
            data = await read_json(request)
            if data is None:
                return no_store(web.json_response({"ok": False, "error": "bad request"}, status=400))
            try:
                status, body = await getattr(backend, method)(int(sess["u"]), data)
            except Exception:  # noqa: BLE001 — ไม่รู้ผล → กดใหม่ด้วยข้อมูลเดิมได้ (nonce เดิม = ออเดอร์เดิม)
                log.exception("Donate บนเว็บพัง (%s)", method)
                status, body = 503, {"ok": False, "code": "retry",
                                     "error": "ระบบสะดุดชั่วคราว กดอีกครั้ง (ไม่สร้างบิลซ้ำ)"}
            resp = no_store(web.json_response(body, status=status))
            if status == 401:
                resp.del_cookie(SESSION_COOKIE, path="/")
            return resp
        return handler

    async def image(request):
        name = request.match_info["name"]
        if not IMAGE_RE.match(name):
            raise web.HTTPNotFound()
        path = images_dir / name
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers=image_headers(name, 86400))

    async def static(request):
        name = request.match_info["name"]
        if not IMAGE_RE.match(name):
            raise web.HTTPNotFound()
        path = static_dir / name
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers=image_headers(name, 604800))

    async def health(request):
        return web.Response(text="ok")

    app = web.Application(client_max_size=MAX_BODY)
    app.router.add_get("/", index)
    app.router.add_get("/login", login)
    app.router.add_get("/auth/callback", callback)
    app.router.add_get("/logout", logout)
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/checkout", api_checkout)
    app.router.add_post("/api/admin/item", admin_item)
    app.router.add_post("/api/admin/item/delete", admin_item_delete)
    app.router.add_post("/api/admin/page", admin_page)
    app.router.add_post("/api/admin/category", admin_category)
    app.router.add_post("/api/admin/site", admin_site)
    app.router.add_post("/api/admin/donate-item", admin_donate_item)
    app.router.add_post("/api/admin/donate-item/delete", admin_donate_delete)
    app.router.add_get("/donate", donate_page)
    app.router.add_get("/api/donate", api_donate)
    for name in ("checkout", "pay", "check", "cancel"):
        app.router.add_post(f"/api/donate/{name}", donate_action(f"donate_{name}"))
    app.router.add_get("/img/{name}", image)
    app.router.add_get("/a/{name}", static)
    app.router.add_get("/health", health)
    return app
