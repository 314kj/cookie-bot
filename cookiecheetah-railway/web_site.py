"""หน้าเว็บที่แก้เองได้บนเว็บ — โลโก้ · ปุ่มลัด · แบนเนอร์ · การ์ดโปรโมต · รูปหมวด · ของตกแต่ง · สีธีม

เก็บเป็น JSON ก้อนเดียวใน settings 'web:site' · ไฟล์นี้เป็น logic ล้วน (ไม่แตะฐานข้อมูล/Discord/ไฟล์รูป)
bot.py เป็นคนเขียน/ลบไฟล์รูป แล้วส่งชื่อไฟล์มาให้ update()
"""
import copy
import json
import re

COLORS = ("c0", "c1", "c2", "c3", "c4", "c5", "c6")
IMAGE_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,40}\.(png|jpe?g|webp|gif)$", re.IGNORECASE)
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# ลิงก์ที่ใส่ได้: หน้าในเว็บ (/...) · จุดในหน้า (#...) · เว็บนอก https · คำพิเศษ (แปลงตอนแสดง)
LINK = re.compile(r"^(?:/(?![/\\])[^\s<>\"'`\\]{0,299}|#[A-Za-z0-9_\-]{0,40}|https://[^\s<>\"'`\\/][^\s<>\"'`\\]{2,289})$")
SPECIAL = {"spin": "ห้องหมุนวงล้อ", "discord": "เข้าดิส", "wallet": "กระเป๋าคุกกี้", "donate": "หน้า Donate",
           "all": "ของทั้งหมด"}

PRESETS = {
    "glitter": {"label": "ดำเลื่อมชมพู", "page": "#050507", "bg": "#0A0A0E", "panel": "#111117", "card": "#17171F",
                "card2": "#21212B", "line": "#2A2A36", "line2": "#3C3C4C", "outline": "#000000", "glit": "#FF6FBF"},
    "mint": {"label": "ดำเลื่อมฟ้ามิกุ", "page": "#040707", "bg": "#090D0E", "panel": "#0F1517", "card": "#151D1F",
             "card2": "#1E2A2C", "line": "#28373A", "line2": "#3A4E52", "outline": "#000000", "glit": "#5AE3D8",
             "teal": "#39C5BB", "teal2": "#86E3DC", "teal-d": "#1C6B65", "on-teal": "#002420", "wt2": "#3A6BFF",
             "pink": "#FF4FB0"},
    "night": {"label": "ดำล้วน (ไม่มีเลื่อม)", "page": "#000000", "bg": "#08080A", "panel": "#101013", "card": "#16161A",
              "card2": "#202026", "line": "#2A2A32", "line2": "#3A3A44", "outline": "#000000", "glit": "transparent"},
}

# ช่องที่แก้ได้: fields = {ชื่อ: (ชนิด, ยาวสุด)} · images = ชื่อช่องรูป
SLOTS = {
    "logo": {"fields": {"text": ("text", 40)}, "images": ("img",)},
    "tiles": {"fields": {"label": ("text", 24), "link": ("link", 300), "color": ("color", 0)}, "images": ("img",),
              "max": 4},
    "hero": {"fields": {"title": ("text", 70), "sub": ("text", 220), "btn": ("text", 24), "link": ("link", 300),
                        "color": ("color", 0)}, "images": ("bg", "art"), "max": 6},
    "promos": {"fields": {"title": ("text", 40), "text": ("text", 160), "btn": ("text", 24), "link": ("link", 300),
                          "color": ("color", 0)}, "images": ("img",), "max": 4},
    "cats": {"fields": {"color": ("color", 0)}, "images": ("img",)},
    "deco": {"fields": {}, "images": ("bg", "left", "right")},
    "theme": {"fields": {"preset": ("preset", 0), "accent": ("hex", 0), "accent2": ("hex", 0)}, "images": ()},
    "donate": {"fields": {"title": ("text", 60), "intro": ("text", 400), "color": ("color", 0)}, "images": ("img",)},
}

