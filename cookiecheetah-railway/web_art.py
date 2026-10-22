"""ไอคอน + รูปประกอบของเว็บร้าน (ธีม Cookie Cheetah: ดำเลื่อมชมพู · หน้าต่างแบบ Win95 · ฟอนต์พิกเซล)

- รูปหลักเป็นของ Cookie Cheetah เอง (assets/web/*.webp) — โลโก้ ไทล์ DONATE/REDEEM สติกเกอร์หมวด แบนเนอร์ คุกกี้
- ไอคอนเล็กเป็นพิกเซลอาร์ต: ส่วนใหญ่จาก pixelarticons (MIT License, Copyright (c) 2019 Gerrit Halfmann)
  + sword / crown / cat วาดเพิ่มในสไตล์เดียวกัน
"""
import hashlib
import html
from pathlib import Path

# ชื่อ: (path ใน viewBox 24×24, "f" = เติมสี | "s" = เส้น)
PX = {
    "archive": ("M22 4H2v6h2v10h16V10h2V4zM6 10h12v8H6v-8zm14-4v2H4V6h16zm-5 6H9v2h6v-2z", "f"),
    "book": ("M8 2h12v20H4V2h4zm4 8h-2v2H8V4H6v16h12V4h-4v8h-2v-2z", "f"),
    "cake": ("M6 2h2v2H6V2zm2 3H6v3H2v9h6v-2h2v2h4v-2h2v2h6V8h-4V5h-2v3h-3V5h-2v3H8V5zm12 10h-4v-3h-2v3h-4v-3H8v3H4v-5h16v5zM2 20h20v2H2v-2zM13 2h-2v2h2V2zm3 0h2v2h-2V2zM2 17h2v3H2zm18 0h2v3h-2z", "f"),
    "car": ("M17 4H7v2H5v2H3v12h4v-2h10v2h4V8h-2V6h-2V4zm0 2v2h2v2H5V8h2V6h10zm2 10H5v-4h14v4zm-2-3h-2v2h2v-2zM7 13h2v2H7v-2z", "f"),
    "cart": ("M2 2h4v4h16v11H4V4H2V2zm4 13h14V8H6v7zm0 4h3v3H6v-3zm14 0h-3v3h3v-3z", "f"),
    "cat": ("M0 0h2v2h-2zM22 0h2v2h-2zM0 2h4v2h-4zM20 2h4v2h-4zM0 4h2v2h-2zM4 4h2v2h-2zM18 4h2v2h-2zM22 4h2v2h-2zM0 6h2v2h-2zM6 6h12v2h-12zM22 6h2v2h-2zM0 8h2v2h-2zM22 8h2v2h-2zM0 10h2v2h-2zM6 10h2v2h-2zM16 10h2v2h-2zM22 10h2v2h-2zM0 12h2v2h-2zM6 12h2v2h-2zM16 12h2v2h-2zM22 12h2v2h-2zM0 14h2v2h-2zM10 14h4v2h-4zM22 14h2v2h-2zM0 16h2v2h-2zM22 16h2v2h-2zM2 18h2v2h-2zM20 18h2v2h-2zM4 20h16v2h-16z", "f"),
    "check": ("M18 6h2v2h-2V6zm-2 4V8h2v2h-2zm-2 2v-2h2v2h-2zm-2 2h2v-2h-2v2zm-2 2h2v-2h-2v2zm-2 0v2h2v-2H8zm-2-2h2v2H6v-2zm0 0H4v-2h2v2z", "f"),
    "chevron-left": ("M16 5v2h-2V5h2zm-4 4V7h2v2h-2zm-2 2V9h2v2h-2zm0 2H8v-2h2v2zm2 2v-2h-2v2h2zm0 0h2v2h-2v-2zm4 4v-2h-2v2h2z", "f"),
    "chevron-right": ("M8 5v2h2V5H8zm4 4V7h-2v2h2zm2 2V9h-2v2h2zm0 2h2v-2h-2v2zm-2 2v-2h2v2h-2zm0 0h-2v2h2v-2zm-4 4v-2h2v2H8z", "f"),
    "clock": ("M19 3H5v2H3v14h2v2h14v-2h2V5h-2V3zm0 2v14H5V5h14zm-8 2h2v6h4v2h-6V7z", "f"),
    "close": ("M5 5h2v2H5V5zm4 4H7V7h2v2zm2 2H9V9h2v2zm2 0h-2v2H9v2H7v2H5v2h2v-2h2v-2h2v-2h2v2h2v2h2v2h2v-2h-2v-2h-2v-2h-2v-2zm2-2v2h-2V9h2zm2-2v2h-2V7h2zm0 0V5h2v2h-2z", "f"),
    "coin": ("M6 2h12v2H6V2zM4 6V4h2v2H4zm0 12V6H2v12h2zm2 2v-2H4v2h2zm12 0v2H6v-2h12zm2-2v2h-2v-2h2zm0-12h2v12h-2V6zm0 0V4h-2v2h2zm-9-1h2v2h3v2h-6v2h6v6h-3v2h-2v-2H8v-2h6v-2H8V7h3V5z", "f"),
    "crown": ("M0 2h2v2h-2zM10 2h4v2h-4zM22 2h2v2h-2zM0 4h4v2h-4zM8 4h2v2h-2zM14 4h2v2h-2zM20 4h4v2h-4zM0 6h2v2h-2zM4 6h4v2h-4zM16 6h4v2h-4zM22 6h2v2h-2zM0 8h2v2h-2zM22 8h2v2h-2zM0 10h2v2h-2zM22 10h2v2h-2zM0 12h2v2h-2zM22 12h2v2h-2zM0 14h24v2h-24zM0 18h24v2h-24z", "f"),
    "dice": ("M5 3H3v18h18V3H5zm14 2v14H5V5h14zM9 7H7v2h2V7zm6 0h2v2h-2V7zm-6 8H7v2h2v-2zm6 0h2v2h-2v-2zm-2-4h-2v2h2v-2z", "f"),
    "edit": ("M18 2h-2v2h-2v2h-2v2h-2v2H8v2H6v2H4v2H2v6h6v-2h2v-2h2v-2h2v-2h2v-2h2v-2h2V8h2V6h-2V4h-2V2zm0 8h-2v2h-2v2h-2v2h-2v2H8v-2H6v-2h2v-2h2v-2h2V8h2V6h2v2h2v2zM6 16H4v4h4v-2H6v-2z", "f"),
    "external-link": ("M21 11V3h-8v2h4v2h-2v2h-2v2h-2v2H9v2h2v-2h2v-2h2V9h2V7h2v4h2zM11 5H3v16h16v-8h-2v6H5V7h6V5z", "f"),
    "gift": ("M19 12v8h-7m7-8h2V8h-3m1 4H5m13-4V4h-6m6 4H6m0 0V4h6M6 8H3v4h2m0 0v8h7m0 0V4", "s"),
    "grid": ("M2 2h20v20H2V2zm2 2v4h4V4H4zm6 0v4h4V4h-4zm6 0v4h4V4h-4zm4 6h-4v4h4v-4zm0 6h-4v4h4v-4zm-6 4v-4h-4v4h4zm-6 0v-4H4v4h4zm-4-6h4v-4H4v4zm6-4v4h4v-4h-4z", "f"),
    "heart": ("M9 2H5v2H3v2H1v6h2v2h2v2h2v2h2v2h2v2h2v-2h2v-2h2v-2h2v-2h2v-2h2V6h-2V4h-2V2h-4v2h-2v2h-2V4H9V2zm0 2v2h2v2h2V6h2V4h4v2h2v6h-2v2h-2v2h-2v2h-2v2h-2v-2H9v-2H7v-2H5v-2H3V6h2V4h4z", "f"),
    "home": ("M14 2h-4v2H8v2H6v2H4v2H2v2h2v10h7v-6h2v6h7V12h2v-2h-2V8h-2V6h-2V4h-2V2zm0 2v2h2v2h2v2h2v2h-2v8h-3v-6H9v6H6v-8H4v-2h2V8h2V6h2V4h4z", "f"),
    "image": ("M4 3H2v18h20V3H4zm16 2v14H4V5h16zm-6 4h-2v2h-2v2H8v2H6v2h2v-2h2v-2h2v-2h2v2h2v2h2v-2h-2v-2h-2V9zM8 7H6v2h2V7z", "f"),
    "info-box": ("M3 3h2v18H3V3zm16 0H5v2h14v14H5v2h16V3h-2zm-8 6h2V7h-2v2zm2 8h-2v-6h2v6z", "f"),
    "logout": ("M5 3h16v4h-2V5H5v14h14v-2h2v4H3V3h2zm16 8h-2V9h-2V7h-2v2h2v2H7v2h10v2h-2v2h2v-2h2v-2h2v-2z", "f"),
    "menu": ("M4 6h16v2H4V6zm0 5h16v2H4v-2zm16 5H4v2h16v-2z", "f"),
    "message": ("M20 2H2v20h2V4h16v12H6v2H4v2h2v-2h16V2h-2z", "f"),
    "mood-happy": ("M5 3h14v2H5V3zm0 16H3V5h2v14zm14 0v2H5v-2h14zm0 0h2V5h-2v14zM10 8H8v2h2V8zm4 0h2v2h-2V8zm-5 6v-2H7v2h2zm6 0v2H9v-2h6zm0 0h2v-2h-2v2z", "f"),
    "notification": ("M14 4V2h-4v2H5v2h14V4h-5zm5 12H5v-4H3v6h5v4h2v-4h4v2h-4v2h6v-4h5v-6h-2V6h-2v8h2v2zM5 6v8h2V6H5z", "f"),
    "paint-bucket": ("M8 3h8v2H8V3zm0 2H6v4H4v12h16V9h-2V5h-2v4H8V5zm8 6h2v8H6v-8h2v6h2v-4h2v2h2v-2h2v-2z", "f"),
    "play": ("M10 20H8V4h2v2h2v3h2v2h2v2h-2v2h-2v3h-2v2z", "f"),
    "plus": ("M11 4h2v7h7v2h-7v7h-2v-7H4v-2h7V4z", "f"),
    "reload": ("M16 2h-2v2h2v2H4v2H2v5h2V8h12v2h-2v2h2v-2h2V8h2V6h-2V4h-2V2zM6 20h2v2h2v-2H8v-2h12v-2h2v-5h-2v5H8v-2h2v-2H8v2H6v2H4v2h2v2z", "f"),
    "search": ("M6 2h8v2H6V2zM4 6V4h2v2H4zm0 8H2V6h2v8zm2 2H4v-2h2v2zm8 0v2H6v-2h8zm2-2h-2v2h2v2h2v2h2v2h2v-2h-2v-2h-2v-2h-2v-2zm0-8h2v8h-2V6zm0 0V4h-2v2h2z", "f"),
    "shopping-bag": ("M9 2h6v2H9V2zm6 4V4h2v2h4v16H3V6h4V4h2v2h6zm0 2H9v2H7V8H5v12h14V8h-2v2h-2V8z", "f"),
    "sliders": ("M17 4h2v10h-2V4zm0 12h-2v2h2v2h2v-2h2v-2h-4zm-4-6h-2v10h2V10zm-8 2H3v2h2v6h2v-6h2v-2H5zm8-8h-2v2H9v2h6V6h-2V4zM5 4h2v6H5V4z", "f"),
    "store": ("M4 3h16v2H4V3zm0 4h18v8h-2v6h-2v-6h-4v6H4v-6H2V7h2zm8 12v-4H6v4h6zm0-6h8V9H4v4h8z", "f"),
    "sword": ("M16 0h8v2h-8zM14 2h2v2h-2zM22 2h2v2h-2zM12 4h2v2h-2zM20 4h2v2h-2zM10 6h2v2h-2zM18 6h2v2h-2zM8 8h2v2h-2zM16 8h2v2h-2zM2 10h2v2h-2zM6 10h2v2h-2zM14 10h2v2h-2zM4 12h2v2h-2zM12 12h2v2h-2zM4 14h4v2h-4zM10 14h2v2h-2zM2 16h2v2h-2zM8 16h2v2h-2zM0 18h2v2h-2zM6 18h2v2h-2zM10 18h2v2h-2zM0 20h2v2h-2zM4 20h2v2h-2zM10 20h2v2h-2zM2 22h2v2h-2z", "f"),
    "trash": ("M16 2v4h6v2h-2v14H4V8H2V6h6V2h8zm-2 2h-4v2h4V4zm0 4H6v12h12V8h-4zm-5 2h2v8H9v-8zm6 0h-2v8h2v-8z", "f"),
    "trophy": ("M16 3H6v2H2v10h6V5h8v10h6V5h-4V3h-2zm4 4v6h-2V7h2zM6 13H4V7h2v6zm12 2H6v2h12v-2zm-7 2h2v2h3v2H8v-2h3v-2z", "f"),
    "truck": ("M2 4h14v4h4v2h-4v6h6v-4h2v6h-4v2h-4v-2H8v2H4v-2H0V4h2zm20 8h-2v-2h2v2zm-8-2V6H2v10h12v-6z", "f"),
    "user": ("M15 2H9v2H7v6h2V4h6V2zm0 8H9v2h6v-2zm0-6h2v6h-2V4zM4 16h2v-2h12v2H6v4h12v-4h2v6H4v-6z", "f"),
    "view-list": ("M2 5h20v14H2V5zm2 2v2h16V7H4zm16 4H4v2h16v-2zm0 4H4v2h16v-2z", "f"),
    "wallet": ("M18 3H2v18h18v-4h2V7h-2V3h-2zm0 14v2H4V5h14v2h-8v10h8zm2-2h-8V9h8v6zm-4-4h-2v2h2v-2z", "f"),
    "zap": ("M12 1h2v8h8v4h-2v-2h-8V5h-2V3h2V1zM8 7V5h2v2H8zM6 9V7h2v2H6zm-2 2V9h2v2H4zm10 8v2h-2v2h-2v-8H2v-4h2v2h8v6h2zm2-2v2h-2v-2h2zm2-2v2h-2v-2h2zm0 0h2v-2h-2v2z", "f"),
}

