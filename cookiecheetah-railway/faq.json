"""Cookie Express link — สร้างคำสั่ง ckx ให้ relay และอ่านข้อความที่ relay ตอบกลับ

บอทนี้ (บน Railway) โพสต์คำสั่งในห้องลับของ relay:
    ckx "<ชื่อในเกม>" CX-AAAA-BBBB*2 CV-CCCC-DDDD | rd-15
relay บนเครื่องเซิฟใช้ id ข้อความนั้นเป็นเลขออเดอร์ (dc-<message id>) แล้วตอบกลับในห้องเดียวกัน
ไฟล์นี้ไม่แตะ Discord เลย — ทดสอบได้ตรงๆ
"""
import re

ALPHA = "TF5GYDLUZXWH2JS7C6E9A8Q4VKMRP3BN"  # ตัวอักษรรหัส Cookie Express
_CODE = re.compile(r"^(C[XV])-?([" + ALPHA + r"]{4})-?([" + ALPHA + r"]{4})$")
_DC = re.compile(r"`dc-(\d+)`")
MAX_COUNT = 999


def normalize_items(text: str, multiply: int = 1) -> str:
    """'cx-aaaa-bbbb * 2, CV-…' → 'CX-AAAA-BBBB*2;CV-…*1' (คูณจำนวนด้วย multiply) — ValueError ถ้ารหัสผิด"""
    text = re.sub(r"\s*\*\s*", "*", (text or "").strip())
    out = []
    for part in re.split(r"[\s;,]+", text):
        if not part:
            continue
        code, _, n = part.partition("*")
        m = _CODE.match(code.upper())
        if not m:
            raise ValueError(f"รหัส `{part}` ไม่ใช่รหัส Cookie Express (CX-XXXX-XXXX / CV-XXXX-XXXX)")
        try:
            count = int(n) if n else 1
        except ValueError:
            raise ValueError(f"จำนวนใน `{part}` ต้องเป็นตัวเลข")
        count *= max(1, int(multiply))
        if not 1 <= count <= MAX_COUNT:
            raise ValueError(f"จำนวนต่อรหัสต้อง 1–{MAX_COUNT} (ได้ {count})")
        out.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}*{count}")
    if not out:
        raise ValueError("ไม่มีรหัส")
    return ";".join(out)


def max_count(items: str) -> int:
    """จำนวนสูงสุดต่อรหัสในชุด (ใช้กันคูณจำนวนแล้วเกิน 999)"""
    return max((int(p.partition("*")[2] or 1) for p in (items or "").split(";") if p), default=0)


def count_lines(items: str) -> int:
    return len([p for p in (items or "").split(";") if p])


def valid_ingame(name: str) -> bool:
    """ชื่อในเกมที่ส่งผ่านคำสั่งได้ (ภาษาไทยได้ ห้าม \" | และขึ้นบรรทัดใหม่)"""
    name = name or ""
    return 1 <= len(name.strip()) <= 40 and not re.search(r'["|\r\n`]', name)


def build_command(ingame: str, items: str, note: str) -> str:
    if not valid_ingame(ingame):
        raise ValueError("ชื่อในเกมใช้ไม่ได้")
    note = re.sub(r"[^A-Za-z0-9 #._\-]", "", note or "")[:40]
    return f'ckx "{ingame.strip()}" {" ".join(items.split(";"))}' + (f" | {note}" if note else "")


# ---------------------------------------------------------------- อ่านข้อความ relay

# (คำนำหน้า, ชนิด) — ตรงกับข้อความใน cookie_relay.py
_PREFIX = (
    ("📦", "queued"),
    ("👀", "seen"),
    ("✅", "claimed"),
    ("🚗", "vehicle"),
    ("⚠️ รหัสใช้ไม่ได้", "rejected"),
    ("❗", "short"),
    ("↩️", "undo"),
    ("🗑️ ยกเลิก", "cancelled"),
    ("🗑️ ส่งคำสั่งยกเลิก", "cancel_sent"),
    ("ออเดอร์", "queued"),  # "ออเดอร์ `dc-…` อยู่ในคิวแล้ว" (ส่งซ้ำ)
)


def parse_relay(content: str, is_reply: bool):
    """คืน list ของ (ชนิด, order_msg_id|None, บรรทัด)
    - บรรทัดที่มี `dc-<id>` → ชนิดตามคำนำหน้า
    - ข้อความตอบกลับ (reply) ที่ไม่มี dc-id และไม่ใช่ 📦 → ('error', None, ข้อความ) ให้ผู้เรียกใช้ reference แทน
    """
    events = []
    for line in (content or "").splitlines():
        m = _DC.search(line)
        if not m:
            continue
        kind = None
        stripped = line.strip()
        bare = stripped.replace("\ufe0f", "")  # ⚠️/🗑️/↩️ มีหรือไม่มีตัวแปร FE0F ก็ได้
        for prefix, k in sorted(_PREFIX, key=lambda p: -len(p[0])):
            if bare.startswith(prefix.replace("\ufe0f", "")):
                kind = k
                break
        if kind:
            events.append((kind, int(m.group(1)), stripped))
    if is_reply and not events:
        text = (content or "").strip()
        if text and not text.startswith("📦"):
            events.append(("error", None, text))
    return events