DEFAULT = {
    "logo": {"text": "", "img": ""},
    "tiles": [{"label": "Redeem", "link": "#all", "color": "c3", "img": ""},
              {"label": "Donate", "link": "/donate", "color": "c1", "img": ""}],
    "hero": [{"title": "", "sub": "", "btn": "", "link": "#all", "color": "c3", "bg": "", "art": ""}],
    "promos": [{"title": "หมุนวงล้อฟรี", "text": "หมุนวันละครั้ง ได้คุกกี้ไปแลกของในเกม", "btn": "ไปหมุน",
                "link": "spin", "color": "c1", "img": ""},
               {"title": "Donate", "text": "แพ็กคุกกี้ / ของในเกม จ่ายบนเว็บได้เลย",
                "btn": "Donate Now!", "link": "/donate", "color": "c3", "img": ""}],
    "cats": {},
    "deco": {"bg": "", "left": "", "right": ""},
    "theme": {"preset": "glitter", "accent": "", "accent2": ""},
    "donate": {"title": "Donate", "intro": "", "color": "c1", "img": ""},
}
LIST_SLOTS = ("tiles", "hero", "promos")
SINGLE_SLOTS = ("logo", "deco", "theme", "donate")
BLANK = {"tiles": {"label": "ปุ่มใหม่", "link": "/", "color": "c0", "img": ""},
         "hero": {"title": "แบนเนอร์ใหม่", "sub": "", "btn": "", "link": "", "color": "c3", "bg": "", "art": ""},
         "promos": {"title": "โปรโมตใหม่", "text": "", "btn": "", "link": "", "color": "c2", "img": ""}}


class SiteError(ValueError):
    pass


def _clean_value(kind: str, value, limit: int) -> str:
    value = "" if value is None else str(value).strip()
    if kind == "text":
        return value[:limit]
    if kind == "link":
        if value == "" or value in SPECIAL:
            return value
        if not LINK.fullmatch(value):
            raise SiteError("ลิงก์ใช้ได้แค่ /หน้าในเว็บ · #จุดในหน้า · https://เว็บนอก · หรือ spin / discord / wallet / donate")
        return value
    if kind == "color":
        if value not in COLORS:
            raise SiteError("สีไม่ถูกต้อง")
        return value
    if kind == "hex":
        if value and not HEX.fullmatch(value):
            raise SiteError("สีต้องเป็นรหัสแบบ #39C5BB")
        return value.upper()
    if kind == "preset":
        if value not in PRESETS:
            raise SiteError("ไม่มีธีมนี้")
        return value
    raise SiteError("ช่องไม่ถูกต้อง")


def _clean_entry(slot: str, raw, base: dict) -> dict:
    """ค่าจาก JSON เก่า (อาจเพี้ยน) → ค่าที่ใช้ได้ (ช่องที่เสีย = ค่าเริ่มต้น)"""
    spec = SLOTS[slot]
    out = dict(base)
    if not isinstance(raw, dict):
        return out
    for key, (kind, limit) in spec["fields"].items():
        if key in raw:
            try:
                out[key] = _clean_value(kind, raw[key], limit)
            except SiteError:
                pass
    for key in spec["images"]:
        v = raw.get(key)
        out[key] = v if isinstance(v, str) and IMAGE_NAME.fullmatch(v) else ""
    return out