# ไฟล์รูปในตัว (เสิร์ฟที่ /a/<ชื่อ>) · ?v= = แฮชของไฟล์ทั้งหมด → เปลี่ยนรูปแล้วเบราว์เซอร์โหลดใหม่ทันที (cache 7 วัน)
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "web"


def _asset_version() -> str:
    h = hashlib.sha1()
    for p in sorted(ASSET_DIR.glob("*")) if ASSET_DIR.is_dir() else ():
        if p.is_file():
            h.update(p.name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()[:8]


VER = _asset_version()


def asset(name: str) -> str:
    return f"/a/{name}?v={VER}"


LOGO = asset("logo.webp")
BANNER = asset("banner.webp")
TILE_DONATE = asset("tile-donate.webp")
TILE_REDEEM = asset("tile-redeem.webp")
MASCOT = asset("mascot.webp")
COOKIE_BAR = asset("cookie-bar.webp")
COOKIE_FOIL = asset("cookie-foil.webp")
COOKIE_PACK = asset("cookie-pack.webp")
COOKIE_STICKER = asset("cookie-sticker.webp")
WINDOW = asset("window.webp")
STICKERS = {"vehicle": asset("cat-car.webp"), "outfit": asset("cat-skin.webp"), "bag": asset("cat-skin.webp"),
            "weapon": asset("cat-weapon.webp"), "ammo": asset("cat-weapon.webp"), "misc": asset("cat-etc.webp")}

# คีย์ภาพเดิม → ไอคอนพิกเซล
ART_PX = {"all": "grid", "weapon": "sword", "ammo": "zap", "vehicle": "car", "outfit": "crown", "bag": "shopping-bag",
          "food": "cake", "med": "heart", "tool": "paint-bucket", "material": "archive", "book": "book", "chat": "message",
          "event": "trophy", "special": "zap", "parcel": "archive", "admin": "user", "wheel": "dice",
          "megaphone": "notification", "heart": "heart", "jar": "gift", "qr": "coin", "misc": "cat", "leek": "zap",
          "petal": "heart", "cookie": "coin"}

CAT_WORDS = (
    (("อาวุธ", "ดาบ", "ปืน", "weapon", "gun", "sword"), "weapon"),
    (("กระสุน", "ammo"), "ammo"),
    (("รถ", "vehicle", "car"), "vehicle"),
    (("สกิน", "ชุด", "แฟชั่น", "เสื้อ", "skin", "outfit", "cloth"), "outfit"),
    (("กระเป๋า", "bag"), "bag"),
    (("อาหาร", "ขนม", "food"), "food"),
    (("ยา", "แพทย์", "med"), "med"),
    (("เครื่องมือ", "tool"), "tool"),
    (("วัสดุ", "ไม้", "material"), "material"),
    (("หนังสือ", "สกิล", "book", "skill"), "book"),
    (("ดิส", "ยศ", "discord", "role"), "chat"),
    (("อีเวนต์", "event", "ฮาโลวีน", "halloween"), "event"),
    (("พิเศษ", "special", "limited", "แรร์", "rare"), "special"),
    (("อื่น", "etc", "misc", "ทั่วไป", "เบ็ดเตล็ด"), "misc"),
)


def cat_art(name: str) -> str:
    low = (name or "").lower()
    for words, key in CAT_WORDS:
        if any(w in low for w in words):
            return key
    return "cookie"


def px(name: str, size: int = 24, cls: str = "", label: str = "") -> str:
    """ไอคอนพิกเซล (สีตาม currentColor) · ขนาดปัดเป็นทวีคูณของ 12 ให้พิกเซลคม"""
    d, mode = PX.get(name, PX["zap"])
    size = 12 if size <= 14 else 24 if size <= 30 else 36 if size <= 42 else 48 if size <= 60 else 72 if size <= 84 else 96
    c = f" class='px {cls}'" if cls else " class='px'"
    a = f" role='img' aria-label='{html.escape(label)}'" if label else " aria-hidden='true' focusable='false'"
    paint = "fill='none' stroke='currentColor' stroke-width='2'" if mode == "s" else "fill='currentColor'"
    return (f"<svg{c} width='{size}' height='{size}' viewBox='0 0 24 24' shape-rendering='crispEdges'{a}>"
            f"<path d='{d}' {paint}/></svg>")


def cookie(size: int = 24, cls: str = "") -> str:
    """หน้าคุกกี้ (มาสคอตของเซิฟ) — ใช้เป็นหน่วยคุกกี้ทุกที่"""
    src = asset("cookie.webp" if size > 48 else "cookie-64.webp")
    c = f"ck {cls}".strip()
    return f"<img class='{c}' src='{src}' width='{size}' height='{size}' alt='' decoding='async'>"


def art(key: str, size: int = 32, cls: str = "") -> str:
    """ภาพประกอบเล็ก (ชื่อคีย์เดิม) → คุกกี้ = รูปมาสคอต · อื่นๆ = ไอคอนพิกเซล"""
    if key == "cookie":
        return cookie(size, cls)
    return px(ART_PX.get(key, key if key in PX else "zap"), size, cls)


def sticker(key: str) -> str:
    """สติกเกอร์หมวดในตัว (CAR / SKIN & BAG / WEAPON / ETC) — '' = ไม่มี"""
    return STICKERS.get(key, "")


def hero_art() -> str:
    return f"<img class='hero-art' src='{MASCOT}' alt='' width='320' height='320'>"