def load(text) -> dict:
    """JSON ใน settings → config เต็ม (เติมค่าเริ่มต้นช่องที่ไม่มี) · พังทั้งก้อน = ค่าเริ่มต้น"""
    site = copy.deepcopy(DEFAULT)
    try:
        raw = json.loads(text) if text else {}
    except (TypeError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        return site
    for slot in SINGLE_SLOTS:
        if slot in raw:
            site[slot] = _clean_entry(slot, raw[slot], DEFAULT[slot])
    for slot in LIST_SLOTS:
        if isinstance(raw.get(slot), list):
            blank = {k: "" for k in SLOTS[slot]["fields"]} | {k: "" for k in SLOTS[slot]["images"]}
            blank["color"] = "c0"
            site[slot] = [_clean_entry(slot, r, blank) for r in raw[slot][:SLOTS[slot]["max"]]]
    if isinstance(raw.get("cats"), dict):
        site["cats"] = {str(k)[:40]: _clean_entry("cats", v, {"color": "", "img": ""})
                        for k, v in list(raw["cats"].items())[:60]}
    return site


def dump(site: dict) -> str:
    return json.dumps(site, ensure_ascii=False, separators=(",", ":"))


def images_of(site: dict) -> set:
    """ชื่อไฟล์รูปทั้งหมดที่ config ใช้อยู่"""
    out = set()
    for slot in SINGLE_SLOTS:
        out |= {site[slot].get(k) for k in SLOTS[slot]["images"]}
    for slot in LIST_SLOTS:
        for entry in site[slot]:
            out |= {entry.get(k) for k in SLOTS[slot]["images"]}
    for entry in site["cats"].values():
        out.add(entry.get("img"))
    return {x for x in out if x}


def parse_address(address: str):
    """'hero:2' → ('hero', 2) · 'hero:new' → ('hero', 'new') · 'cats:อาวุธ' → ('cats', 'อาวุธ') · 'logo' → ('logo', None)"""
    slot, _, key = str(address or "").partition(":")
    if slot not in SLOTS:
        raise SiteError("ไม่มีช่องนี้")
    if slot in LIST_SLOTS:
        if key == "new":
            return slot, "new"
        if not (key.isascii() and key.isdigit()):
            raise SiteError("ไม่มีช่องนี้")
        return slot, int(key)
    if slot == "cats":
        key = key.strip()[:40]
        if not key:
            raise SiteError("ไม่มีหมวดนี้")
        return slot, key
    return slot, None


def update(site: dict, address: str, action: str, fields: dict, images: dict) -> tuple:
    """แก้ 1 ช่อง — images = {ช่องรูป: ชื่อไฟล์ใหม่ | '' (ลบรูป)} (ช่องที่ไม่ส่ง = ไม่แตะ)
    คืน (site ใหม่, ชื่อไฟล์รูปที่ไม่ได้ใช้แล้ว) · ผิด → SiteError"""
    site = copy.deepcopy(site)
    before = images_of(site)
    slot, key = parse_address(address)
    spec = SLOTS[slot]
    action = action or "save"
    if slot in LIST_SLOTS:
        items = site[slot]
        if key == "new":
            if action != "save":
                raise SiteError("ไม่มีช่องนี้")
            if len(items) >= spec["max"]:
                raise SiteError(f"ใส่ได้สูงสุด {spec['max']} อัน")
            items.append(copy.deepcopy(BLANK[slot]))
            key = len(items) - 1
        if not 0 <= key < len(items):
            raise SiteError("ช่องนี้ถูกลบไปแล้ว รีเฟรชหน้า")
        if action == "delete":
            if slot == "hero" and len(items) == 1:
                raise SiteError("ต้องมีแบนเนอร์อย่างน้อย 1 อัน")
            items.pop(key)
        elif action in ("up", "down"):
            to = key - 1 if action == "up" else key + 1
            if 0 <= to < len(items):
                items[key], items[to] = items[to], items[key]
        elif action == "save":
            _apply(items[key], spec, fields, images)
        else:
            raise SiteError("คำสั่งไม่ถูกต้อง")
    elif slot == "cats":
        if action == "delete":
            site["cats"].pop(key, None)
        elif action == "save":
            entry = site["cats"].setdefault(key, {"color": "", "img": ""})
            _apply(entry, spec, fields, images)
            if len(site["cats"]) > 60:
                raise SiteError("หมวดเยอะเกินไป")
        else:
            raise SiteError("คำสั่งไม่ถูกต้อง")
    else:
        if action == "delete":  # รีเซ็ตเป็นค่าเริ่มต้น
            site[slot] = copy.deepcopy(DEFAULT[slot])
        elif action == "save":
            _apply(site[slot], spec, fields, images)
        else:
            raise SiteError("คำสั่งไม่ถูกต้อง")
    return site, before - images_of(site)


def _apply(entry: dict, spec: dict, fields: dict, images: dict):
    for key, (kind, limit) in spec["fields"].items():
        if key in fields:
            entry[key] = _clean_value(kind, fields[key], limit)
    for key in spec["images"]:
        if key in images:
            name = images[key] or ""
            if name and not IMAGE_NAME.fullmatch(name):
                raise SiteError("ชื่อไฟล์รูปไม่ถูกต้อง")
            entry[key] = name


def resolve_link(link: str, ctx: dict) -> tuple:
    """คืน (href, เปิดแท็บใหม่ไหม) · ctx: spin_url / invite_url / wallet_url"""
    if not link:
        return "", False
    if link == "spin":
        return ctx.get("spin_url") or "", True
    if link == "discord":
        return ctx.get("invite_url") or ctx.get("discord_url") or "", True
    if link == "wallet":
        return ctx.get("wallet_url") or "", True
    if link == "donate":
        return "/donate", False
    if link == "all":
        return "/#all", False
    return link, link.startswith("https://")


def _mix(hex_color: str, other: str, t: float) -> str:
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def _ink_on(hex_color: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return "#0F2E2B" if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.55 else "#FFFFFF"


def theme_css(theme: dict) -> str:
    """ตัวแปรสีของธีม (ค่าผ่านการตรวจแล้วทั้งหมด → ใส่ใน <style> ได้ปลอดภัย)"""
    p = PRESETS.get(theme.get("preset"), PRESETS["glitter"])
    css = [f"--{k}:{v}" for k, v in p.items() if k != "label"]
    accent = theme.get("accent") or ""
    if HEX.fullmatch(accent):
        css += [f"--teal:{accent}", f"--teal2:{_mix(accent, '#FFFFFF', .18)}", f"--teal-d:{_mix(accent, '#000000', .45)}",
                f"--on-teal:{_ink_on(accent)}"]
        if p.get("glit") != "transparent":  # เลื่อมเป็นสีเดียวกับสีหลัก
            css.append(f"--glit:{accent}")
    accent2 = theme.get("accent2") or ""
    if HEX.fullmatch(accent2):
        css.append(f"--pink:{accent2}")
    return ":root{" + ";".join(css) + "}"
