"""
CookieCheetah Bot — welcome + ticket (private thread) + whitelist + Steam + Donate (Stripe)
รันบน Railway (ตั้งค่าผ่าน Variables) ไม่ต้องใช้ akapanel

- ข้อความต้อนรับ (Components V2) มีปุ่มไปห้องกฎ + ปุ่ม 🍪 Join
- Join / ปุ่มเปิด Ticket → เลือกหมวด: ขอ White List (เฉพาะคนที่ยังไม่มี) / Donate / แจ้งบั๊ก / รีพอร์ต / ติดต่อแอดมิน
- ทุก ticket เป็น private thread ในห้อง ticket ห้องเดียว (ไม่สร้างห้องใหม่)
- White List: กรอก Steam ID → เช็คผ่าน Steam Web API → แอดมินกดอนุมัติ / ไม่ผ่าน
- Donate: ตะกร้า 5 รายการ → การ์ดสรุป → ยืนยัน → บิล Stripe (PromptPay QR / บัตร)
  → จ่ายแล้วมีการ์ดยืนยัน + ปุ่มให้แอดมินติ๊กว่าส่งของแล้ว
- แอดมินจัดการรายการ Donate ด้วย /item, ดูออเดอร์ด้วย /order
"""

import asyncio
import html
import io
import json
import logging
import os
import re
import secrets
import sqlite3
import struct
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Awaitable, Callable, Mapping, Optional

import aiohttp
import discord
from discord import app_commands, ui

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv ไม่บังคับ (ใช้ตอนรันในเครื่อง)
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
EXIT_CONFIG = 3

log = logging.getLogger("cookiecheetah")


# =====================================================================
# ข้อความที่แก้ได้
# =====================================================================

WELCOME_TITLE = "Welcome to Cookie Cheetah! 🍪"
WELCOME_SUBTITLE = "เซิฟเวอร์ Project Zomboid PVE 100% | Thailand Community"
WELCOME_STEPS = (
    "อ่าน {rules} ให้ครบ",
    "กดคำขอและกรอกแบบสอบถามที่ 🍪 Join",
    "รอแอดมินอนุมัติภายใน 24 ชม. แล้วจะได้ข้อมูลเข้าเกม ✅",
)
RULES_HEADING = "📜 Rules"
RULES_TEXT = "อ่าน กฎ-ข้อต้องห้าม ก่อนเข้าร่วม"
RULES_BUTTON = "กฎ-ข้อต้องห้าม"
JOIN_HEADING = "✅ คำขอ White List"
JOIN_TEXT = "ส่งคำขอได้ที่นี่"
JOIN_BUTTON = "Join"

TICKET_PANEL_TITLE = "Ticket 🍪"
TICKET_PANEL_TEXT = ("กดปุ่มแล้วเลือกเรื่องที่ต้องการ ระบบจะเปิดห้องคุยส่วนตัว (thread) "
                     "ที่เห็นแค่คุณกับทีมแอดมิน")
TICKET_PANEL_BUTTON = "เปิด Ticket"
MENU_PROMPT = "ต้องการทำรายการอะไร?"

DONATE_TITLE = "💝 Donate สนับสนุนเซิฟ"
DONATE_INTRO = "ขอบคุณที่ช่วยให้ Cookie Cheetah เปิดต่อไปได้ 🍪"
DONATE_HOWTO = (
    "กด **💝 Donate** แล้วใส่รหัสกับจำนวน (สูงสุด 5 รายการต่อรอบ)",
    "กด **ส่ง** → ตรวจการ์ดสรุปแล้วกด **ยืนยัน**",
    "จ่ายผ่าน PromptPay QR หรือบัตร → บอทแจ้งในห้องนี้ แอดมินจะส่งของให้ในเกม",
)

COLOR_OK = 0x2ECC71
COLOR_BAD = 0xE74C3C
COLOR_INFO = 0x3498DB
COLOR_MUTED = 0x95A5A6
COLOR_DONATE = 0xF06292
COLOR_WAIT = 0xF5A623


@dataclass(frozen=True)
class Question:
    key: str
    label: str  # Discord จำกัด 45 ตัวอักษร
    paragraph: bool = False
    required: bool = False
    max_length: int = 200
    placeholder: Optional[str] = None


@dataclass(frozen=True)
class TicketType:
    key: str
    label: str
    emoji: str  # emoji ตัวเดียวล้วน (ห้ามตัวที่มีตัวต่อท้ายอย่าง ⚠️)
    prefix: str
    color: int
    menu_text: str  # คำอธิบายในเมนูเลือกหมวด (ไม่เกิน 100 ตัวอักษร)
    welcome: str
    questions: tuple = ()
    modal_title: str = ""


TICKET_TYPES = {
    "wl": TicketType(
        key="wl", label="ขอ White List", emoji="📝", prefix="wl", color=0x2ECC71,
        menu_text="สมัครเข้าเล่นเซิฟ (กรอก Steam + แบบสอบถาม)", modal_title="คำขอ White List",
        welcome=("{user} ได้รับคำขอแล้ว แอดมินจะตรวจข้อมูลด้านล่างและตอบในห้องนี้ภายใน 24 ชม. "
                 "อย่าเพิ่งออกจากเซิฟ Discord นะ"),
        questions=(
            Question("steam", "Steam ID หรือลิงก์โปรไฟล์ Steam", required=True, max_length=200,
                     placeholder="เช่น https://steamcommunity.com/id/xxx หรือ 7656119xxxxxxxxxx"),
            Question("username", "Username ในเกม (อังกฤษ ไม่มีเว้นวรรค)", required=True,
                     max_length=32, placeholder="เช่น Somchai_99"),
            Question("online", "ปกติออนช่วงไหน (วัน/เวลา)", max_length=100),
            Question("source", "รู้จักเซิฟจากไหน / ใครชวนมา", max_length=100),
            Question("code", "รหัสลับที่ซ่อนอยู่ในห้องกฎ", required=True, max_length=100),
        ),
    ),
    "donate": TicketType(
        key="donate", label="Donate", emoji="💝", prefix="donate", color=COLOR_DONATE,
        menu_text="สนับสนุนเซิฟ รับของขอบคุณในเกม",
        welcome="{user} ยินดีต้อนรับสู่ห้อง Donate 💝 ดูวิธีใช้และรายการด้านล่างได้เลย",
    ),
    "bug": TicketType(
        key="bug", label="แจ้งบั๊ก / ปัญหาเซิฟ", emoji="🐛", prefix="bug", color=0x3498DB,
        menu_text="เข้าเกมไม่ได้ หลุดบ่อย ของหาย", modal_title="แจ้งบั๊ก / ปัญหาเซิฟ",
        welcome=("{user} แนบรูป error หรือไฟล์ `console.txt` ในห้องนี้ได้เลย\n"
                 "ไฟล์อยู่ที่ `C:\\Users\\<ชื่อเครื่อง>\\Zomboid\\console.txt`"),
        questions=(
            Question("issue", "อาการที่เจอ", paragraph=True, required=True, max_length=1000),
            Question("where", "เกิดตอนไหน / ตรงไหนในเกม", max_length=200),
            Question("repro", "ทำซ้ำแล้วเกิดอีกไหม", max_length=100),
        ),
    ),
    "report": TicketType(
        key="report", label="รีพอร์ตผู้เล่น", emoji="🚨", prefix="report", color=0xE74C3C,
        menu_text="คนทำผิดกฎ (แนบหลักฐานในห้องได้)", modal_title="รีพอร์ตผู้เล่น",
        welcome="{user} แนบหลักฐาน (รูป/คลิป) ในห้องนี้ ทีมจะตรวจแล้วแจ้งผล ห้องนี้เห็นแค่คุณกับทีมแอดมิน",
        questions=(
            Question("target", "ชื่อผู้เล่นที่รีพอร์ต", required=True, max_length=100),
            Question("what", "เกิดอะไรขึ้น", paragraph=True, required=True, max_length=1000),
            Question("when", "เวลาและตำแหน่งในเกม", max_length=200),
        ),
    ),
    "help": TicketType(
        key="help", label="ติดต่อแอดมิน", emoji="💬", prefix="help", color=0x95A5A6,
        menu_text="เรื่องอื่นๆ", modal_title="ติดต่อแอดมิน",
        welcome="{user} แอดมินจะมาตอบในห้องนี้ เพิ่มรายละเอียดหรือแนบรูปได้เลย",
        questions=(
            Question("topic", "เรื่องที่ต้องการติดต่อ", paragraph=True, required=True, max_length=1000),
        ),
    ),
}

# username/password ถูกใส่ลงคำสั่ง adduser "..." "..." จึงห้ามมี " หรือเว้นวรรค
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,32}$")
PASSWORD_RE = re.compile(r"^[A-Za-z0-9_.@#!$%^&*+=\-]{4,32}$")
ITEM_CODE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,20}$")
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
MAX_CART_LINES = 5


def valid_username(name: str) -> bool:
    return bool(USERNAME_RE.fullmatch(name or ""))


def valid_password(pw: str) -> bool:
    return bool(PASSWORD_RE.fullmatch(pw or ""))


def generate_password(length: int = 8) -> str:
    length = max(6, min(length, 32))
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def normalize_code(text: str) -> str:
    return re.sub(r"\s+", "", text or "").casefold()


def parse_baht(text: str) -> int:
    """'49', '49.50', '1,200' → สตางค์ (int); โยน ValueError ถ้าไม่ใช่ตัวเลขบวก"""
    cleaned = (text or "").replace(",", "").replace("฿", "").replace("บาท", "").strip()
    if not re.fullmatch(r"\d+(\.\d{1,2})?", cleaned):
        raise ValueError(text)
    whole, _, frac = cleaned.partition(".")
    satang = int(whole) * 100 + int((frac + "00")[:2])
    if satang <= 0:
        raise ValueError(text)
    return satang


def fmt_baht(satang: int) -> str:
    satang = int(satang or 0)
    if satang % 100 == 0:
        return f"฿{satang // 100:,}"
    return f"฿{satang / 100:,.2f}"


# =====================================================================
# Config (Railway Variables / .env)
# =====================================================================

class ConfigError(Exception):
    pass


@dataclass
class Config:
    token: str
    guild_id: int
    survivor_role: int
    staff_roles: list
    ticket_channel: int
    transcripts: int
    admin_roles: list = field(default_factory=list)
    member_role: int = 0
    whitelist_log: int = 0
    mod_logs: int = 0
    donate_log: int = 0
    rules_channel: int = 0
    connect_info_channel: int = 0
    steam_api_key: str = ""
    steam_required: bool = True
    steam_require_pz: bool = False
    stripe_secret_key: str = ""
    stripe_currency: str = "thb"
    stripe_payment_methods: list = field(default_factory=list)
    stripe_session_minutes: int = 60
    donate_min: int = 1000  # สตางค์ (Stripe รับเงินบาทขั้นต่ำ ฿10)
    donate_max_qty: int = 99
    secret_code: str = ""
    game_version: str = ""
    max_open_per_type: int = 1
    allow_owner_close: bool = True
    dm_transcript: bool = False
    ping_staff_on_new: bool = True
    password_length: int = 8
    set_nickname: bool = True
    auto_close_after_decision: bool = True
    utc_offset: int = 7
    accent_color: int = 0x22C7E8
    welcome_banner_url: str = ""
    rcon_enabled: bool = False
    rcon_host: str = "127.0.0.1"
    rcon_port: int = 27015
    rcon_password: str = ""
    data_dir: Path = BASE_DIR / "data"
    on_railway: bool = False
    has_volume: bool = False

    @property
    def donate_enabled(self) -> bool:
        return bool(self.stripe_secret_key)


_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n"}


def _str(env, key, default=""):
    value = env.get(key)
    if value is None:
        return default
    value = re.sub(r"\s+#.*$", "", str(value)).strip()  # กันคอมเมนต์ท้ายบรรทัดที่ติดมากับค่า
    return value or default


def _bool(env, key, default):
    value = _str(env, key).lower()
    if not value:
        return default
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(f"{key} ต้องเป็น true หรือ false (ได้ {value!r})")


def _int(env, key, default=0):
    value = _str(env, key)
    if not value:
        return default
    if not re.fullmatch(r"-?\d+", value):
        raise ConfigError(f"{key} ต้องเป็นตัวเลข (ได้ {value!r})")
    return int(value)


def _ids(env, key):
    out = []
    for part in re.split(r"[,\s]+", _str(env, key)):
        if not part:
            continue
        if not part.isdigit():
            raise ConfigError(f"{key} ต้องเป็น ID ตัวเลข คั่นด้วยจุลภาค (เจอ {part!r})")
        out.append(int(part))
    return out


def _color(env, key, default):
    value = _str(env, key).lstrip("#")
    if not value:
        return default
    try:
        return int(value, 16)
    except ValueError:
        raise ConfigError(f"{key} ต้องเป็นสี hex เช่น 22C7E8 (ได้ {value!r})")


def load_config(env: Mapping[str, str]) -> Config:
    problems = []

    def need(key, value):
        if not value:
            problems.append(key)
        return value

    volume = _str(env, "RAILWAY_VOLUME_MOUNT_PATH")
    data_dir = Path(_str(env, "DATA_DIR") or volume or str(BASE_DIR / "data"))
    try:
        donate_min = parse_baht(_str(env, "DONATE_MIN_BAHT", "10"))
    except ValueError:
        raise ConfigError("DONATE_MIN_BAHT ต้องเป็นตัวเลขบาท เช่น 10")
    cfg = Config(
        token=need("DISCORD_TOKEN", _str(env, "DISCORD_TOKEN")),
        guild_id=need("GUILD_ID", _int(env, "GUILD_ID")),
        survivor_role=need("ROLE_SURVIVOR", _int(env, "ROLE_SURVIVOR")),
        staff_roles=need("ROLE_STAFF", _ids(env, "ROLE_STAFF")),
        ticket_channel=need("TICKET_CHANNEL_ID", _int(env, "TICKET_CHANNEL_ID")),
        transcripts=need("TRANSCRIPT_CHANNEL_ID", _int(env, "TRANSCRIPT_CHANNEL_ID")),
        admin_roles=_ids(env, "ROLE_ADMIN"),
        member_role=_int(env, "ROLE_MEMBER"),
        whitelist_log=_int(env, "WHITELIST_LOG_CHANNEL_ID"),
        mod_logs=_int(env, "MOD_LOG_CHANNEL_ID"),
        donate_log=_int(env, "DONATE_LOG_CHANNEL_ID"),
        rules_channel=_int(env, "RULES_CHANNEL_ID"),
        connect_info_channel=_int(env, "CONNECT_INFO_CHANNEL_ID"),
        steam_api_key=_str(env, "STEAM_API_KEY"),
        steam_required=_bool(env, "STEAM_REQUIRED", True),
        steam_require_pz=_bool(env, "STEAM_REQUIRE_PZ", False),
        stripe_secret_key=_str(env, "STRIPE_SECRET_KEY"),
        stripe_currency=_str(env, "STRIPE_CURRENCY", "thb").lower(),
        stripe_payment_methods=[p for p in re.split(r"[,\s]+", _str(env, "STRIPE_PAYMENT_METHODS")) if p],
        stripe_session_minutes=min(1440, max(31, _int(env, "STRIPE_SESSION_MINUTES", 60))),
        donate_min=donate_min,
        donate_max_qty=max(1, min(999, _int(env, "DONATE_MAX_QTY", 99))),
        secret_code=_str(env, "SECRET_CODE"),
        game_version=_str(env, "GAME_VERSION"),
        max_open_per_type=max(1, _int(env, "MAX_OPEN_PER_TYPE", 1)),
        allow_owner_close=_bool(env, "ALLOW_OWNER_CLOSE", True),
        dm_transcript=_bool(env, "DM_TRANSCRIPT", False),
        ping_staff_on_new=_bool(env, "PING_STAFF_ON_NEW", True),
        password_length=_int(env, "PASSWORD_LENGTH", 8),
        set_nickname=_bool(env, "SET_NICKNAME", True),
        auto_close_after_decision=_bool(env, "AUTO_CLOSE_AFTER_DECISION", True),
        utc_offset=_int(env, "UTC_OFFSET", 7),
        accent_color=_color(env, "ACCENT_COLOR", 0x22C7E8),
        welcome_banner_url=_str(env, "WELCOME_BANNER_URL"),
        rcon_enabled=_bool(env, "RCON_ENABLED", False),
        rcon_host=_str(env, "RCON_HOST", "127.0.0.1"),
        rcon_port=_int(env, "RCON_PORT", 27015),
        rcon_password=_str(env, "RCON_PASSWORD"),
        data_dir=data_dir,
        on_railway=bool(_str(env, "RAILWAY_ENVIRONMENT_NAME") or _str(env, "RAILWAY_SERVICE_ID")),
        has_volume=bool(volume) or bool(_str(env, "DATA_DIR")),
    )
    if cfg.token and len(cfg.token) < 50:
        problems.append("DISCORD_TOKEN (สั้นผิดปกติ — ก๊อปมาไม่ครบ?)")
    if cfg.steam_required and not cfg.steam_api_key:
        problems.append("STEAM_API_KEY (ต้องมีเพื่อเช็ค Steam — หรือตั้ง STEAM_REQUIRED=false)")
    if cfg.stripe_secret_key and not re.match(r"^(sk|rk)_(test|live)_", cfg.stripe_secret_key):
        problems.append("STRIPE_SECRET_KEY (ต้องขึ้นต้นด้วย sk_live_ / sk_test_ / rk_live_ / rk_test_)")
    if cfg.rcon_enabled and not cfg.rcon_password:
        problems.append("RCON_PASSWORD (เปิด RCON แล้วแต่ยังไม่ใส่รหัส)")
    if problems:
        raise ConfigError("Variables ใน Railway ยังไม่ครบ / ไม่ถูกต้อง:\n  - " + "\n  - ".join(problems))
    return cfg


# =====================================================================
# Database (SQLite — อยู่ใน Railway Volume)
# =====================================================================

ORDER_OPEN = ("cart", "review", "pending", "expired")


class Database:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                number INTEGER NOT NULL,
                channel_id INTEGER UNIQUE,
                owner_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                claimed_by INTEGER,
                decision TEXT,
                answers TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                closed_at TEXT,
                transcript_saved INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_owner ON tickets(owner_id, type, status);
            CREATE TABLE IF NOT EXISTS counters(type TEXT PRIMARY KEY, value INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS whitelist(
                username TEXT PRIMARY KEY COLLATE NOCASE,
                discord_id INTEGER NOT NULL,
                approved_by INTEGER,
                approved_at TEXT,
                ticket_id INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                steam_id TEXT
            );
            CREATE TABLE IF NOT EXISTS sensitive(message_id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS steam_links(
                discord_id INTEGER PRIMARY KEY,
                steam_id TEXT NOT NULL UNIQUE,
                info TEXT NOT NULL DEFAULT '{}',
                linked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS items(
                code TEXT PRIMARY KEY COLLATE NOCASE,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                sort INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                thread_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                lines TEXT NOT NULL DEFAULT '[]',
                total INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'cart',
                message_id INTEGER,
                paid_message_id INTEGER,
                stripe_session TEXT,
                stripe_url TEXT,
                stripe_expires INTEGER,
                attempt INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                delivered_at TEXT,
                delivered_by INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_thread ON orders(thread_id, status);
            """
        )
        try:  # ฐานข้อมูลจากเวอร์ชันก่อนไม่มีคอลัมน์ steam_id
            self.conn.execute("ALTER TABLE whitelist ADD COLUMN steam_id TEXT")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    # --- tickets ---
    def next_number(self, ttype: str) -> int:
        with self.conn:
            self.conn.execute(
                "INSERT INTO counters(type, value) VALUES(?, 1) "
                "ON CONFLICT(type) DO UPDATE SET value = value + 1", (ttype,))
            return self.conn.execute("SELECT value FROM counters WHERE type=?", (ttype,)).fetchone()[0]

    def create_ticket(self, ttype, number, channel_id, owner_id, answers) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO tickets(type, number, channel_id, owner_id, answers, created_at) VALUES(?,?,?,?,?,?)",
                (ttype, number, channel_id, owner_id, json.dumps(answers, ensure_ascii=False), self._now()))
            return cur.lastrowid

    def by_channel(self, channel_id):
        return self.conn.execute("SELECT * FROM tickets WHERE channel_id=?", (channel_id,)).fetchone()

    def by_id(self, ticket_id):
        return self.conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()

    def open_tickets(self, owner_id, ttype):
        return self.conn.execute("SELECT * FROM tickets WHERE owner_id=? AND type=? AND status='open'",
                                 (owner_id, ttype)).fetchall()

    def set_status(self, ticket_id, status):
        with self.conn:
            if status == "closed":
                self.conn.execute("UPDATE tickets SET status=?, closed_at=? WHERE id=?",
                                  (status, self._now(), ticket_id))
            else:
                self.conn.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))

    def set_claim(self, ticket_id, user_id):
        with self.conn:
            self.conn.execute("UPDATE tickets SET claimed_by=? WHERE id=?", (user_id, ticket_id))

    def set_decision(self, ticket_id, decision):
        with self.conn:
            self.conn.execute("UPDATE tickets SET decision=? WHERE id=?", (decision, ticket_id))

    def set_transcript_saved(self, ticket_id):
        with self.conn:
            self.conn.execute("UPDATE tickets SET transcript_saved=1 WHERE id=?", (ticket_id,))

    # --- whitelist ---
    def wl_get(self, username):
        return self.conn.execute("SELECT * FROM whitelist WHERE username=?", (username,)).fetchone()

    def wl_by_user(self, discord_id, active_only=True):
        q = "SELECT * FROM whitelist WHERE discord_id=?" + (" AND active=1" if active_only else "")
        return self.conn.execute(q, (discord_id,)).fetchall()

    def wl_add(self, username, discord_id, approved_by, ticket_id, steam_id=None):
        with self.conn:
            self.conn.execute(
                "INSERT INTO whitelist(username, discord_id, approved_by, approved_at, ticket_id, active, steam_id) "
                "VALUES(?,?,?,?,?,1,?) ON CONFLICT(username) DO UPDATE SET discord_id=excluded.discord_id, "
                "approved_by=excluded.approved_by, approved_at=excluded.approved_at, "
                "ticket_id=excluded.ticket_id, active=1, steam_id=excluded.steam_id",
                (username, discord_id, approved_by, self._now(), ticket_id, steam_id))

    def wl_deactivate(self, username):
        with self.conn:
            self.conn.execute("UPDATE whitelist SET active=0 WHERE username=?", (username,))

    # --- transcript redaction ---
    def mark_sensitive(self, message_id):
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO sensitive(message_id) VALUES(?)", (message_id,))

    def sensitive_ids(self) -> set:
        return {row[0] for row in self.conn.execute("SELECT message_id FROM sensitive")}

    # --- steam ---
    def steam_get(self, discord_id):
        return self.conn.execute("SELECT * FROM steam_links WHERE discord_id=?", (discord_id,)).fetchone()

    def steam_by_steam(self, steam_id):
        return self.conn.execute("SELECT * FROM steam_links WHERE steam_id=?", (str(steam_id),)).fetchone()

    def steam_save(self, discord_id, info: dict):
        with self.conn:
            self.conn.execute(
                "INSERT INTO steam_links(discord_id, steam_id, info, linked_at) VALUES(?,?,?,?) "
                "ON CONFLICT(discord_id) DO UPDATE SET steam_id=excluded.steam_id, info=excluded.info, "
                "linked_at=excluded.linked_at",
                (discord_id, str(info["steam_id"]), json.dumps(info, ensure_ascii=False), self._now()))

    def steam_unlink(self, discord_id) -> bool:
        with self.conn:
            return self.conn.execute("DELETE FROM steam_links WHERE discord_id=?", (discord_id,)).rowcount > 0

    # --- items (รายการ Donate) ---
    def item_get(self, code):
        return self.conn.execute("SELECT * FROM items WHERE code=?", ((code or "").strip(),)).fetchone()

    def items(self, active_only=True):
        q = "SELECT * FROM items" + (" WHERE active=1" if active_only else "") + " ORDER BY sort, code"
        return self.conn.execute(q).fetchall()

    def item_add(self, code, name, price, description="", sort=0):
        with self.conn:
            self.conn.execute(
                "INSERT INTO items(code, name, price, description, active, sort, updated_at) VALUES(?,?,?,?,1,?,?)",
                (code, name, price, description, sort, self._now()))

    def item_update(self, old_code, **fields):
        """fields: code (รหัสใหม่) / name / price / description / active / sort — ค่า None = ไม่แก้"""
        allowed = {"code", "name", "price", "description", "active", "sort"}
        sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not sets:
            return
        sets["updated_at"] = self._now()
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE items SET {cols} WHERE code=?", (*sets.values(), old_code))

    def item_delete(self, code) -> bool:
        with self.conn:
            return self.conn.execute("DELETE FROM items WHERE code=?", (code,)).rowcount > 0

    # --- orders ---
    def order_create(self, ticket_id, thread_id, owner_id) -> int:
        with self.conn:
            return self.conn.execute(
                "INSERT INTO orders(ticket_id, thread_id, owner_id, status, created_at) VALUES(?,?,?,'cart',?)",
                (ticket_id, thread_id, owner_id, self._now())).lastrowid

    def order_get(self, order_id):
        return self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()

    def order_by_message(self, message_id):
        return self.conn.execute("SELECT * FROM orders WHERE message_id=? OR paid_message_id=?",
                                 (message_id, message_id)).fetchone()

    def order_open_in_thread(self, thread_id):
        marks = ",".join("?" * len(ORDER_OPEN))
        return self.conn.execute(
            f"SELECT * FROM orders WHERE thread_id=? AND status IN ({marks}) ORDER BY id DESC LIMIT 1",
            (thread_id, *ORDER_OPEN)).fetchone()

    def orders_with_status(self, *statuses, limit=50):
        marks = ",".join("?" * len(statuses))
        return self.conn.execute(f"SELECT * FROM orders WHERE status IN ({marks}) ORDER BY id DESC LIMIT ?",
                                 (*statuses, limit)).fetchall()

    def order_update(self, order_id, **fields):
        allowed = {"lines", "total", "status", "message_id", "paid_message_id", "stripe_session", "stripe_url",
                   "stripe_expires", "attempt", "paid_at", "delivered_at", "delivered_by"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if "lines" in sets and not isinstance(sets["lines"], str):
            sets["lines"] = json.dumps(sets["lines"], ensure_ascii=False)
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE orders SET {cols} WHERE id=?", (*sets.values(), order_id))


def steam_info_of(row) -> dict:
    if not row:
        return {}
    try:
        return json.loads(row["info"] or "{}")
    except (TypeError, ValueError):
        return {"steam_id": row["steam_id"]}


def lines_of(order) -> list:
    try:
        return json.loads(order["lines"] or "[]")
    except (TypeError, ValueError):
        return []


# =====================================================================
# ตะกร้า Donate (logic ล้วน — ไม่แตะ Discord)
# =====================================================================

class CartError(Exception):
    pass


def cart_add(lines: list, item, qty: int, max_qty: int) -> list:
    """เพิ่ม/รวมรายการ คืน list ใหม่; item = แถวจากตาราง items"""
    if item is None or not item["active"]:
        raise CartError("ไม่พบรหัสนี้ หรือรายการนี้ปิดอยู่ — ดูรหัสในรายการด้านบน")
    if qty < 1:
        raise CartError("จำนวนต้องมากกว่า 0")
    new = [dict(line) for line in lines]
    for line in new:
        if line["code"].casefold() == item["code"].casefold():
            if line["qty"] + qty > max_qty:
                raise CartError(f"รายการเดียวกันใส่ได้ไม่เกิน {max_qty} ชิ้นต่อรอบ")
            line["qty"] += qty
            line.update(name=item["name"], unit=item["price"])
            return new
    if len(new) >= MAX_CART_LINES:
        raise CartError(f"ใส่ได้สูงสุด {MAX_CART_LINES} รายการต่อรอบ — ลบรายการเดิมก่อน หรือส่งรอบนี้แล้วทำรอบใหม่")
    if qty > max_qty:
        raise CartError(f"ใส่ได้ไม่เกิน {max_qty} ชิ้นต่อรายการ")
    new.append({"code": item["code"], "name": item["name"], "unit": item["price"], "qty": qty})
    return new


def cart_total(lines: list) -> int:
    return sum(int(line["unit"]) * int(line["qty"]) for line in lines)


def cart_text(lines: list) -> str:
    if not lines:
        return "_ยังไม่มีรายการ — กด ➕ เพิ่มรายการ_"
    rows = []
    for i, line in enumerate(lines, 1):
        name = discord.utils.escape_markdown(line["name"])
        rows.append(f"**{i}.** `{line['code']}` {name}\n"
                    f"　{fmt_baht(line['unit'])} × {line['qty']} = **{fmt_baht(line['unit'] * line['qty'])}**")
    return "\n".join(rows)


def catalog_text(items: list, limit: int = 3500) -> str:
    if not items:
        return "_ยังไม่มีรายการ — แอดมินกำลังเตรียม_"
    out, used = [], 0
    for idx, item in enumerate(items):
        row = f"`{item['code']}` **{discord.utils.escape_markdown(item['name'])}** — {fmt_baht(item['price'])}"
        if item["description"]:
            row += f"\n　{discord.utils.escape_markdown(item['description'])}"
        if used + len(row) > limit:
            out.append(f"…และอีก {len(items) - idx} รายการ (แอดมินดูทั้งหมดได้ด้วย /item list)")
            break
        out.append(row)
        used += len(row) + 1
    return "\n".join(out)


# =====================================================================
# Stripe (Checkout Session — หน้าจ่ายของ Stripe มี PromptPay QR / บัตร)
# =====================================================================

class StripeError(Exception):
    pass


def stripe_form(data, prefix="") -> list:
    """dict/list ซ้อนกัน → [(key, value)] แบบ bracket ที่ Stripe ใช้"""
    out = []
    if isinstance(data, dict):
        for k, v in data.items():
            out += stripe_form(v, f"{prefix}[{k}]" if prefix else str(k))
    elif isinstance(data, (list, tuple)):
        for i, v in enumerate(data):
            out += stripe_form(v, f"{prefix}[{i}]")
    elif isinstance(data, bool):
        out.append((prefix, "true" if data else "false"))
    elif data is not None:
        out.append((prefix, str(data)))
    return out


class StripeClient:
    API = "https://api.stripe.com/v1"

    def __init__(self, session: aiohttp.ClientSession, secret_key: str, base_url: str = None):
        self.session, self.key, self.base = session, secret_key, base_url or self.API

    async def _request(self, method: str, path: str, data: dict = None, idempotency_key: str = None) -> dict:
        headers = {"Authorization": f"Bearer {self.key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        try:
            async with self.session.request(method, f"{self.base}{path}", data=stripe_form(data or {}) or None,
                                            headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
                body = await r.json(content_type=None)
                if r.status >= 400:
                    err = (body or {}).get("error", {}) if isinstance(body, dict) else {}
                    raise StripeError(err.get("message") or f"Stripe ตอบ HTTP {r.status}")
                return body
        except asyncio.TimeoutError:
            raise StripeError("Stripe ตอบช้า ลองใหม่อีกครั้ง")
        except aiohttp.ClientError as e:
            raise StripeError(f"ติดต่อ Stripe ไม่ได้ ({type(e).__name__})")

    async def create_checkout(self, *, order_id: int, owner_id: int, lines: list, currency: str,
                              success_url: str, expires_at: int, payment_methods: list,
                              idempotency_key: str) -> dict:
        data = {
            "mode": "payment",
            "submit_type": "donate",
            "locale": "th",
            "success_url": success_url,
            "client_reference_id": f"order-{order_id}",
            "expires_at": expires_at,
            "metadata": {"order_id": order_id, "discord_id": owner_id},
            "payment_intent_data": {"metadata": {"order_id": order_id, "discord_id": owner_id}},
            "line_items": [{
                "quantity": line["qty"],
                "price_data": {"currency": currency, "unit_amount": line["unit"],
                               "product_data": {"name": f"[{line['code']}] {line['name']}"[:250]}},
            } for line in lines],
        }
        if payment_methods:
            data["payment_method_types"] = payment_methods
        return await self._request("POST", "/checkout/sessions", data, idempotency_key)

    async def get_session(self, session_id: str) -> dict:
        return await self._request("GET", f"/checkout/sessions/{session_id}")

    async def expire_session(self, session_id: str) -> dict:
        return await self._request("POST", f"/checkout/sessions/{session_id}/expire")

    async def ping(self) -> dict:
        # ใช้สิทธิ์เดียวกับที่บอทใช้จริง (Checkout Sessions) — restricted key ก็เช็คได้
        return await self._request("GET", "/checkout/sessions?limit=1")


# =====================================================================
# Steam (พิมพ์ Steam ID → เช็คผ่าน Steam Web API)
# =====================================================================

STEAM_ID64_BASE = 76561197960265728
PZ_APPID = 108600


class SteamError(Exception):
    def __init__(self, message: str, admin_problem: bool = False):
        super().__init__(message)
        self.admin_problem = admin_problem  # True = ปัญหาฝั่งระบบ (key ผิด/Steam ล่ม) ไม่ใช่ผู้เล่นกรอกผิด


def parse_steam_input(text: str):
    """คืน (steamid64, vanity) — อย่างใดอย่างหนึ่ง; โยน SteamError ถ้ารูปแบบผิด"""
    text = (text or "").strip()
    if not text:
        raise SteamError("กรุณาใส่ Steam ID หรือลิงก์โปรไฟล์")
    m = re.search(r"steamcommunity\.com/profiles/(\d{17})", text)
    if m:
        return m.group(1), None
    m = re.search(r"steamcommunity\.com/id/([\w\-.]+)", text)
    if m:
        return None, m.group(1)
    if text.isdigit() and len(text) == 17 and text.startswith("7656119"):
        return text, None
    m = re.fullmatch(r"STEAM_[0-5]:([01]):(\d+)", text, re.IGNORECASE)
    if m:
        return str(STEAM_ID64_BASE + int(m.group(2)) * 2 + int(m.group(1))), None
    m = re.fullmatch(r"\[?U:1:(\d+)\]?", text, re.IGNORECASE)
    if m:
        return str(STEAM_ID64_BASE + int(m.group(1))), None
    if text.isdigit() and 1 <= len(text) <= 10:  # Friend Code ในหน้า Add Friend ของ Steam
        return str(STEAM_ID64_BASE + int(text)), None
    if re.fullmatch(r"[\w\-.]{2,32}", text):
        return None, text
    raise SteamError("รูปแบบ Steam ID ไม่ถูกต้อง — ใส่ลิงก์โปรไฟล์ Steam (steamcommunity.com/...) "
                     "หรือ SteamID64 (17 หลัก ขึ้นต้น 7656119)")


def steamid32(id64: str) -> str:
    try:
        n = int(id64) - STEAM_ID64_BASE
        return f"STEAM_0:{n % 2}:{n // 2}"
    except (TypeError, ValueError):
        return ""


class SteamClient:
    API = "https://api.steampowered.com"

    def __init__(self, session: aiohttp.ClientSession, api_key: str, base_url: str = None):
        self.session = session
        self.api_key = api_key
        self.base = base_url or self.API

    async def _get(self, path: str, **params) -> dict:
        if not self.api_key:
            raise SteamError("ยังไม่ได้ตั้ง STEAM_API_KEY", admin_problem=True)
        params["key"] = self.api_key
        try:
            async with self.session.get(f"{self.base}{path}", params=params,
                                        timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status in (401, 403):
                    raise SteamError("STEAM_API_KEY ไม่ถูกต้อง (Steam ตอบ 403)", admin_problem=True)
                if r.status == 429:
                    raise SteamError("Steam จำกัดการเรียกชั่วคราว ลองใหม่ในอีกสักครู่", admin_problem=True)
                if r.status != 200:
                    raise SteamError(f"Steam API ตอบ HTTP {r.status} ลองใหม่อีกครั้ง", admin_problem=True)
                return await r.json(content_type=None)
        except asyncio.TimeoutError:
            raise SteamError("Steam ตอบช้า ลองใหม่อีกครั้ง", admin_problem=True)
        except aiohttp.ClientError as e:
            raise SteamError(f"ติดต่อ Steam ไม่ได้ ({type(e).__name__})", admin_problem=True)

    async def resolve(self, text: str) -> str:
        id64, vanity = parse_steam_input(text)
        if id64:
            return id64
        data = await self._get("/ISteamUser/ResolveVanityURL/v1/", vanityurl=vanity)
        resp = (data or {}).get("response", {})
        if resp.get("success") == 1 and resp.get("steamid"):
            return str(resp["steamid"])
        raise SteamError(f"ไม่เจอโปรไฟล์ Steam ชื่อ \"{vanity}\" — ลองใส่ลิงก์โปรไฟล์เต็มๆ แทน")

    async def lookup(self, text: str) -> dict:
        id64 = await self.resolve(text)
        data = await self._get("/ISteamUser/GetPlayerSummaries/v2/", steamids=id64)
        players = (data or {}).get("response", {}).get("players", [])
        if not players:
            raise SteamError("ไม่พบบัญชี Steam นี้ — เช็คลิงก์/ID อีกครั้ง")
        p = players[0]
        info = {
            "steam_id": id64,
            "persona": p.get("personaname", ""),
            "profile_url": p.get("profileurl") or f"https://steamcommunity.com/profiles/{id64}",
            "avatar": p.get("avatarfull", ""),
            "visibility": p.get("communityvisibilitystate", 0),
            "created": p.get("timecreated"),
            "country": p.get("loccountrycode", ""),
            "pz_status": "unknown",
            "pz_minutes": None,
            "vac_bans": None,
            "game_bans": None,
            "community_banned": None,
            "days_since_last_ban": None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            owned = await self._get("/IPlayerService/GetOwnedGames/v1/", steamid=id64,
                                    include_played_free_games=1, **{"appids_filter[0]": PZ_APPID})
            resp = (owned or {}).get("response", {})
            games = [g for g in resp.get("games", []) if g.get("appid") == PZ_APPID]
            if games:
                info["pz_status"], info["pz_minutes"] = "owned", int(games[0].get("playtime_forever", 0))
            elif "game_count" in resp:
                info["pz_status"] = "not_owned"
            else:
                info["pz_status"] = "private"
        except SteamError as e:
            log.warning("เช็คเกม PZ ไม่ได้: %s", e)
        try:
            bans = await self._get("/ISteamUser/GetPlayerBans/v1/", steamids=id64)
            b = ((bans or {}).get("players") or [{}])[0]
            info.update(vac_bans=b.get("NumberOfVACBans"), game_bans=b.get("NumberOfGameBans"),
                        community_banned=b.get("CommunityBanned"), days_since_last_ban=b.get("DaysSinceLastBan"))
        except SteamError as e:
            log.warning("เช็คประวัติแบน Steam ไม่ได้: %s", e)
        return info


def steam_summary(info: dict) -> list:
    if not info:
        return ["ยังไม่ได้เชื่อม Steam"]
    persona = discord.utils.escape_markdown(info.get("persona") or "?")
    lines = [f"[{persona}]({info.get('profile_url')})"
             + (f" · {country_flag(info.get('country'))}" if info.get("country") else ""),
             f"`{info.get('steam_id')}` · `{steamid32(info.get('steam_id'))}`"]
    lines.append("โปรไฟล์: " + ("สาธารณะ" if info.get("visibility") == 3 else "ส่วนตัว/เพื่อนเท่านั้น"))
    return lines


def steam_checks(info: dict) -> list:
    if not info:
        return []
    out = []
    created = info.get("created")
    if created:
        days = (datetime.now(timezone.utc) - datetime.fromtimestamp(created, timezone.utc)).days
        out.append(("⚠️ " if days < 90 else "✅ ") + f"บัญชี Steam อายุ {fmt_age(days)}")
    else:
        out.append("➖ ไม่ทราบอายุบัญชี Steam (โปรไฟล์ไม่สาธารณะ)")
    status, minutes = info.get("pz_status"), info.get("pz_minutes")
    if status == "owned":
        hours = (minutes or 0) / 60
        out.append(("⚠️ " if hours < 2 else "✅ ") + f"Project Zomboid {hours:,.0f} ชม.")
    elif status == "not_owned":
        out.append("❌ ไม่พบเกม Project Zomboid ในบัญชีนี้")
    elif status == "private":
        out.append("➖ ซ่อนข้อมูลเกม (Game details ไม่สาธารณะ)")
    else:
        out.append("➖ เช็คเกมไม่ได้")
    vac, game, community = info.get("vac_bans"), info.get("game_bans"), info.get("community_banned")
    if vac is None and game is None:
        out.append("➖ เช็คประวัติแบนไม่ได้")
    elif vac or game or community:
        parts = [f"VAC {vac or 0}", f"Game {game or 0}"] + (["Community"] if community else [])
        last = info.get("days_since_last_ban")
        out.append("⚠️ เคยโดนแบน: " + " · ".join(parts) + (f" (ล่าสุด {last} วันก่อน)" if last is not None else ""))
    else:
        out.append("✅ ไม่มีประวัติแบน Steam")
    return out


def fmt_age(days: int) -> str:
    if days >= 365:
        return f"{days / 365:.1f} ปี"
    return f"{days} วัน"


def country_flag(code: str) -> str:
    if not code or len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


# =====================================================================
# RCON (ไม่บังคับ — บน Railway ต่อเข้าเครื่องในบ้านผ่าน Radmin ไม่ได้ ปล่อยปิดไว้)
# =====================================================================

class RconError(Exception):
    pass


class Rcon:
    AUTH, EXEC, AUTH_RESPONSE = 3, 2, 2

    def __init__(self, host, port, password, timeout=6.0):
        self.host, self.port, self.password, self.timeout = host, port, password, timeout
        self._lock = asyncio.Lock()

    @staticmethod
    def _packet(req_id: int, ptype: int, body: str) -> bytes:
        data = struct.pack("<ii", req_id, ptype) + body.encode("utf-8") + b"\x00\x00"
        return struct.pack("<i", len(data)) + data

    async def _read(self, reader):
        size = struct.unpack("<i", await reader.readexactly(4))[0]
        if size < 10 or size > 1_000_000:
            raise RconError(f"แพ็กเก็ตผิดรูปแบบ (size={size})")
        data = await reader.readexactly(size)
        req_id, ptype = struct.unpack("<ii", data[:8])
        return req_id, ptype, data[8:-2].decode("utf-8", errors="replace")

    async def command(self, cmd: str) -> str:
        async with self._lock:
            return await asyncio.wait_for(self._command(cmd), timeout=self.timeout)

    async def _command(self, cmd: str) -> str:
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
        except OSError as e:
            raise RconError(f"ต่อ {self.host}:{self.port} ไม่ได้ ({e.strerror or e})")
        try:
            writer.write(self._packet(1, self.AUTH, self.password))
            await writer.drain()
            while True:
                req_id, ptype, _ = await self._read(reader)
                if ptype == self.AUTH_RESPONSE:
                    if req_id == -1:
                        raise RconError("รหัส RCON ผิด")
                    break
            writer.write(self._packet(2, self.EXEC, cmd))
            await writer.drain()
            _, _, body = await self._read(reader)
            return body.strip()
        except asyncio.IncompleteReadError:
            raise RconError("เซิฟตัดการเชื่อมต่อ RCON")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


# =====================================================================
# Transcript
# =====================================================================

TRANSCRIPT_CSS = """
body{margin:0;background:#313338;color:#dbdee1;font:15px/1.45 "Segoe UI",Tahoma,"Noto Sans Thai",sans-serif}
header{background:#2b2d31;padding:20px 24px;border-bottom:1px solid #1e1f22}
header h1{margin:0 0 8px;font-size:20px;color:#f2f3f5}
header dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0;font-size:14px}
header dt{color:#949ba4}header dd{margin:0}
main{padding:12px 24px 40px;max-width:980px}
.m{display:flex;gap:12px;padding:8px 0}
.av{width:40px;height:40px;border-radius:50%;flex:none;background:#5865f2}
.h{display:flex;gap:8px;align-items:baseline}
.n{font-weight:600;color:#f2f3f5}.b{font-size:11px;background:#5865f2;color:#fff;border-radius:3px;padding:0 4px}
.t{font-size:12px;color:#949ba4}
.c{white-space:pre-wrap;word-wrap:break-word}
.e{border-left:4px solid #5865f2;background:#2b2d31;border-radius:4px;padding:8px 12px;margin-top:6px;max-width:560px}
.e b{display:block;color:#f2f3f5}.f{margin-top:6px}.f i{display:block;font-style:normal;font-weight:600;font-size:13px}
.a{display:block;margin-top:4px}.s{color:#949ba4;font-style:italic}
a{color:#00a8fc}
"""

_URL_RE = re.compile(r"(https?://[^\s<]+)")


def _fmt_text(text: str) -> str:
    return _URL_RE.sub(r'<a href="\1">\1</a>', html.escape(text or ""))


def render_transcript(meta: dict, messages: list, sensitive: set, tz) -> str:
    def ts(dt):
        return dt.astimezone(tz).strftime("%d/%m/%Y %H:%M")

    rows = "".join(f"<dt>{html.escape(k)}</dt><dd>{html.escape(str(v))}</dd>" for k, v in meta["rows"])
    parts = [
        "<!doctype html><html lang='th'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>{html.escape(meta['title'])}</title><style>{TRANSCRIPT_CSS}</style></head><body>",
        f"<header><h1>{html.escape(meta['title'])}</h1><dl>{rows}</dl></header><main>",
    ]
    for m in messages:
        avatar = (f"<img class='av' src='{html.escape(m['avatar'])}' alt=''>" if m.get("avatar")
                  else "<div class='av'></div>")
        bot_tag = "<span class='b'>BOT</span>" if m.get("bot") else ""
        if m["id"] in sensitive:
            body = "<div class='c s'>[ซ่อนข้อความที่มีรหัสผ่าน]</div>"
        else:
            body = f"<div class='c'>{_fmt_text(m.get('content', ''))}</div>" if m.get("content") else ""
            for e in m.get("embeds", []):
                inner = ""
                if e.get("title"):
                    inner += f"<b>{html.escape(e['title'])}</b>"
                if e.get("description"):
                    inner += f"<div class='c'>{_fmt_text(e['description'])}</div>"
                for name, value in e.get("fields", []):
                    inner += f"<div class='f'><i>{html.escape(name)}</i><span class='c'>{_fmt_text(value)}</span></div>"
                if inner:
                    body += f"<div class='e'>{inner}</div>"
            for name, url in m.get("attachments", []):
                body += f"<a class='a' href='{html.escape(url)}'>📎 {html.escape(name)}</a>"
        parts.append(
            f"<div class='m'>{avatar}<div><div class='h'><span class='n'>{html.escape(m['author'])}</span>"
            f"{bot_tag}<span class='t'>{ts(m['time'])}</span></div>{body}</div></div>")
    parts.append("</main></body></html>")
    return "".join(parts)


async def collect_messages(channel) -> list:
    out = []
    async for msg in channel.history(limit=5000, oldest_first=True):
        out.append({
            "id": msg.id,
            "author": msg.author.display_name,
            "avatar": msg.author.display_avatar.url if msg.author.display_avatar else "",
            "bot": msg.author.bot,
            "time": msg.created_at,
            "content": msg.clean_content,
            "attachments": [(a.filename, a.url) for a in msg.attachments],
            "embeds": [{"title": e.title or "", "description": e.description or "",
                        "fields": [(f.name, f.value) for f in e.fields]} for e in msg.embeds],
        })
    return out


# =====================================================================
# Bot
# =====================================================================

cfg: Config = None  # type: ignore  (โหลดใน main())
db: Database = None  # type: ignore
steam: SteamClient = None  # type: ignore
stripe: Optional[StripeClient] = None
rcon: Optional[Rcon] = None
TZ = timezone(timedelta(hours=7))
_user_locks: dict = {}
_order_locks: dict = {}
PAYMENT_POLL_SECONDS = 20


class CookieBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # ใช้อ่านข้อความทำ transcript
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions(
            everyone=False, roles=True, users=True))
        self.tree = app_commands.CommandTree(self)
        self.session: Optional[aiohttp.ClientSession] = None
        self._poller: Optional[asyncio.Task] = None

    async def setup_hook(self):
        global steam, stripe
        self.session = aiohttp.ClientSession()
        steam = SteamClient(self.session, cfg.steam_api_key)
        if cfg.donate_enabled:
            stripe = StripeClient(self.session, cfg.stripe_secret_key)
        for view in (WelcomeView(), TicketPanelView(), DonatePanelView(), CatalogView(), CartView(),
                     ReviewView(), PaymentView(url="https://stripe.com"), ExpiredView(), DeliverView(),
                     TicketView(whitelist_buttons=True), ClosedView()):
            self.add_view(view)
        guild = discord.Object(id=cfg.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)  # แทนที่คำสั่งเก่าของบอทตัวเดิมในเซิฟนี้ทั้งหมด
        log.info("ลงทะเบียนคำสั่ง %d คำสั่ง", len(synced))
        try:  # ล้างคำสั่งแบบ global ที่บอทตัวเก่าอาจลงไว้
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
        except discord.HTTPException as e:
            log.warning("ล้างคำสั่ง global ไม่ได้: %s", e)
        if stripe:
            self._poller = asyncio.create_task(payment_poller())

    async def close(self):
        if self._poller:
            self._poller.cancel()
        if self.session:
            await self.session.close()
        await super().close()

    async def on_ready(self):
        log.info("ออนไลน์แล้ว: %s (%s)", self.user, self.user.id)
        guild = self.get_guild(cfg.guild_id)
        if guild is None:
            log.error("บอทไม่ได้อยู่ในเซิฟ GUILD_ID=%s — เช็ค GUILD_ID", cfg.guild_id)
        else:
            log.info("เซิฟ: %s — พิมพ์ /check ใน Discord เพื่อตรวจสิทธิ์", guild.name)
        if cfg.on_railway and not cfg.has_volume:
            log.warning("ยังไม่ได้ต่อ Volume — ข้อมูล ticket/whitelist/Steam/Donate จะหายทุกครั้งที่ deploy")
        if not cfg.donate_enabled:
            log.info("ยังไม่ได้ตั้ง STRIPE_SECRET_KEY — ปิดระบบ Donate ไว้")

    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent):
        ticket = db.by_channel(payload.thread_id)
        if ticket and ticket["status"] != "deleted":
            db.set_status(ticket["id"], "deleted")


bot = CookieBot()


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

def fmt_time(iso_or_dt) -> str:
    if not iso_or_dt:
        return "—"
    dt = datetime.fromisoformat(iso_or_dt) if isinstance(iso_or_dt, str) else iso_or_dt
    return dt.astimezone(TZ).strftime("%d/%m/%Y %H:%M")


def has_role(member, role_id) -> bool:
    return bool(role_id) and any(r.id == role_id for r in getattr(member, "roles", []))


def is_admin(member) -> bool:
    perms = getattr(member, "guild_permissions", None)
    if perms and perms.administrator:
        return True
    return any(has_role(member, r) for r in cfg.admin_roles)


def is_staff(member) -> bool:
    return is_admin(member) or any(has_role(member, r) for r in cfg.staff_roles)


def answers_of(ticket) -> dict:
    try:
        return json.loads(ticket["answers"] or "{}")
    except (TypeError, ValueError):
        return {}


def trunc(text: str, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def channel_link(channel_id: int) -> Optional[str]:
    return f"https://discord.com/channels/{cfg.guild_id}/{channel_id}" if channel_id else None


async def reply(interaction: discord.Interaction, content: str = None, embed=None, view=None):
    kwargs = {"ephemeral": True}
    if embed is not None:
        kwargs["embed"] = embed
    if view is not None:
        kwargs["view"] = view
    if interaction.response.is_done():
        await interaction.followup.send(content, **kwargs)
    else:
        await interaction.response.send_message(content, **kwargs)


async def fetch_member(guild: discord.Guild, user_id: int):
    member = guild.get_member(user_id)
    if member:
        return member
    try:
        return await guild.fetch_member(user_id)
    except (discord.NotFound, discord.HTTPException):
        return None


async def get_thread(guild: discord.Guild, thread_id: int, unarchive: bool = False):
    """หา thread (รวม thread ที่ archive แล้ว) — unarchive=True เพื่อให้โพสต์/แก้ข้อความได้"""
    thread = guild.get_thread(thread_id)
    if thread is None:
        try:
            thread = await guild.fetch_channel(thread_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None
    if unarchive and getattr(thread, "archived", False):
        try:
            await thread.edit(archived=False)
        except discord.HTTPException as e:
            log.warning("unarchive thread %s ไม่ได้: %s", thread_id, e)
    return thread


async def log_to(guild: discord.Guild, channel_id: int, embed: discord.Embed = None, **kwargs):
    if not channel_id:
        return None
    channel = guild.get_channel(channel_id)
    if channel is None:
        return None
    try:
        return await channel.send(embed=embed, allowed_mentions=kwargs.pop("allowed_mentions",
                                                                           discord.AllowedMentions.none()), **kwargs)
    except discord.HTTPException as e:
        log.warning("ส่ง log ไป #%s ไม่ได้: %s (รัน /check)", getattr(channel, "name", channel_id), e)
        return None


async def mod_log(guild, text: str, color=COLOR_MUTED):
    await log_to(guild, cfg.mod_logs, discord.Embed(description=text, color=color,
                                                     timestamp=datetime.now(timezone.utc)))


def user_lock(user_id: int) -> asyncio.Lock:
    return _user_locks.setdefault(user_id, asyncio.Lock())


def order_lock(order_id: int) -> asyncio.Lock:
    return _order_locks.setdefault(order_id, asyncio.Lock())


async def _report_error(interaction, error, where):
    log.error("%s พัง", where, exc_info=error)
    try:
        await reply(interaction, f"เกิดข้อผิดพลาด: `{trunc(str(error), 300)}` — ลองใหม่ หรือแจ้งแอดมิน")
    except discord.HTTPException:
        pass


class BaseView(ui.View):
    async def on_error(self, interaction, error, item):
        await _report_error(interaction, error, f"ปุ่ม {getattr(item, 'custom_id', item)}")


class BaseLayout(ui.LayoutView):
    async def on_error(self, interaction, error, item):
        await _report_error(interaction, error, f"ปุ่ม {getattr(item, 'custom_id', item)}")


class BaseModal(ui.Modal):
    async def on_error(self, interaction, error):
        await _report_error(interaction, error, f"ฟอร์ม {self.title}")


class ConfirmView(ui.View):
    def __init__(self, action: Callable[[discord.Interaction], Awaitable[None]], label="ยืนยัน",
                 style=discord.ButtonStyle.danger):
        super().__init__(timeout=60)
        self.action = action
        btn = ui.Button(label=label, style=style)
        btn.callback = self._go
        self.add_item(btn)

    async def _go(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.edit_message(content="กำลังดำเนินการ...", view=None)
        await self.action(interaction)
        try:
            await interaction.edit_original_response(content="เสร็จแล้ว")
        except discord.HTTPException:
            pass  # thread อาจถูกลบไปแล้ว

    async def on_error(self, interaction, error, item):
        await _report_error(interaction, error, "ปุ่มยืนยัน")


# ---------------------------------------------------------------------
# ข้อความต้อนรับ + panel (Components V2)
# ---------------------------------------------------------------------

def find_banner_file() -> Optional[Path]:
    for ext in ("png", "jpg", "jpeg", "gif", "webp"):
        path = ASSETS_DIR / f"banner.{ext}"
        if path.exists():
            return path
    return None


def welcome_text() -> str:
    rules = f"<#{cfg.rules_channel}>" if cfg.rules_channel else "ห้องกฎ"
    steps = "\n".join(f"{i}. {step.format(rules=rules)}" for i, step in enumerate(WELCOME_STEPS, 1))
    return f"## {WELCOME_TITLE}\n{WELCOME_SUBTITLE}\n{steps}"


async def open_menu(interaction: discord.Interaction):
    await reply(interaction, MENU_PROMPT, view=CategoryView(interaction.user))


class WelcomeView(BaseLayout):
    def __init__(self, banner: Optional[str] = None):
        super().__init__(timeout=None)
        children = []
        if banner:
            children.append(ui.MediaGallery(discord.MediaGalleryItem(banner)))
        children.append(ui.TextDisplay(welcome_text()))
        children.append(ui.Separator(spacing=discord.SeparatorSpacing.large))
        rules = ui.TextDisplay(f"**{RULES_HEADING}**\n{RULES_TEXT}")
        url = channel_link(cfg.rules_channel)
        if url:
            children.append(ui.Section(rules, accessory=ui.Button(
                style=discord.ButtonStyle.link, label=RULES_BUTTON, emoji="📜", url=url)))
        else:
            children.append(rules)
        join = ui.Button(style=discord.ButtonStyle.success, label=JOIN_BUTTON, emoji="🍪", custom_id="cc:join")
        join.callback = open_menu
        children.append(ui.Section(ui.TextDisplay(f"**{JOIN_HEADING}**\n{JOIN_TEXT}"), accessory=join))
        self.add_item(ui.Container(*children, accent_colour=cfg.accent_color))


class TicketPanelView(BaseLayout):
    def __init__(self):
        super().__init__(timeout=None)
        menu = "\n".join(f"{t.emoji} **{t.label}** — {t.menu_text}" for t in TICKET_TYPES.values()
                         if t.key != "donate" or cfg.donate_enabled)
        btn = ui.Button(style=discord.ButtonStyle.primary, label=TICKET_PANEL_BUTTON, emoji="🎫",
                        custom_id="cc:menu")
        btn.callback = open_menu
        self.add_item(ui.Container(
            ui.TextDisplay(f"## {TICKET_PANEL_TITLE}\n{TICKET_PANEL_TEXT}"),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            ui.Section(ui.TextDisplay(menu), accessory=btn),
            accent_colour=cfg.accent_color))


class CategoryView(ui.View):
    """เมนูเลือกหมวด (ส่งเป็นข้อความส่วนตัว) — ขอ White List โชว์เฉพาะคนที่ยังไม่มี"""

    def __init__(self, member):
        super().__init__(timeout=300)
        options = []
        for t in TICKET_TYPES.values():
            if t.key == "wl" and has_role(member, cfg.survivor_role) and not is_staff(member):
                continue
            if t.key == "donate" and not cfg.donate_enabled:
                continue
            if t.key in ("bug", "report") and cfg.member_role and not (
                    has_role(member, cfg.member_role) or has_role(member, cfg.survivor_role) or is_staff(member)):
                continue
            options.append(discord.SelectOption(label=t.label, value=t.key, emoji=t.emoji,
                                                description=t.menu_text[:100]))
        select = ui.Select(placeholder="เลือกเรื่อง...", options=options, min_values=1, max_values=1)
        select.callback = self._chosen
        self.select = select
        self.add_item(select)

    async def _chosen(self, interaction: discord.Interaction):
        key = self.select.values[0]
        if key == "wl":
            await start_whitelist(interaction)
        elif key == "donate":
            await start_donate_ticket(interaction)
        else:
            await start_ticket(interaction, key)

    async def on_error(self, interaction, error, item):
        await _report_error(interaction, error, "เมนูเลือกหมวด")


# ---------------------------------------------------------------------
# เปิด ticket (private thread ในห้อง ticket ห้องเดียว)
# ---------------------------------------------------------------------

async def start_whitelist(interaction: discord.Interaction):
    member = interaction.user
    if has_role(member, cfg.survivor_role) and not is_staff(member):
        where = f" ดูวิธีเข้าเซิฟที่ <#{cfg.connect_info_channel}>" if cfg.connect_info_channel else ""
        return await reply(interaction, f"คุณผ่าน White List แล้ว 🎉{where}")
    existing = db.open_tickets(member.id, "wl")
    if existing:
        return await reply(interaction, f"ส่งคำขอไว้แล้ว รอแอดมินตรวจที่ <#{existing[0]['channel_id']}>")
    defaults = {}
    link = db.steam_get(member.id)
    if link:
        defaults["steam"] = link["steam_id"]
    await interaction.response.send_modal(TicketModal(TICKET_TYPES["wl"], defaults))


async def start_ticket(interaction: discord.Interaction, key: str):
    existing = db.open_tickets(interaction.user.id, key)
    if len(existing) >= cfg.max_open_per_type:
        return await reply(interaction, f"คุณมี ticket ประเภทนี้เปิดอยู่แล้ว: <#{existing[0]['channel_id']}>")
    await interaction.response.send_modal(TicketModal(TICKET_TYPES[key]))


async def start_donate_ticket(interaction: discord.Interaction):
    if not cfg.donate_enabled:
        return await reply(interaction, "ระบบ Donate ยังไม่เปิด")
    existing = db.open_tickets(interaction.user.id, "donate")
    if existing:
        return await reply(interaction, f"ห้อง Donate ของคุณเปิดอยู่แล้ว: <#{existing[0]['channel_id']}>")
    await interaction.response.defer(ephemeral=True, thinking=True)
    async with user_lock(interaction.user.id):
        if db.open_tickets(interaction.user.id, "donate"):
            return await interaction.followup.send("ห้อง Donate ของคุณเปิดอยู่แล้ว", ephemeral=True)
        thread = await create_ticket(interaction, TICKET_TYPES["donate"], {})
    if thread:
        await interaction.followup.send(f"เปิดห้อง Donate แล้ว: {thread.mention}", ephemeral=True)


class RetryView(ui.View):
    """ปุ่มเปิดฟอร์มเดิมอีกครั้งพร้อมคำตอบเก่า"""

    def __init__(self, modal_factory: Callable[[], ui.Modal]):
        super().__init__(timeout=600)
        self.modal_factory = modal_factory
        btn = ui.Button(label="แก้ไขแล้วส่งใหม่", emoji="📝", style=discord.ButtonStyle.primary)
        btn.callback = self._retry
        self.add_item(btn)

    async def _retry(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self.modal_factory())


class TicketModal(BaseModal):
    def __init__(self, ttype: TicketType, defaults: Optional[dict] = None):
        super().__init__(title=ttype.modal_title[:45], timeout=900)
        self.ttype = ttype
        self.inputs = {}
        defaults = defaults or {}
        for q in ttype.questions[:5]:
            field_ = ui.TextInput(
                label=q.label[:45],
                style=discord.TextStyle.paragraph if q.paragraph else discord.TextStyle.short,
                required=q.required, max_length=q.max_length,
                placeholder=(q.placeholder or None) and q.placeholder[:100],
                default=trunc(defaults.get(q.key, ""), q.max_length) or None)
            self.inputs[q.key] = field_
            self.add_item(field_)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        answers = {k: v.value.strip() for k, v in self.inputs.items()}
        if self.ttype.key == "wl" and cfg.steam_required:
            if not await verify_steam_for(interaction, self.ttype, answers):
                return
        async with user_lock(interaction.user.id):
            existing = db.open_tickets(interaction.user.id, self.ttype.key)
            if len(existing) >= cfg.max_open_per_type:
                return await interaction.followup.send(
                    f"คุณมี ticket ประเภทนี้เปิดอยู่แล้ว: <#{existing[0]['channel_id']}>", ephemeral=True)
            thread = await create_ticket(interaction, self.ttype, answers)
        if not thread:
            return
        if self.ttype.key == "wl":
            await give_member_role(interaction)
            await interaction.followup.send(f"ส่งคำขอแล้ว ✅ ติดตามผลได้ที่ {thread.mention}", ephemeral=True)
        else:
            await interaction.followup.send(f"เปิด ticket แล้ว: {thread.mention}", ephemeral=True)


async def verify_steam_for(interaction: discord.Interaction, ttype: TicketType, answers: dict) -> bool:
    """เช็ค Steam ที่ผู้เล่นพิมพ์มา บันทึกการผูก และแก้ answers['steam'] เป็น SteamID64"""
    retry = RetryView(lambda: TicketModal(ttype, answers))
    try:
        info = await steam.lookup(answers.get("steam", ""))
    except SteamError as e:
        if e.admin_problem:
            log.error("เช็ค Steam ไม่ได้: %s", e)
            await mod_log(interaction.guild, f"❌ ระบบเช็ค Steam มีปัญหา: {e}", COLOR_BAD)
            await interaction.followup.send("❌ ระบบตรวจ Steam ขัดข้องชั่วคราว ลองใหม่อีกครั้ง "
                                            "(ถ้ายังไม่ได้ แจ้งแอดมิน)", view=retry, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {e}", view=retry, ephemeral=True)
        return False

    owner = db.steam_by_steam(info["steam_id"])
    if owner and owner["discord_id"] != interaction.user.id:
        await mod_log(interaction.guild, f"⚠️ {interaction.user.mention} ใส่ Steam `{info['steam_id']}` "
                                         f"ที่ผูกกับ <@{owner['discord_id']}> อยู่แล้ว", COLOR_BAD)
        await interaction.followup.send(
            "❌ Steam บัญชีนี้ถูกใช้กับ Discord บัญชีอื่นแล้ว — ถ้าเป็นของคุณจริง เลือก 'ติดต่อแอดมิน' ได้เลย",
            view=retry, ephemeral=True)
        return False
    if cfg.steam_require_pz and info.get("pz_status") != "owned":
        if info.get("pz_status") == "private":
            msg = ("❌ บอทมองไม่เห็นเกมในบัญชี Steam นี้ — ไปที่ Steam → Edit Profile → Privacy Settings "
                   "ตั้ง **Game details** เป็น Public ชั่วคราว แล้วกดส่งใหม่")
        else:
            msg = "❌ ไม่พบเกม Project Zomboid ในบัญชี Steam นี้ — เช็คว่าใส่บัญชีถูกตัว"
        await interaction.followup.send(msg, view=retry, ephemeral=True)
        return False

    db.steam_save(interaction.user.id, info)
    answers["steam"] = info["steam_id"]
    return True


async def give_member_role(interaction: discord.Interaction):
    if not cfg.member_role:
        return
    role = interaction.guild.get_role(cfg.member_role)
    if role and role not in interaction.user.roles:
        try:
            await interaction.user.add_roles(role, reason="ส่งคำขอ White List")
        except discord.Forbidden:
            log.warning("ให้ role Member ไม่ได้ — role บอทต้องอยู่เหนือ %s", role.name)


def build_ticket_embed(t: TicketType, number: int, member, answers: dict) -> discord.Embed:
    embed = discord.Embed(title=f"{t.emoji} {t.label} #{number:04d}",
                          description=t.welcome.format(user=member.mention),
                          color=t.color, timestamp=datetime.now(timezone.utc))
    info = steam_info_of(db.steam_get(member.id)) if t.key == "wl" else {}
    for q in t.questions:
        if q.key == "steam" and info:
            embed.add_field(name="Steam", value=trunc("\n".join(steam_summary(info)), 1024), inline=False)
            continue
        embed.add_field(name=q.label, value=trunc(answers.get(q.key) or "—", 1024), inline=False)
    if t.key == "wl":
        checks = []
        username = answers.get("username", "")
        if valid_username(username):
            checks.append("✅ username ใช้ได้")
        else:
            checks.append("❌ username ใช้ไม่ได้ (อังกฤษ/ตัวเลข/_ . - ยาว 2–32 ตัว ไม่มีเว้นวรรค) — แก้ได้ตอนกดอนุมัติ")
        existing = db.wl_get(username) if username else None
        if existing and existing["active"] and existing["discord_id"] != member.id:
            checks.append(f"⚠️ username นี้อยู่ใน whitelist แล้ว (<@{existing['discord_id']}>)")
        if cfg.secret_code:
            ok = normalize_code(answers.get("code", "")) == normalize_code(cfg.secret_code)
            checks.append("✅ รหัสลับตรง" if ok else "❌ รหัสลับไม่ตรง")
        checks += steam_checks(info)
        age = (datetime.now(timezone.utc) - member.created_at).days
        checks.append(("⚠️ " if age < 30 else "✅ ") + f"บัญชี Discord อายุ {fmt_age(age)}")
        embed.add_field(name="เช็คอัตโนมัติ (สำหรับแอดมิน)", value=trunc("\n".join(checks), 1024), inline=False)
        if info.get("avatar"):
            embed.set_thumbnail(url=info["avatar"])
    embed.set_footer(text=f"เปิดโดย {member} · {member.id}")
    return embed


async def create_ticket(interaction: discord.Interaction, t: TicketType, answers: dict):
    guild = interaction.guild
    member = interaction.user
    parent = guild.get_channel(cfg.ticket_channel)
    if not isinstance(parent, discord.TextChannel):
        await interaction.followup.send("ตั้ง TICKET_CHANNEL_ID ไม่ถูก (ต้องเป็น ID ของห้องข้อความ) — แจ้งแอดมิน",
                                        ephemeral=True)
        return None
    number = db.next_number(t.key)
    try:
        thread = await parent.create_thread(
            name=trunc(f"{t.prefix}-{number:04d} {member.display_name}", 100),
            type=discord.ChannelType.private_thread, invitable=False, auto_archive_duration=10080,
            reason=f"ticket โดย {member}")
        await thread.add_user(member)
    except discord.Forbidden:
        await interaction.followup.send(
            "บอทสร้าง ticket ไม่ได้ — ขาดสิทธิ์ในห้อง ticket (Create Private Threads / Manage Threads) "
            "แจ้งแอดมินให้รัน /check", ephemeral=True)
        return None
    except discord.HTTPException as e:
        await interaction.followup.send(f"สร้าง ticket ไม่สำเร็จ: {e.text or e}", ephemeral=True)
        return None

    ticket_id = db.create_ticket(t.key, number, thread.id, member.id, answers)
    mentions = [member.mention]
    staff_roles = [guild.get_role(r) for r in dict.fromkeys(cfg.staff_roles + cfg.admin_roles)]
    if cfg.ping_staff_on_new:
        mentions += [r.mention for r in staff_roles if r]
    try:
        await thread.send(" ".join(mentions), embed=build_ticket_embed(t, number, member, answers),
                          view=TicketView(whitelist_buttons=(t.key == "wl")))
        if t.key == "donate":
            await thread.send(embed=catalog_embed(in_thread=True), view=CatalogView())
    except discord.HTTPException as e:
        log.error("ส่งข้อความแรกใน ticket ไม่ได้: %s", e)
    await mod_log(guild, f"🎫 เปิด {thread.mention} ({t.label}) โดย {member.mention} · ticket #{ticket_id}",
                  COLOR_INFO)
    return thread


# ---------------------------------------------------------------------
# ปุ่มในห้อง ticket
# ---------------------------------------------------------------------

async def load_ticket(interaction: discord.Interaction, staff_only=True):
    ticket = db.by_channel(interaction.channel_id)
    if ticket is None:
        await reply(interaction, "ห้องนี้ไม่ใช่ ticket ของบอท")
        return None, None
    ttype = TICKET_TYPES.get(ticket["type"])
    if ttype is None:
        await reply(interaction, "ประเภท ticket นี้ไม่มีในบอทแล้ว")
        return None, None
    if staff_only and not is_staff(interaction.user):
        await reply(interaction, "ปุ่มนี้สำหรับทีมแอดมินเท่านั้น")
        return None, None
    return ticket, ttype


class TicketView(BaseView):
    def __init__(self, whitelist_buttons=True):
        super().__init__(timeout=None)
        if not whitelist_buttons:
            self.remove_item(self.approve)
            self.remove_item(self.reject)

    @ui.button(label="รับเรื่อง", emoji="🙋", style=discord.ButtonStyle.secondary, custom_id="cc:claim")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        ticket, _ = await load_ticket(interaction)
        if not ticket:
            return
        if ticket["status"] != "open":
            return await reply(interaction, "ticket นี้ปิดไปแล้ว")
        if ticket["claimed_by"] == interaction.user.id:
            db.set_claim(ticket["id"], None)
            await interaction.response.send_message(f"{interaction.user.mention} ปล่อยเรื่องนี้แล้ว",
                                                    allowed_mentions=discord.AllowedMentions.none())
        elif ticket["claimed_by"]:
            await reply(interaction, f"<@{ticket['claimed_by']}> รับเรื่องนี้ไปแล้ว")
        else:
            db.set_claim(ticket["id"], interaction.user.id)
            await interaction.response.send_message(f"🙋 {interaction.user.mention} รับเรื่องนี้แล้ว",
                                                    allowed_mentions=discord.AllowedMentions.none())

    @ui.button(label="ปิด ticket", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="cc:close")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        ticket, _ = await load_ticket(interaction, staff_only=False)
        if not ticket:
            return
        is_owner = interaction.user.id == ticket["owner_id"]
        if not (is_staff(interaction.user) or (is_owner and cfg.allow_owner_close)):
            return await reply(interaction, "ปิด ticket ได้เฉพาะทีมแอดมิน")
        if ticket["status"] != "open":
            return await reply(interaction, "ticket นี้ปิดไปแล้ว")
        note = ""
        if ticket["type"] == "donate":
            order = db.order_open_in_thread(ticket["channel_id"])
            if order and order["status"] == "pending":
                note = "\n⚠️ มีบิลรอจ่ายอยู่ — ถ้าจ่ายหลังปิด บอทยังแจ้งในห้องนี้ให้"

        async def do_close(i: discord.Interaction):
            await close_ticket(i.guild, i.channel, db.by_id(ticket["id"]), i.user)

        await reply(interaction, "ปิด ticket นี้? หลังปิดผู้เล่นจะพิมพ์ต่อไม่ได้" + note,
                    view=ConfirmView(do_close, "ปิดเลย"))

    @ui.button(label="อนุมัติ", emoji="✅", style=discord.ButtonStyle.success, custom_id="cc:wl:approve", row=1)
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        ticket = await _wl_decision_ticket(interaction)
        if ticket:
            await interaction.response.send_modal(ApproveModal(ticket["id"], answers_of(ticket).get("username", "")))

    @ui.button(label="ไม่ผ่าน", emoji="❌", style=discord.ButtonStyle.danger, custom_id="cc:wl:reject", row=1)
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        ticket = await _wl_decision_ticket(interaction)
        if ticket:
            await interaction.response.send_modal(RejectModal(ticket["id"]))


async def _wl_decision_ticket(interaction):
    ticket, _ = await load_ticket(interaction)
    if not ticket:
        return None
    if ticket["type"] != "wl":
        await reply(interaction, "ปุ่มนี้ใช้กับ ticket ขอ White List เท่านั้น")
        return None
    if ticket["decision"]:
        await reply(interaction, f"ตัดสินไปแล้ว: {ticket['decision']}")
        return None
    if ticket["status"] != "open":
        await reply(interaction, "ticket นี้ปิดไปแล้ว — กดเปิดใหม่ก่อน")
        return None
    return ticket


class ClosedView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="เปิดใหม่", emoji="🔓", style=discord.ButtonStyle.secondary, custom_id="cc:reopen")
    async def reopen(self, interaction: discord.Interaction, button: ui.Button):
        ticket, _ = await load_ticket(interaction)
        if not ticket:
            return
        if ticket["status"] == "open":
            return await reply(interaction, "ticket นี้เปิดอยู่แล้ว")
        await interaction.response.defer()
        try:
            await interaction.channel.edit(archived=False, locked=False)
        except discord.HTTPException as e:
            return await interaction.followup.send(f"เปิด thread ไม่ได้: {e.text or e}", ephemeral=True)
        db.set_status(ticket["id"], "open")
        await interaction.followup.send(f"🔓 {interaction.user.mention} เปิด ticket อีกครั้ง — <@{ticket['owner_id']}> "
                                        f"พิมพ์ต่อได้แล้ว", allowed_mentions=discord.AllowedMentions(users=True))
        await mod_log(interaction.guild, f"🔓 {interaction.channel.mention} เปิดใหม่โดย {interaction.user.mention}")

    @ui.button(label="Transcript", emoji="📄", style=discord.ButtonStyle.secondary, custom_id="cc:transcript")
    async def transcript(self, interaction: discord.Interaction, button: ui.Button):
        ticket, _ = await load_ticket(interaction)
        if not ticket:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        msg = await save_transcript(interaction.guild, interaction.channel, ticket, interaction.user)
        await interaction.followup.send(f"บันทึกแล้ว: {msg.jump_url}" if msg else
                                        "บันทึก transcript ไม่ได้ — รัน /check ดูสิทธิ์ห้อง transcript", ephemeral=True)

    @ui.button(label="ลบ thread", emoji="⛔", style=discord.ButtonStyle.danger, custom_id="cc:delete")
    async def delete(self, interaction: discord.Interaction, button: ui.Button):
        ticket, _ = await load_ticket(interaction)
        if not ticket:
            return

        async def do_delete(i: discord.Interaction):
            await delete_ticket(i.guild, i.channel, db.by_id(ticket["id"]), i.user)

        await reply(interaction, "ลบ thread นี้ถาวร? (บอทเก็บ transcript ให้ก่อนลบ)", view=ConfirmView(do_delete, "ลบเลย"))


# ---------------------------------------------------------------------
# ปิด / ลบ / transcript
# ---------------------------------------------------------------------

async def _user_label(guild, user_id):
    if not user_id:
        return "—"
    member = await fetch_member(guild, user_id)
    return f"{member} ({user_id})" if member else str(user_id)


async def save_transcript(guild, channel, ticket, by):
    target = guild.get_channel(cfg.transcripts)
    if target is None:
        return None
    ttype = TICKET_TYPES.get(ticket["type"])
    label = ttype.label if ttype else ticket["type"]
    messages = await collect_messages(channel)
    meta = {
        "title": f"{guild.name} · {channel.name}",
        "rows": [
            ("ประเภท", f"{label} #{ticket['number']:04d}"),
            ("เจ้าของ", await _user_label(guild, ticket["owner_id"])),
            ("รับเรื่องโดย", await _user_label(guild, ticket["claimed_by"])),
            ("เปิดเมื่อ", fmt_time(ticket["created_at"])),
            ("ปิดเมื่อ", fmt_time(ticket["closed_at"])),
            ("ผลการพิจารณา", ticket["decision"] or "—"),
            ("จำนวนข้อความ", str(len(messages))),
        ],
    }
    page = render_transcript(meta, messages, db.sensitive_ids(), TZ)
    file = discord.File(io.BytesIO(page.encode("utf-8")), filename=f"{ttype.prefix if ttype else 'ticket'}-"
                                                                    f"{ticket['number']:04d}.html")
    embed = discord.Embed(title=f"Transcript · {channel.name}", color=ttype.color if ttype else COLOR_MUTED,
                          timestamp=datetime.now(timezone.utc))
    embed.add_field(name="ประเภท", value=label)
    embed.add_field(name="เจ้าของ", value=f"<@{ticket['owner_id']}>")
    embed.add_field(name="รับเรื่องโดย", value=f"<@{ticket['claimed_by']}>" if ticket["claimed_by"] else "—")
    embed.add_field(name="บันทึกโดย", value=by.mention)
    embed.add_field(name="ข้อความ", value=str(len(messages)))
    if ticket["decision"]:
        embed.add_field(name="ผล", value=ticket["decision"])
    try:
        msg = await target.send(embed=embed, file=file, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException as e:
        log.warning("ส่ง transcript ไม่ได้: %s", e)
        return None
    db.set_transcript_saved(ticket["id"])
    return msg


async def close_ticket(guild, thread, ticket, by, reason: str = None):
    if ticket is None or ticket["status"] != "open":
        return
    db.set_status(ticket["id"], "closed")
    ticket = db.by_id(ticket["id"])
    embed = discord.Embed(title="ปิด ticket แล้ว", color=COLOR_MUTED,
                          description=f"ปิดโดย {by.mention}" + (f"\nเหตุผล: {reason}" if reason else ""),
                          timestamp=datetime.now(timezone.utc))
    await thread.send(embed=embed, view=ClosedView())
    msg = await save_transcript(guild, thread, ticket, by)
    if cfg.dm_transcript and msg and msg.attachments:
        owner = await fetch_member(guild, ticket["owner_id"])
        if owner:
            try:
                await owner.send(f"ticket {thread.name} ที่ {guild.name} ปิดแล้ว — นี่คือบันทึกบทสนทนา",
                                 file=await msg.attachments[0].to_file())
            except discord.HTTPException:
                pass
    try:
        await thread.edit(archived=True, locked=True, reason="ปิด ticket")
    except discord.HTTPException as e:
        log.warning("ล็อก thread ไม่ได้: %s", e)
    await mod_log(guild, f"🔒 ปิด {thread.mention} โดย {by.mention}" + (f" — {reason}" if reason else ""))


async def delete_ticket(guild, thread, ticket, by):
    if ticket is None:
        return
    if not ticket["transcript_saved"]:
        await save_transcript(guild, thread, ticket, by)
    db.set_status(ticket["id"], "deleted")
    await mod_log(guild, f"⛔ ลบ thread {thread.name} โดย {by.mention}")
    try:
        await thread.delete(reason=f"ลบ ticket โดย {by}")
    except discord.HTTPException as e:
        log.warning("ลบ thread ไม่ได้: %s", e)


# ---------------------------------------------------------------------
# อนุมัติ / ไม่ผ่าน White List
# ---------------------------------------------------------------------

class ApproveModal(BaseModal):
    def __init__(self, ticket_id: int, username: str):
        super().__init__(title="อนุมัติ White List", timeout=600)
        self.ticket_id = ticket_id
        self.username = ui.TextInput(label="Username ในเกม", default=trunc(username, 32) or None,
                                     max_length=32, required=True)
        self.password = ui.TextInput(label="Password (สุ่มให้แล้ว แก้ได้)",
                                     default=generate_password(cfg.password_length), max_length=32, required=True)
        self.add_item(self.username)
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await approve_whitelist(interaction, self.ticket_id, self.username.value.strip(), self.password.value.strip())


async def run_rcon(cmd: str):
    if not (cfg.rcon_enabled and rcon):
        return False, "ปิด RCON ไว้"
    try:
        resp = await rcon.command(cmd)
        return True, resp or "(เซิฟไม่ได้ตอบข้อความ)"
    except asyncio.TimeoutError:
        return False, "RCON ไม่ตอบภายในเวลา"
    except RconError as e:
        return False, str(e)
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


async def approve_whitelist(interaction: discord.Interaction, ticket_id: int, username: str, password: str):
    guild = interaction.guild
    ticket = db.by_id(ticket_id)
    send = interaction.followup.send
    if ticket is None or ticket["decision"]:
        return await send("ticket นี้ถูกตัดสินไปแล้ว", ephemeral=True)
    if not valid_username(username):
        return await send(f"username `{username}` ใช้ไม่ได้ — ใช้ได้แค่อังกฤษ ตัวเลข _ . - ยาว 2–32 ตัว ไม่มีเว้นวรรค",
                          ephemeral=True)
    if not valid_password(password):
        return await send("password ใช้ไม่ได้ — 4–32 ตัว ห้ามมีเว้นวรรคหรือเครื่องหมายคำพูด", ephemeral=True)
    existing = db.wl_get(username)
    if existing and existing["active"] and existing["discord_id"] != ticket["owner_id"]:
        return await send(f"username `{username}` เป็นของ <@{existing['discord_id']}> อยู่แล้ว — ให้ผู้เล่นเลือกชื่ออื่น",
                          ephemeral=True)
    owner = await fetch_member(guild, ticket["owner_id"])
    if owner is None:
        return await send("ผู้เล่นออกจากเซิฟ Discord ไปแล้ว — กดไม่ผ่านแล้วปิด ticket ได้เลย", ephemeral=True)

    notes = []
    cmd = f'adduser "{username}" "{password}"'
    ok, resp = await run_rcon(cmd)
    if ok:
        notes.append(f"RCON ตอบกลับ: `{trunc(resp, 300)}`")
        if re.search(r"exist|already", resp, re.I):
            notes.append("⚠️ ดูเหมือนชื่อนี้มีในเซิฟแล้ว — ผู้เล่นอาจต้องใช้รหัสเดิม หรือลบด้วย removeuserfromwhitelist ก่อน")
    else:
        if cfg.rcon_enabled:
            notes.append(f"❌ RCON: {resp}")
        notes.append(f"ก๊อปคำสั่งนี้ไปวางในหน้าต่างคอนโซลของเซิฟ **ก่อน**ผู้เล่นจะล็อกอิน:\n```{cmd}```")

    survivor = guild.get_role(cfg.survivor_role)
    if survivor:
        try:
            await owner.add_roles(survivor, reason=f"อนุมัติ whitelist โดย {interaction.user}")
            notes.append(f"ให้ role {survivor.mention} แล้ว")
        except discord.Forbidden:
            notes.append(f"❌ ให้ role {survivor.mention} ไม่ได้ (role บอทต้องอยู่เหนือ Survivor) — ให้เอง")
    if cfg.set_nickname and owner.display_name != username:
        try:
            await owner.edit(nick=username, reason="ตั้งชื่อให้ตรงกับในเกม")
            notes.append(f"เปลี่ยน nickname เป็น `{username}` แล้ว")
        except discord.HTTPException:
            notes.append("⚠️ เปลี่ยน nickname ไม่ได้ (เจ้าของเซิฟหรือ role สูงกว่าบอท) — ข้ามไป")

    connect = channel_link(cfg.connect_info_channel)
    dm = discord.Embed(title=f"ผ่าน White List แล้ว — {guild.name}", color=COLOR_OK,
                       description="ยินดีต้อนรับ! ใช้ข้อมูลนี้ล็อกอินเข้าเกม เก็บรหัสไว้คนเดียวนะ")
    dm.add_field(name="Username", value=f"`{username}`")
    dm.add_field(name="Password", value=f"||`{password}`||")
    if cfg.game_version:
        dm.add_field(name="เวอร์ชันเกม", value=cfg.game_version, inline=False)
    if connect:
        dm.add_field(name="วิธีเข้าเซิฟ", value=connect, inline=False)
    try:
        await owner.send(embed=dm)
        dm_ok = True
        notes.append("DM username/รหัสให้ผู้เล่นแล้ว")
    except discord.HTTPException:
        dm_ok = False

    steam_id = answers_of(ticket).get("steam", "")
    if not re.fullmatch(r"\d{17}", steam_id):
        link = db.steam_get(owner.id)
        steam_id = link["steam_id"] if link else None
    db.wl_add(username, owner.id, interaction.user.id, ticket_id, steam_id)
    db.set_decision(ticket_id, "approved")

    done = discord.Embed(title="อนุมัติแล้ว", color=COLOR_OK,
                         description=f"ยินดีต้อนรับ {owner.mention}! ได้ role Survivor แล้ว"
                                     + (f"\nดูวิธีเข้าเซิฟที่ <#{cfg.connect_info_channel}>" if cfg.connect_info_channel else ""))
    done.set_footer(text=f"อนุมัติโดย {interaction.user}")
    channel = interaction.channel
    await channel.send(owner.mention, embed=done, allowed_mentions=discord.AllowedMentions(users=[owner]))
    if dm_ok:
        await channel.send("ส่ง username/รหัสผ่านให้ทาง DM แล้ว")
    else:
        secret = await channel.send(
            f"{owner.mention} ส่ง DM ไม่ได้ (ปิดรับ DM อยู่) เลยส่งตรงนี้ — จดไว้แล้วอย่าแชร์ใคร\n"
            f"Username: `{username}`\nPassword: ||`{password}`||",
            allowed_mentions=discord.AllowedMentions(users=[owner]))
        db.mark_sensitive(secret.id)
        notes.append("⚠️ ผู้เล่นปิด DM — ส่งรหัสในห้อง ticket แทน (transcript จะซ่อนข้อความนี้)")

    steam_note = f" · Steam `{steam_id}`" if steam_id else ""
    await log_to(guild, cfg.whitelist_log, discord.Embed(
        color=COLOR_OK, timestamp=datetime.now(timezone.utc),
        description=f"**[APPROVE]** `{username}` · {owner.mention}{steam_note} · โดย {interaction.user.mention}"))
    await interaction.followup.send("อนุมัติแล้ว\n" + "\n".join(f"• {n}" for n in notes), ephemeral=True)
    if cfg.auto_close_after_decision:
        await close_ticket(guild, channel, db.by_id(ticket_id), interaction.user, "อนุมัติ White List")


class RejectModal(BaseModal):
    def __init__(self, ticket_id: int):
        super().__init__(title="ไม่ผ่าน White List", timeout=600)
        self.ticket_id = ticket_id
        self.reason = ui.TextInput(label="เหตุผล (ผู้เล่นจะเห็น)", style=discord.TextStyle.paragraph,
                                   default="รหัสลับไม่ตรงกับในห้องกฎ", max_length=500)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        ticket = db.by_id(self.ticket_id)
        if ticket is None or ticket["decision"]:
            return await interaction.followup.send("ticket นี้ถูกตัดสินไปแล้ว", ephemeral=True)
        reason = self.reason.value.strip()
        db.set_decision(self.ticket_id, "rejected")
        embed = discord.Embed(title="ยังไม่ผ่าน", color=COLOR_BAD,
                              description=f"เหตุผล: {reason}\n\nแก้แล้วกด 🍪 Join ส่งคำขอใหม่ได้เลย")
        embed.set_footer(text=f"โดย {interaction.user}")
        await interaction.channel.send(f"<@{ticket['owner_id']}>", embed=embed,
                                       allowed_mentions=discord.AllowedMentions(users=True))
        username = answers_of(ticket).get("username", "?")
        await log_to(guild, cfg.whitelist_log, discord.Embed(
            color=COLOR_BAD, timestamp=datetime.now(timezone.utc),
            description=f"**[REJECT]** `{trunc(username, 40)}` · <@{ticket['owner_id']}> · โดย {interaction.user.mention}\n"
                        f"เหตุผล: {trunc(reason, 300)}"))
        await interaction.followup.send("บันทึกว่าไม่ผ่านแล้ว", ephemeral=True)
        if cfg.auto_close_after_decision:
            await close_ticket(guild, interaction.channel, db.by_id(self.ticket_id), interaction.user,
                               "ไม่ผ่าน White List")


# =====================================================================
# Donate: รายการ → ตะกร้า → การ์ดสรุป → บิล Stripe → จ่ายแล้ว → ส่งของ
# =====================================================================

def catalog_embed(in_thread: bool) -> discord.Embed:
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(DONATE_HOWTO, 1))
    embed = discord.Embed(title=DONATE_TITLE, color=COLOR_DONATE,
                          description=f"{DONATE_INTRO}\n\n**วิธีใช้**\n{steps}\n\n**รายการ**\n"
                                      f"{catalog_text(db.items())}")
    if not in_thread:
        embed.set_footer(text="กด Donate เพื่อเปิดห้อง Donate ส่วนตัว")
    return embed


class DonatePanelView(BaseView):
    """panel สาธารณะ (/panel donate) — กดแล้วเปิดห้อง Donate ส่วนตัว"""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Donate", emoji="💝", style=discord.ButtonStyle.success, custom_id="cc:donate:open")
    async def open_donate(self, interaction: discord.Interaction, button: ui.Button):
        await start_donate_ticket(interaction)


class CatalogView(BaseView):
    """ปุ่ม Donate ในห้อง Donate — เริ่ม/ต่อตะกร้า"""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Donate", emoji="💝", style=discord.ButtonStyle.success, custom_id="cc:donate:start")
    async def start(self, interaction: discord.Interaction, button: ui.Button):
        ticket = db.by_channel(interaction.channel_id)
        if ticket is None or ticket["type"] != "donate":
            return await reply(interaction, "ใช้ปุ่มนี้ในห้อง Donate เท่านั้น")
        if interaction.user.id != ticket["owner_id"] and not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับเจ้าของห้อง")
        if ticket["status"] != "open":
            return await reply(interaction, "ห้องนี้ปิดแล้ว — เปิดห้อง Donate ใหม่ได้จากปุ่ม Join / เปิด Ticket")
        if not db.items():
            return await reply(interaction, "ยังไม่มีรายการให้ Donate — รอแอดมินเพิ่มก่อนนะ")
        order = db.order_open_in_thread(interaction.channel_id)
        if order and order["status"] in ("review", "pending", "expired"):
            link = f"https://discord.com/channels/{cfg.guild_id}/{order['thread_id']}/{order['message_id']}"
            return await reply(interaction, f"มีรายการ #{order['id']:04d} ค้างอยู่ — จัดการที่การ์ดนี้ก่อน: {link}")
        if order is None:
            order_id = db.order_create(ticket["id"], interaction.channel_id, ticket["owner_id"])
        else:
            order_id = order["id"]
        await interaction.response.send_modal(AddItemModal(order_id))


def order_owner_or_staff(interaction, order) -> bool:
    return interaction.user.id == order["owner_id"] or is_staff(interaction.user)


async def order_from_message(interaction: discord.Interaction, owner_only=True):
    order = db.order_by_message(interaction.message.id) if interaction.message else None
    if order is None:
        await reply(interaction, "ไม่พบรายการนี้แล้ว")
        return None
    if owner_only and not order_owner_or_staff(interaction, order):
        await reply(interaction, "ปุ่มนี้สำหรับเจ้าของรายการ")
        return None
    return order


def cart_embed(order, lines: list) -> discord.Embed:
    embed = discord.Embed(title=f"🛒 ตะกร้า Donate #{order['id']:04d}", color=COLOR_DONATE,
                          description=cart_text(lines))
    embed.add_field(name="รวม", value=f"**{fmt_baht(cart_total(lines))}**")
    embed.set_footer(text=f"{len(lines)}/{MAX_CART_LINES} รายการ · กด 📨 ส่ง เมื่อครบแล้ว")
    return embed


def review_embed(order, lines: list) -> discord.Embed:
    embed = discord.Embed(title=f"📋 สรุปรายการ Donate #{order['id']:04d}", color=COLOR_WAIT,
                          description=cart_text(lines))
    embed.add_field(name="ยอดรวม", value=f"**{fmt_baht(cart_total(lines))}**")
    embed.add_field(name="ผู้ Donate", value=f"<@{order['owner_id']}>")
    embed.set_footer(text="ตรวจให้ครบแล้วกด ✅ ยืนยัน เพื่อรับบิลชำระเงิน")
    return embed


def payment_embed(order, lines: list) -> discord.Embed:
    expires = order["stripe_expires"]
    embed = discord.Embed(title=f"💳 รอชำระ — Donate #{order['id']:04d}", color=COLOR_WAIT,
                          description=f"{cart_text(lines)}\n\nกดปุ่ม **จ่ายเงิน** → เลือก PromptPay แล้วสแกน QR "
                                      f"หรือจ่ายด้วยบัตร\nจ่ายเสร็จบอทจะแจ้งในห้องนี้เอง (ภายใน ~{PAYMENT_POLL_SECONDS} วินาที)")
    url = order["stripe_url"] or ""
    if len(url) > 512:
        embed.description += f"\n\n💳 [กดที่นี่เพื่อจ่ายเงิน]({url})"
    embed.add_field(name="ยอดที่ต้องจ่าย", value=f"**{fmt_baht(order['total'])}**")
    if expires:
        embed.add_field(name="บิลหมดอายุ", value=f"<t:{expires}:R>")
    return embed


def paid_embed(order, lines: list, delivered: bool = False) -> discord.Embed:
    embed = discord.Embed(title=f"💝 ได้รับยอด Donate แล้ว — #{order['id']:04d}",
                          color=COLOR_OK if delivered else COLOR_DONATE,
                          description=f"ขอบคุณ <@{order['owner_id']}> ที่ช่วยสนับสนุนเซิฟ 🍪\n\n{cart_text(lines)}")
    embed.add_field(name="ยอดรวม", value=f"**{fmt_baht(order['total'])}**")
    embed.add_field(name="ชำระเมื่อ", value=fmt_time(order["paid_at"]))
    if delivered:
        embed.add_field(name="สถานะ", value=f"✅ ส่งของแล้ว โดย <@{order['delivered_by']}> · {fmt_time(order['delivered_at'])}",
                        inline=False)
    else:
        embed.add_field(name="สถานะ", value="⏳ รอแอดมินส่งของในเกม", inline=False)
    return embed


def closed_order_embed(order, lines: list, text: str, color=COLOR_MUTED) -> discord.Embed:
    embed = discord.Embed(title=f"Donate #{order['id']:04d} — {text}", color=color, description=cart_text(lines))
    embed.add_field(name="ยอดรวม", value=fmt_baht(order["total"] or cart_total(lines)))
    return embed


class AddItemModal(BaseModal):
    def __init__(self, order_id: int, code: str = "", qty: str = "1"):
        super().__init__(title="เพิ่มรายการ Donate", timeout=600)
        self.order_id = order_id
        self.code = ui.TextInput(label="รหัส", placeholder="ดูรหัสในรายการด้านบน เช่น A01", max_length=20,
                                 default=code or None)
        self.qty = ui.TextInput(label="จำนวน", default=qty or "1", max_length=3)
        self.add_item(self.code)
        self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        code, qty_text = self.code.value.strip(), self.qty.value.strip()
        retry = RetryView(lambda: AddItemModal(self.order_id, code, qty_text))
        async with order_lock(self.order_id):
            order = db.order_get(self.order_id)
            if order is None or order["status"] != "cart":
                return await reply(interaction, "ตะกร้านี้ส่งไปแล้ว — กด 📝 แก้ไข ที่การ์ดสรุปถ้าจะเปลี่ยน")
            if not qty_text.isdigit():
                return await reply(interaction, "❌ จำนวนต้องเป็นตัวเลข", view=retry)
            try:
                lines = cart_add(lines_of(order), db.item_get(code), int(qty_text), cfg.donate_max_qty)
            except CartError as e:
                return await reply(interaction, f"❌ {e}", view=retry)
            db.order_update(order["id"], lines=lines, total=cart_total(lines))
            order = db.order_get(order["id"])
            await show_cart(interaction, order, lines)
        added = next(line for line in lines if line["code"].casefold() == code.casefold())
        await reply(interaction, f"เพิ่ม `{added['code']}` {added['name']} × {int(qty_text)} แล้ว "
                                 f"({fmt_baht(added['unit'])}/ชิ้น)")


async def show_cart(interaction: discord.Interaction, order, lines: list):
    """แก้การ์ดตะกร้าเดิม หรือโพสต์ใหม่ถ้ายังไม่มี"""
    embed, view = cart_embed(order, lines), CartView(lines)
    if order["message_id"]:
        try:
            await interaction.channel.get_partial_message(order["message_id"]).edit(embed=embed, view=view)
            return
        except discord.HTTPException:
            pass
    msg = await interaction.channel.send(embed=embed, view=view)
    db.order_update(order["id"], message_id=msg.id)


class CartView(BaseView):
    def __init__(self, lines: Optional[list] = None):
        super().__init__(timeout=None)
        if lines is not None:
            self.add.disabled = len(lines) >= MAX_CART_LINES
            self.remove.disabled = not lines
            self.send.disabled = not lines

    @ui.button(label="เพิ่มรายการ", emoji="➕", style=discord.ButtonStyle.secondary, custom_id="cc:cart:add")
    async def add(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        if order["status"] != "cart":
            return await reply(interaction, "ตะกร้านี้ส่งไปแล้ว")
        if len(lines_of(order)) >= MAX_CART_LINES:
            return await reply(interaction, f"ครบ {MAX_CART_LINES} รายการแล้ว — ลบรายการเดิม หรือกด 📨 ส่ง")
        await interaction.response.send_modal(AddItemModal(order["id"]))

    @ui.button(label="ลบรายการ", emoji="➖", style=discord.ButtonStyle.secondary, custom_id="cc:cart:remove")
    async def remove(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        lines = lines_of(order)
        if order["status"] != "cart" or not lines:
            return await reply(interaction, "ไม่มีรายการให้ลบ")
        await reply(interaction, "เลือกรายการที่จะลบ", view=RemoveLineView(order["id"], lines))

    @ui.button(label="ส่ง", emoji="📨", style=discord.ButtonStyle.success, custom_id="cc:cart:send")
    async def send(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        async with order_lock(order["id"]):
            order = db.order_get(order["id"])
            lines = lines_of(order)
            if order["status"] != "cart" or not lines:
                return await reply(interaction, "ไม่มีรายการให้ส่ง")
            total = cart_total(lines)
            if total < cfg.donate_min:
                return await reply(interaction, f"ยอดขั้นต่ำต่อรอบคือ {fmt_baht(cfg.donate_min)} — เพิ่มรายการอีกนิดนะ")
            db.order_update(order["id"], status="review", total=total)
            await interaction.response.edit_message(embed=cart_embed(order, lines).set_footer(text="ส่งแล้ว"),
                                                    view=None)
            msg = await interaction.channel.send(embed=review_embed(db.order_get(order["id"]), lines),
                                                 view=ReviewView())
            db.order_update(order["id"], message_id=msg.id)

    @ui.button(label="ยกเลิก", emoji="❌", style=discord.ButtonStyle.danger, custom_id="cc:cart:cancel")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        await cancel_order(interaction, order)


class RemoveLineView(ui.View):
    def __init__(self, order_id: int, lines: list):
        super().__init__(timeout=120)
        self.order_id = order_id
        select = ui.Select(placeholder="เลือกรายการ", options=[
            discord.SelectOption(label=trunc(f"{line['code']} · {line['name']}", 100), value=line["code"],
                                 description=f"{fmt_baht(line['unit'])} × {line['qty']}") for line in lines])
        select.callback = self._remove
        self.select = select
        self.add_item(select)

    async def _remove(self, interaction: discord.Interaction):
        code = self.select.values[0]
        async with order_lock(self.order_id):
            order = db.order_get(self.order_id)
            if order is None or order["status"] != "cart":
                return await interaction.response.edit_message(content="ตะกร้านี้ส่งไปแล้ว", view=None)
            lines = [line for line in lines_of(order) if line["code"] != code]
            db.order_update(order["id"], lines=lines, total=cart_total(lines))
            order = db.order_get(order["id"])
            thread = interaction.channel
            try:
                await thread.get_partial_message(order["message_id"]).edit(embed=cart_embed(order, lines),
                                                                           view=CartView(lines))
            except discord.HTTPException:
                pass
        await interaction.response.edit_message(content=f"ลบ `{code}` แล้ว", view=None)


class ReviewView(BaseView):
    @ui.button(label="ยืนยัน", emoji="✅", style=discord.ButtonStyle.success, custom_id="cc:order:confirm")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        if interaction.user.id != order["owner_id"]:
            return await reply(interaction, "เจ้าของรายการต้องกดยืนยันเอง")
        await interaction.response.defer()
        await create_bill(interaction, order["id"])

    @ui.button(label="แก้ไข", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="cc:order:edit")
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        async with order_lock(order["id"]):
            order = db.order_get(order["id"])
            if order["status"] != "review":
                return await reply(interaction, "แก้ไขไม่ได้แล้ว")
            db.order_update(order["id"], status="cart")
            lines = lines_of(order)
            await interaction.response.edit_message(embed=cart_embed(order, lines), view=CartView(lines))

    @ui.button(label="ยกเลิก", emoji="❌", style=discord.ButtonStyle.danger, custom_id="cc:order:cancel")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        await cancel_order(interaction, order)

    def __init__(self):
        super().__init__(timeout=None)


class PaymentView(BaseView):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.clear_items()  # จัดลำดับให้ปุ่มจ่ายเงินอยู่ซ้ายสุด
        if url and len(url) <= 512:  # Discord จำกัดลิงก์ในปุ่ม 512 ตัว (ยาวกว่านี้ใช้ลิงก์ในการ์ดแทน)
            self.add_item(ui.Button(label="จ่ายเงิน (PromptPay / บัตร)", emoji="💳", url=url, row=0))
        self.add_item(self.check)
        self.add_item(self.cancel)

    @ui.button(label="เช็คสถานะ", emoji="🔄", style=discord.ButtonStyle.secondary, custom_id="cc:order:check", row=0)
    async def check(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await sync_payment(order["id"])
        await interaction.followup.send({"paid": "ได้รับยอดแล้ว ✅ ขอบคุณ!", "expired": "บิลหมดอายุแล้ว — กดสร้างบิลใหม่ได้",
                                         "pending": "ยังไม่ได้รับยอด ถ้าจ่ายแล้วรอสักครู่แล้วกดเช็คอีกครั้ง"}
                                        .get(result, f"เช็คไม่ได้: {result}"), ephemeral=True)

    @ui.button(label="ยกเลิก", emoji="❌", style=discord.ButtonStyle.danger, custom_id="cc:order:cancelpay", row=0)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        await cancel_order(interaction, order)


class ExpiredView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="สร้างบิลใหม่", emoji="🔁", style=discord.ButtonStyle.primary, custom_id="cc:order:renew")
    async def renew(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        if interaction.user.id != order["owner_id"]:
            return await reply(interaction, "เจ้าของรายการต้องกดเอง")
        await interaction.response.defer()
        await create_bill(interaction, order["id"])

    @ui.button(label="ยกเลิก", emoji="❌", style=discord.ButtonStyle.danger, custom_id="cc:order:cancelexp")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        await cancel_order(interaction, order)


class DeliverView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="ยืนยันส่งของแล้ว", emoji="📦", style=discord.ButtonStyle.success, custom_id="cc:order:deliver")
    async def deliver(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับแอดมิน")
        order = await order_from_message(interaction, owner_only=False)
        if order is None:
            return
        await interaction.response.defer()
        result = await mark_delivered(interaction.guild, order["id"], interaction.user)
        if result != "ok":
            await interaction.followup.send(result, ephemeral=True)


async def create_bill(interaction: discord.Interaction, order_id: int):
    """สร้าง Checkout Session แล้วเปลี่ยนการ์ดเป็น 'รอชำระ' (เรียกหลัง defer)"""
    async with order_lock(order_id):
        order = db.order_get(order_id)
        if order is None or order["status"] not in ("review", "expired"):
            return await interaction.followup.send("รายการนี้ไม่อยู่ในสถานะที่ยืนยันได้แล้ว", ephemeral=True)
        lines = lines_of(order)
        # ราคาอิงตอนใส่ตะกร้า ถ้าแอดมินปิดรายการระหว่างนั้น ให้แจ้งก่อน
        gone = [line["code"] for line in lines if not (db.item_get(line["code"]) or {"active": 0})["active"]]
        if gone:
            how = "กด 📝 แก้ไข เพื่อเอาออก" if order["status"] == "review" else "กดยกเลิกแล้วทำรายการใหม่"
            return await interaction.followup.send(f"รายการ {', '.join(gone)} ถูกปิดไปแล้ว — {how}", ephemeral=True)
        if stripe is None:
            return await interaction.followup.send("ระบบ Donate ปิดอยู่ (ยังไม่ได้ตั้ง STRIPE_SECRET_KEY)", ephemeral=True)
        attempt = order["attempt"] + 1
        expires_at = int(time.time()) + cfg.stripe_session_minutes * 60
        try:
            session = await stripe.create_checkout(
                order_id=order["id"], owner_id=order["owner_id"], lines=lines, currency=cfg.stripe_currency,
                success_url=f"https://discord.com/channels/{cfg.guild_id}/{order['thread_id']}",
                expires_at=expires_at, payment_methods=cfg.stripe_payment_methods,
                idempotency_key=f"cookiecheetah-order-{order['id']}-{attempt}")
        except StripeError as e:
            log.error("สร้างบิล Stripe ไม่ได้ (order %s): %s", order_id, e)
            await mod_log(interaction.guild, f"❌ สร้างบิล Stripe ไม่ได้ (Donate #{order_id:04d}): {e}", COLOR_BAD)
            return await interaction.followup.send("❌ สร้างบิลไม่สำเร็จ ลองกดยืนยันอีกครั้ง (ถ้ายังไม่ได้ แจ้งแอดมิน)",
                                                   ephemeral=True)
        db.order_update(order_id, status="pending", attempt=attempt, stripe_session=session["id"],
                        stripe_url=session["url"], stripe_expires=session.get("expires_at") or expires_at,
                        total=cart_total(lines))
        order = db.order_get(order_id)
        await interaction.message.edit(embed=payment_embed(order, lines), view=PaymentView(order["stripe_url"]))
        await mod_log(interaction.guild, f"💳 บิล Donate #{order_id:04d} {fmt_baht(order['total'])} "
                                         f"โดย <@{order['owner_id']}> · <#{order['thread_id']}>", COLOR_WAIT)


async def cancel_order(interaction: discord.Interaction, order):
    await interaction.response.defer()  # คุยกับ Stripe อาจเกิน 3 วินาที
    already_paid = False
    async with order_lock(order["id"]):
        order = db.order_get(order["id"])
        if order["status"] in ("paid", "delivered", "cancelled"):
            return await interaction.followup.send("ยกเลิกรายการนี้ไม่ได้แล้ว", ephemeral=True)
        if order["status"] == "pending" and order["stripe_session"] and stripe:
            try:
                session = await stripe.get_session(order["stripe_session"])
                if session.get("payment_status") == "paid":
                    already_paid = True
                elif session.get("status") == "open":
                    await stripe.expire_session(order["stripe_session"])
            except StripeError as e:
                return await interaction.followup.send(f"ยกเลิกบิลที่ Stripe ไม่ได้: {e}", ephemeral=True)
        if not already_paid:
            db.order_update(order["id"], status="cancelled")
            await interaction.edit_original_response(
                embed=closed_order_embed(order, lines_of(order), "ยกเลิกแล้ว"), view=None)
    if already_paid:
        await interaction.followup.send("บิลนี้จ่ายแล้ว ยกเลิกไม่ได้ — อัปเดตการ์ดให้แล้ว", ephemeral=True)
        await sync_payment(order["id"])


async def sync_payment(order_id: int) -> str:
    """เช็คบิลกับ Stripe — คืน 'paid' / 'pending' / 'expired' / ข้อความ error"""
    async with order_lock(order_id):
        order = db.order_get(order_id)
        if order is None:
            return "ไม่พบรายการ"
        if order["status"] in ("paid", "delivered"):
            return "paid"
        if order["status"] == "expired":
            return "expired"
        if order["status"] != "pending" or not order["stripe_session"]:
            return "pending"
        if stripe is None:
            return "ยังไม่ได้ตั้ง STRIPE_SECRET_KEY"
        try:
            session = await stripe.get_session(order["stripe_session"])
        except StripeError as e:
            return str(e)
        guild = bot.get_guild(cfg.guild_id)
        if session.get("payment_status") == "paid":
            await on_paid(guild, order, session)
            return "paid"
        if session.get("status") == "expired":
            db.order_update(order_id, status="expired")
            order = db.order_get(order_id)
            thread = await get_thread(guild, order["thread_id"], unarchive=True) if guild else None
            if thread and order["message_id"]:
                try:
                    await thread.get_partial_message(order["message_id"]).edit(
                        embed=closed_order_embed(order, lines_of(order), "บิลหมดอายุ", COLOR_MUTED)
                        .set_footer(text="กด 🔁 สร้างบิลใหม่ ถ้ายังต้องการ Donate รายการนี้"), view=ExpiredView())
                except discord.HTTPException as e:
                    log.warning("แก้การ์ดบิลหมดอายุไม่ได้: %s", e)
            return "expired"
        return "pending"


async def on_paid(guild, order, session):
    paid_at = datetime.now(timezone.utc).isoformat()
    db.order_update(order["id"], status="paid", paid_at=paid_at)
    order = db.order_get(order["id"])
    lines = lines_of(order)
    if guild is None:
        return
    thread = await get_thread(guild, order["thread_id"], unarchive=True)
    if thread is not None:
        if order["message_id"]:
            try:
                await thread.get_partial_message(order["message_id"]).edit(
                    embed=closed_order_embed(order, lines, "ชำระแล้ว ✅", COLOR_OK), view=None)
            except discord.HTTPException:
                pass
        staff = " ".join(f"<@&{r}>" for r in dict.fromkeys(cfg.staff_roles + cfg.admin_roles)) \
            if cfg.ping_staff_on_new else ""
        try:
            msg = await thread.send(f"<@{order['owner_id']}> {staff}".strip(), embed=paid_embed(order, lines),
                                    view=DeliverView())
            db.order_update(order["id"], paid_message_id=msg.id)
        except discord.HTTPException as e:
            log.error("ส่งการ์ดยืนยันการจ่ายไม่ได้ (order %s): %s", order["id"], e)
    amount = session.get("amount_total") or order["total"]
    email = (session.get("customer_details") or {}).get("email") or "—"
    await log_to(guild, cfg.donate_log or cfg.mod_logs, discord.Embed(
        color=COLOR_OK, timestamp=datetime.now(timezone.utc),
        description=f"**[PAID]** Donate #{order['id']:04d} · <@{order['owner_id']}> · **{fmt_baht(amount)}**\n"
                    f"{cart_text(lines)}\nStripe: `{order['stripe_session']}` · {email}\n"
                    + (f"ห้อง: <#{order['thread_id']}>" if thread else "")))


async def mark_delivered(guild, order_id: int, by) -> str:
    async with order_lock(order_id):
        order = db.order_get(order_id)
        if order is None:
            return "ไม่พบรายการ"
        if order["status"] == "delivered":
            return f"ส่งไปแล้วโดย <@{order['delivered_by']}>"
        if order["status"] != "paid":
            return "รายการนี้ยังไม่ได้จ่าย"
        db.order_update(order_id, status="delivered", delivered_by=by.id,
                        delivered_at=datetime.now(timezone.utc).isoformat())
        order = db.order_get(order_id)
        lines = lines_of(order)
        thread = await get_thread(guild, order["thread_id"], unarchive=True)
        if thread is not None:
            if order["paid_message_id"]:
                try:
                    await thread.get_partial_message(order["paid_message_id"]).edit(
                        embed=paid_embed(order, lines, delivered=True), view=None)
                except discord.HTTPException:
                    pass
            try:
                await thread.send(f"<@{order['owner_id']}> ส่งของให้ในเกมแล้ว 📦 ขอบคุณที่สนับสนุนเซิฟนะ 🍪",
                                  allowed_mentions=discord.AllowedMentions(users=True))
            except discord.HTTPException:
                pass
            ticket = db.by_channel(thread.id)
            if ticket and ticket["status"] == "closed":  # ห้องปิดไปแล้ว → เก็บกลับเข้า archive
                try:
                    await thread.edit(archived=True, locked=True)
                except discord.HTTPException:
                    pass
        await log_to(guild, cfg.donate_log or cfg.mod_logs, discord.Embed(
            color=COLOR_OK, timestamp=datetime.now(timezone.utc),
            description=f"**[DELIVERED]** Donate #{order_id:04d} · <@{order['owner_id']}> · ส่งโดย {by.mention}"))
        return "ok"


async def payment_poller():
    """เช็คบิลที่รอจ่ายกับ Stripe เป็นระยะ (ไม่ต้องตั้ง webhook / โดเมน)"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            stale = int(time.time()) - 3 * 86400  # บิลหมดอายุเกิน 3 วันแล้วไม่ต้องเช็คต่อ (ใช้ /order check เองได้)
            for order in db.orders_with_status("pending", limit=100):
                if order["stripe_expires"] and order["stripe_expires"] < stale:
                    continue
                result = await sync_payment(order["id"])
                if result not in ("paid", "pending", "expired"):
                    log.warning("เช็คบิล #%s ไม่ได้: %s", order["id"], result)
                await asyncio.sleep(0.3)
        except Exception:  # noqa: BLE001 — ห้ามให้ loop ตาย
            log.exception("payment poller พัง")
        await asyncio.sleep(PAYMENT_POLL_SECONDS)


# =====================================================================
# /check
# =====================================================================

PERM_NAMES = {
    "view_channel": "View Channel", "send_messages": "Send Messages", "embed_links": "Embed Links",
    "attach_files": "Attach Files", "read_message_history": "Read Message History",
    "manage_channels": "Manage Channels", "manage_roles": "Manage Roles", "manage_nicknames": "Manage Nicknames",
    "manage_messages": "Manage Messages", "manage_threads": "Manage Threads",
    "create_private_threads": "Create Private Threads", "send_messages_in_threads": "Send Messages in Threads",
}


def check_channel(guild, channel_id, label, perms, kind="ห้อง") -> list:
    if not channel_id:
        return [("➖", f"{label}: ไม่ได้ตั้ง (ข้าม)")]
    ch = guild.get_channel(channel_id)
    if ch is None:
        return [("❌", f"{label}: ไม่เจอ ID `{channel_id}` — เช็ค Variables หรือบอทมองไม่เห็นเลย (ขาด View Channel)")]
    p = ch.permissions_for(guild.me)
    missing = [PERM_NAMES[x] for x in perms if not getattr(p, x)]
    if missing:
        return [("❌", f"{label} ({ch.mention}): ขาด **{', '.join(missing)}** → Edit {kind} → Permissions → "
                       f"เพิ่ม role **{guild.me.top_role.name}** แล้วติ๊ก ✓")]
    return [("✅", f"{label} ({ch.mention})")]


def check_ticket_channel(guild) -> list:
    out = check_channel(guild, cfg.ticket_channel, "ห้อง ticket (บอท)",
                        ["view_channel", "send_messages", "send_messages_in_threads", "create_private_threads",
                         "manage_threads", "embed_links", "attach_files", "read_message_history"])
    ch = guild.get_channel(cfg.ticket_channel)
    if not isinstance(ch, discord.TextChannel):
        if ch is not None:
            out.append(("❌", "TICKET_CHANNEL_ID ต้องเป็นห้องข้อความ (ไม่ใช่ category / forum / voice)"))
        return out
    everyone = ch.permissions_for(guild.default_role)
    if not (everyone.view_channel and everyone.send_messages_in_threads and everyone.read_message_history):
        out.append(("❌", f"{ch.mention}: @everyone ต้องมี View Channel + Send Messages in Threads + Read Message History "
                          "(คนที่ยังไม่มี role ต้องคุยใน ticket ของตัวเองได้)"))
    if everyone.send_messages or everyone.create_public_threads:
        out.append(("⚠️", f"{ch.mention}: แนะนำปิด Send Messages และ Create Public Threads ของ @everyone "
                          "(ไม่งั้นทุกคนพิมพ์ในห้องหลักได้)"))
    for rid in dict.fromkeys(cfg.staff_roles + cfg.admin_roles):
        role = guild.get_role(rid)
        if role and not (ch.permissions_for(role).manage_threads and ch.permissions_for(role).view_channel):
            out.append(("❌", f"{ch.mention}: role {role.mention} ต้องมี **Manage Threads** ถึงจะเห็น ticket ทุกอัน"))
    return out


async def run_checks(guild: discord.Guild, panel_channel=None) -> list:
    me = guild.me
    out = []
    if cfg.on_railway and not cfg.has_volume:
        out.append(("❌", "ยังไม่ได้ต่อ Volume ใน Railway — ข้อมูล ticket/whitelist/Steam/Donate หายทุกครั้งที่ deploy"))
    gp = me.guild_permissions
    need = ["manage_roles", "view_channel", "send_messages", "embed_links", "attach_files",
            "read_message_history"] + (["manage_nicknames"] if cfg.set_nickname else [])
    missing = [PERM_NAMES[x] for x in need if not getattr(gp, x)]
    out.append(("❌", f"สิทธิ์ระดับเซิฟของ role {me.top_role.mention} ขาด **{', '.join(missing)}** → Server Settings → Roles")
               if missing else ("✅", "สิทธิ์ระดับเซิฟครบ"))
    for label, rid in (("Survivor", cfg.survivor_role), ("Member", cfg.member_role)):
        if not rid:
            continue
        role = guild.get_role(rid)
        if role is None:
            out.append(("❌", f"role {label}: ไม่เจอ ID `{rid}`"))
        elif role >= me.top_role:
            out.append(("❌", f"role {label} ({role.mention}) อยู่สูงกว่า/เท่ากับ role บอท → ลาก role "
                              f"**{me.top_role.name}** ขึ้นไปไว้เหนือ {role.name}"))
        else:
            out.append(("✅", f"บอทแจก role {label} ได้"))
    for rid in cfg.staff_roles + cfg.admin_roles:
        if guild.get_role(rid) is None:
            out.append(("❌", f"role ทีมแอดมิน: ไม่เจอ ID `{rid}`"))
    out += check_ticket_channel(guild)
    out += check_channel(guild, cfg.transcripts, "ห้อง transcript",
                         ["view_channel", "send_messages", "embed_links", "attach_files"])
    out += check_channel(guild, cfg.whitelist_log, "ห้อง whitelist-log", ["view_channel", "send_messages", "embed_links"])
    out += check_channel(guild, cfg.mod_logs, "ห้อง mod-logs", ["view_channel", "send_messages", "embed_links"])
    if cfg.donate_enabled:
        out += check_channel(guild, cfg.donate_log, "ห้อง donate-log", ["view_channel", "send_messages", "embed_links"])
    if cfg.rules_channel and guild.get_channel(cfg.rules_channel) is None:
        out.append(("❌", f"RULES_CHANNEL_ID `{cfg.rules_channel}` ไม่เจอ — ปุ่มกฎจะลิงก์ไปห้องที่ไม่มี"))
    elif not cfg.rules_channel:
        out.append(("➖", "ไม่ได้ตั้ง RULES_CHANNEL_ID — ข้อความต้อนรับจะไม่มีปุ่มไปห้องกฎ"))
    if panel_channel is not None:
        out += check_channel(guild, panel_channel.id, "ห้องที่จะส่งข้อความ",
                             ["view_channel", "send_messages", "embed_links", "attach_files", "read_message_history"])

    if cfg.steam_api_key:
        try:
            await steam.lookup("76561197960287930")
            out.append(("✅", "STEAM_API_KEY ใช้ได้"))
        except SteamError as e:
            out.append(("❌", f"Steam: {e}"))
    elif cfg.steam_required:
        out.append(("❌", "ยังไม่ได้ตั้ง STEAM_API_KEY"))
    if cfg.donate_enabled:
        try:
            await stripe.ping()
            mode = "ทดสอบ (test)" if "_test_" in cfg.stripe_secret_key else "จริง (live)"
            out.append(("✅", f"Stripe ต่อได้ — โหมด{mode} · รายการที่เปิดอยู่ {len(db.items())} รายการ"))
        except StripeError as e:
            out.append(("❌", f"Stripe: {e}"))
    else:
        out.append(("➖", "ยังไม่ได้ตั้ง STRIPE_SECRET_KEY — ระบบ Donate ปิดอยู่"))
    if cfg.rcon_enabled:
        ok, resp = await run_rcon("players")
        out.append(("✅", f"RCON ต่อได้ — `{trunc(resp, 150)}`") if ok else ("❌", f"RCON: {resp}"))
    return out


# =====================================================================
# Slash commands
# =====================================================================

# ซ่อนคำสั่งจากผู้เล่นทั่วไป (ปรับได้ที่ Server Settings → Integrations → บอท)
ADMIN_PERMS = discord.Permissions(manage_guild=True)
STAFF_PERMS = discord.Permissions(manage_threads=True)


async def require(interaction: discord.Interaction, check, message="คำสั่งนี้สำหรับแอดมินเท่านั้น") -> bool:
    if check(interaction.user):
        return True
    await reply(interaction, message)
    return False


@bot.tree.command(name="check", description="ตรวจว่าบอทมีสิทธิ์ครบไหม และ Steam / Stripe ใช้ได้ไหม")
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(panel_channel="ห้องที่จะส่งข้อความต้อนรับ (ถ้าอยากเช็คด้วย)")
async def cmd_check(interaction: discord.Interaction, panel_channel: Optional[discord.TextChannel] = None):
    if not await require(interaction, is_admin):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    results = await run_checks(interaction.guild, panel_channel)
    bad = sum(1 for icon, _ in results if icon == "❌")
    embed = discord.Embed(title="ผลตรวจบอท", color=COLOR_BAD if bad else COLOR_OK,
                          description=trunc("\n".join(f"{icon} {text}" for icon, text in results), 4000))
    embed.set_footer(text=f"มีปัญหา {bad} จุด" if bad else "ผ่านทุกข้อ")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="panel", description="ส่งข้อความต้อนรับ / ปุ่มเปิด Ticket / ป้าย Donate ลงห้อง")
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(kind="ชนิดข้อความ", channel="ห้องที่จะส่ง (ไม่ใส่ = ห้องนี้)")
@app_commands.choices(kind=[
    app_commands.Choice(name="welcome — ต้อนรับ + ปุ่ม Join", value="welcome"),
    app_commands.Choice(name="ticket — ปุ่มเปิด Ticket (เลือกหมวด)", value="ticket"),
    app_commands.Choice(name="donate — รายการ Donate + ปุ่ม Donate", value="donate"),
])
async def cmd_panel(interaction: discord.Interaction, kind: app_commands.Choice[str],
                    channel: Optional[discord.TextChannel] = None):
    if not await require(interaction, is_admin):
        return
    target = channel or interaction.channel
    p = target.permissions_for(interaction.guild.me)
    missing = [PERM_NAMES[x] for x in ("view_channel", "send_messages", "embed_links", "attach_files")
               if not getattr(p, x)]
    if missing:
        return await reply(interaction, f"บอทส่งลง {target.mention} ไม่ได้ — ขาด **{', '.join(missing)}**\n"
                                        f"Edit Channel/Category → Permissions → เพิ่ม role "
                                        f"**{interaction.guild.me.top_role.name}** แล้วติ๊ก ✓ ให้ครบ")
    kwargs = {}
    if kind.value == "welcome":
        banner_file = find_banner_file()
        if banner_file:
            name = f"banner{banner_file.suffix}"
            kwargs["file"] = discord.File(banner_file, filename=name)
            kwargs["view"] = WelcomeView(banner=f"attachment://{name}")
        else:
            kwargs["view"] = WelcomeView(banner=cfg.welcome_banner_url or None)
    elif kind.value == "ticket":
        kwargs["view"] = TicketPanelView()
    else:
        if not cfg.donate_enabled:
            return await reply(interaction, "ยังไม่ได้ตั้ง STRIPE_SECRET_KEY")
        kwargs.update(embed=catalog_embed(in_thread=False), view=DonatePanelView())
    try:
        msg = await target.send(**kwargs)
    except discord.HTTPException as e:
        return await reply(interaction, f"ส่งไม่สำเร็จ: `{e.text or e}`")
    await reply(interaction, f"ส่งแล้ว: {msg.jump_url}")


ticket_group = app_commands.Group(name="ticket", description="จัดการ ticket ใน thread นี้", guild_only=True,
                              default_permissions=STAFF_PERMS)


@ticket_group.command(name="add", description="ดึงคนเข้า ticket นี้")
async def cmd_ticket_add(interaction: discord.Interaction, member: discord.Member):
    ticket, _ = await load_ticket(interaction)
    if not ticket:
        return
    await interaction.channel.add_user(member)
    await interaction.response.send_message(f"➕ {interaction.user.mention} เพิ่ม {member.mention} เข้า ticket",
                                            allowed_mentions=discord.AllowedMentions(users=[member]))


@ticket_group.command(name="remove", description="เอาคนออกจาก ticket นี้")
async def cmd_ticket_remove(interaction: discord.Interaction, member: discord.Member):
    ticket, _ = await load_ticket(interaction)
    if not ticket:
        return
    if member.id == ticket["owner_id"]:
        return await reply(interaction, "เอาเจ้าของ ticket ออกไม่ได้ — ปิด ticket แทน")
    await interaction.channel.remove_user(member)
    await interaction.response.send_message(f"➖ เอา {member.mention} ออกจาก ticket",
                                            allowed_mentions=discord.AllowedMentions.none())


@ticket_group.command(name="close", description="ปิด ticket นี้พร้อมเหตุผล")
async def cmd_ticket_close(interaction: discord.Interaction, reason: Optional[str] = None):
    ticket, _ = await load_ticket(interaction)
    if not ticket:
        return
    if ticket["status"] != "open":
        return await reply(interaction, "ticket นี้ปิดไปแล้ว")
    await interaction.response.defer(ephemeral=True, thinking=True)
    await close_ticket(interaction.guild, interaction.channel, ticket, interaction.user, reason)
    await interaction.followup.send("ปิดแล้ว", ephemeral=True)


wl_group = app_commands.Group(name="whitelist", description="จัดการ White List", guild_only=True,
                          default_permissions=STAFF_PERMS)


@wl_group.command(name="remove", description="ถอดออกจาก White List (ถอด role Survivor + ให้คำสั่งลบในเซิฟ)")
@app_commands.describe(member="คนใน Discord", username="หรือใส่ username ในเกม", reason="เหตุผล")
async def cmd_wl_remove(interaction: discord.Interaction, member: Optional[discord.Member] = None,
                        username: Optional[str] = None, reason: Optional[str] = None):
    if not await require(interaction, is_staff):
        return
    if not member and not username:
        return await reply(interaction, "ใส่ member หรือ username อย่างน้อยหนึ่งอย่าง")
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    names = set()
    if member:
        names |= {row["username"] for row in db.wl_by_user(member.id)}
    if username:
        if not valid_username(username):
            return await interaction.followup.send("username มีตัวอักษรที่ใช้ไม่ได้", ephemeral=True)
        names.add(username)
        row = db.wl_get(username)
        if row and not member:
            member = await fetch_member(guild, row["discord_id"])
    if not names:
        return await interaction.followup.send("ไม่เจอ username ของคนนี้ในบันทึกของบอท — ใส่ username เองได้",
                                               ephemeral=True)
    notes = []
    for name in sorted(names):
        cmd = f'removeuserfromwhitelist "{name}"'
        ok, resp = await run_rcon(cmd)
        notes.append(f"`{name}`: RCON → `{trunc(resp, 200)}`" if ok else f"`{name}`: วางในคอนโซลเซิฟ ```{cmd}```")
        db.wl_deactivate(name)
    if member:
        role = guild.get_role(cfg.survivor_role)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=f"ถอด whitelist โดย {interaction.user}")
                notes.append(f"ถอด role {role.mention} จาก {member.mention} แล้ว")
            except discord.Forbidden:
                notes.append("❌ ถอด role ไม่ได้ (role บอทต้องอยู่เหนือ Survivor) — ถอดเอง")
    await log_to(guild, cfg.whitelist_log, discord.Embed(
        color=COLOR_BAD, timestamp=datetime.now(timezone.utc),
        description=f"**[REMOVE]** {', '.join(f'`{n}`' for n in sorted(names))}"
                    + (f" · {member.mention}" if member else "") + f" · โดย {interaction.user.mention}"
                    + (f"\nเหตุผล: {trunc(reason, 300)}" if reason else "")))
    await interaction.followup.send("\n".join(notes), ephemeral=True)


@wl_group.command(name="info", description="ดูว่าคนนี้ใช้ username / Steam อะไร")
async def cmd_wl_info(interaction: discord.Interaction, member: discord.Member):
    if not await require(interaction, is_staff):
        return
    rows = db.wl_by_user(member.id, active_only=False)
    lines = [f"`{r['username']}` — {'ใช้งาน' if r['active'] else 'ถูกถอดแล้ว'} · อนุมัติ {fmt_time(r['approved_at'])} "
             f"โดย <@{r['approved_by']}>" for r in rows] or [f"{member.mention} ยังไม่เคยผ่าน White List ผ่านบอท"]
    info = steam_info_of(db.steam_get(member.id))
    lines.append("**Steam:** " + (" · ".join(steam_summary(info)) if info else "ยังไม่ได้ผูก"))
    await reply(interaction, "\n".join(lines))


steam_group = app_commands.Group(name="steam", description="ข้อมูล Steam ที่ผูกกับผู้เล่น", guild_only=True,
                             default_permissions=STAFF_PERMS)


@steam_group.command(name="info", description="ดู Steam ที่ผูกกับคนนี้ (เช็คใหม่จาก Steam)")
async def cmd_steam_info(interaction: discord.Interaction, member: discord.Member):
    if not await require(interaction, is_staff):
        return
    row = db.steam_get(member.id)
    if not row:
        return await reply(interaction, f"{member.mention} ยังไม่ได้ผูก Steam")
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        info = await steam.lookup(row["steam_id"])
        db.steam_save(member.id, info)
    except SteamError as e:
        info = steam_info_of(row)
        info["_error"] = str(e)
    embed = discord.Embed(title=f"Steam ของ {member.display_name}", color=COLOR_INFO,
                          description="\n".join(steam_summary(info) + steam_checks(info)))
    if info.get("avatar"):
        embed.set_thumbnail(url=info["avatar"])
    if info.get("_error"):
        embed.set_footer(text=f"เช็คใหม่ไม่ได้ ({info['_error']}) — แสดงข้อมูลเดิม")
    await interaction.followup.send(embed=embed, ephemeral=True)


@steam_group.command(name="lookup", description="ใครใช้ Steam นี้อยู่ (ใส่ ID หรือลิงก์โปรไฟล์)")
async def cmd_steam_lookup(interaction: discord.Interaction, steam_id: str):
    if not await require(interaction, is_staff):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        id64 = await steam.resolve(steam_id)
    except SteamError as e:
        return await interaction.followup.send(f"❌ {e}", ephemeral=True)
    row = db.steam_by_steam(id64)
    await interaction.followup.send(f"`{id64}` ผูกกับ <@{row['discord_id']}>" if row else f"`{id64}` ยังไม่มีใครผูก",
                                    ephemeral=True)


@steam_group.command(name="unlink", description="ยกเลิกการผูก Steam ของคนนี้ (ให้ผู้เล่นใส่ใหม่ได้)")
async def cmd_steam_unlink(interaction: discord.Interaction, member: discord.Member):
    if not await require(interaction, is_staff):
        return
    row = db.steam_get(member.id)
    if not db.steam_unlink(member.id):
        return await reply(interaction, f"{member.mention} ไม่ได้ผูก Steam ไว้")
    await mod_log(interaction.guild, f"🔗 {interaction.user.mention} ยกเลิกผูก Steam `{row['steam_id']}` ของ {member.mention}")
    await reply(interaction, f"ยกเลิกแล้ว — {member.mention} กด Join แล้วใส่ Steam ใหม่ได้")


# ---------- /item (จัดการรายการ Donate) ----------

item_group = app_commands.Group(name="item", description="จัดการรายการ Donate (แอดมิน)", guild_only=True,
                            default_permissions=ADMIN_PERMS)


def _parse_price(text: str) -> int:
    try:
        return parse_baht(text)
    except ValueError:
        raise app_commands.AppCommandError(f"ราคา `{text}` ไม่ถูกต้อง — ใส่ตัวเลขบาท เช่น 50 หรือ 49.50")


@item_group.command(name="add", description="เพิ่มรายการ Donate ใหม่")
@app_commands.describe(code="รหัส (อังกฤษ/ตัวเลข/_ -) เช่น A01", name="ชื่อที่ผู้เล่นเห็น",
                       price="ยอดต่อชิ้น (บาท) เช่น 50", description="คำอธิบายสั้นๆ (ไม่ใส่ก็ได้)",
                       sort="ลำดับในรายการ (เลขน้อยขึ้นก่อน)")
async def cmd_item_add(interaction: discord.Interaction, code: str, name: str, price: str,
                       description: Optional[str] = None, sort: Optional[int] = 0):
    if not await require(interaction, is_admin):
        return
    code = code.strip()
    if not ITEM_CODE_RE.fullmatch(code):
        return await reply(interaction, "รหัสใช้ได้แค่อังกฤษ ตัวเลข _ - ยาวไม่เกิน 20 ตัว")
    if db.item_get(code):
        return await reply(interaction, f"รหัส `{code}` มีอยู่แล้ว — ใช้ /item edit แทน")
    satang = _parse_price(price)
    db.item_add(code, trunc(name.strip(), 80), satang, trunc((description or "").strip(), 200), sort or 0)
    await reply(interaction, f"เพิ่ม `{code}` **{name}** — {fmt_baht(satang)} แล้ว")
    await mod_log(interaction.guild, f"🧾 {interaction.user.mention} เพิ่มรายการ `{code}` {name} {fmt_baht(satang)}")


async def item_code_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=trunc(f"{i['code']} · {i['name']} · {fmt_baht(i['price'])}"
                                           + ("" if i["active"] else " (ปิด)"), 100), value=i["code"])
            for i in db.items(active_only=False) if current.casefold() in (i["code"] + i["name"]).casefold()][:25]


@item_group.command(name="edit", description="แก้รายการ Donate (ใส่เฉพาะช่องที่จะแก้)")
@app_commands.describe(code="รหัสเดิม", new_code="เปลี่ยนรหัสเป็น", name="ชื่อใหม่", price="ยอดต่อชิ้นใหม่ (บาท)",
                       description="คำอธิบายใหม่ (ใส่ - เพื่อลบ)", active="เปิดให้ Donate ไหม", sort="ลำดับ")
@app_commands.autocomplete(code=item_code_autocomplete)
async def cmd_item_edit(interaction: discord.Interaction, code: str, new_code: Optional[str] = None,
                        name: Optional[str] = None, price: Optional[str] = None,
                        description: Optional[str] = None, active: Optional[bool] = None,
                        sort: Optional[int] = None):
    if not await require(interaction, is_admin):
        return
    item = db.item_get(code)
    if item is None:
        return await reply(interaction, f"ไม่พบรหัส `{code}`")
    if new_code is not None:
        new_code = new_code.strip()
        if not ITEM_CODE_RE.fullmatch(new_code):
            return await reply(interaction, "รหัสใหม่ใช้ได้แค่อังกฤษ ตัวเลข _ - ยาวไม่เกิน 20 ตัว")
        clash = db.item_get(new_code)
        if clash and clash["code"].casefold() != item["code"].casefold():
            return await reply(interaction, f"รหัส `{new_code}` มีอยู่แล้ว")
    db.item_update(item["code"], code=new_code, name=trunc(name.strip(), 80) if name else None,
                   price=_parse_price(price) if price else None,
                   description=("" if description.strip() == "-" else trunc(description.strip(), 200))
                   if description is not None else None,
                   active=int(active) if active is not None else None, sort=sort)
    updated = db.item_get(new_code or item["code"])
    await reply(interaction, f"แก้แล้ว: `{updated['code']}` **{updated['name']}** — {fmt_baht(updated['price'])}"
                             f" · {'เปิด' if updated['active'] else 'ปิด'}")
    await mod_log(interaction.guild, f"🧾 {interaction.user.mention} แก้รายการ `{item['code']}` → `{updated['code']}`")


@item_group.command(name="remove", description="ลบรายการ Donate (ออร์เดอร์เก่ายังเก็บชื่อ/ยอดไว้)")
@app_commands.autocomplete(code=item_code_autocomplete)
async def cmd_item_remove(interaction: discord.Interaction, code: str):
    if not await require(interaction, is_admin):
        return
    item = db.item_get(code)
    if item is None or not db.item_delete(item["code"]):
        return await reply(interaction, f"ไม่พบรหัส `{code}`")
    await reply(interaction, f"ลบ `{item['code']}` {item['name']} แล้ว")
    await mod_log(interaction.guild, f"🧾 {interaction.user.mention} ลบรายการ `{item['code']}` {item['name']}")


@item_group.command(name="list", description="ดูรายการ Donate ทั้งหมด (รวมที่ปิดอยู่)")
async def cmd_item_list(interaction: discord.Interaction):
    if not await require(interaction, is_admin):
        return
    items = db.items(active_only=False)
    if not items:
        return await reply(interaction, "ยังไม่มีรายการ — เพิ่มด้วย /item add")
    rows = [f"{'🟢' if i['active'] else '⚫'} `{i['code']}` **{i['name']}** — {fmt_baht(i['price'])} · ลำดับ {i['sort']}"
            + (f"\n　{i['description']}" if i["description"] else "") for i in items]
    await reply(interaction, embed=discord.Embed(title=f"รายการ Donate ({len(items)})", color=COLOR_DONATE,
                                                 description=trunc("\n".join(rows), 4000)))


# ---------- /order ----------

order_group = app_commands.Group(name="order", description="ดู / จัดการรายการ Donate", guild_only=True,
                             default_permissions=STAFF_PERMS)
ORDER_STATUS_TH = {"cart": "กำลังเลือก", "review": "รอยืนยัน", "pending": "รอชำระ", "expired": "บิลหมดอายุ",
                   "paid": "จ่ายแล้ว รอส่งของ", "delivered": "ส่งของแล้ว", "cancelled": "ยกเลิก"}


@order_group.command(name="list", description="ดูรายการ Donate ล่าสุด")
@app_commands.describe(status="กรองตามสถานะ (ค่าเริ่มต้น = จ่ายแล้ว รอส่งของ)")
@app_commands.choices(status=[app_commands.Choice(name=v, value=k) for k, v in ORDER_STATUS_TH.items()])
async def cmd_order_list(interaction: discord.Interaction, status: Optional[app_commands.Choice[str]] = None):
    if not await require(interaction, is_staff):
        return
    key = status.value if status else "paid"
    orders = db.orders_with_status(key, limit=20)
    if not orders:
        return await reply(interaction, f"ไม่มีรายการสถานะ \"{ORDER_STATUS_TH[key]}\"")
    rows = [f"`#{o['id']:04d}` <@{o['owner_id']}> · {fmt_baht(o['total'])} · <#{o['thread_id']}>"
            + (f" · จ่าย {fmt_time(o['paid_at'])}" if o["paid_at"] else "") for o in orders]
    await reply(interaction, embed=discord.Embed(title=f"Donate — {ORDER_STATUS_TH[key]}", color=COLOR_DONATE,
                                                 description="\n".join(rows)))


@order_group.command(name="deliver", description="ยืนยันว่าส่งของแล้ว (เหมือนกดปุ่ม 📦)")
async def cmd_order_deliver(interaction: discord.Interaction, order_id: int):
    if not await require(interaction, is_staff):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    result = await mark_delivered(interaction.guild, order_id, interaction.user)
    await interaction.followup.send("บันทึกว่าส่งของแล้ว" if result == "ok" else result, ephemeral=True)


@order_group.command(name="check", description="เช็คสถานะการจ่ายกับ Stripe ทันที")
async def cmd_order_check(interaction: discord.Interaction, order_id: int):
    if not await require(interaction, is_staff):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    result = await sync_payment(order_id)
    order = db.order_get(order_id)
    status = ORDER_STATUS_TH.get(order["status"], order["status"]) if order else "-"
    await interaction.followup.send(f"#{order_id:04d}: {status} ({result})", ephemeral=True)


@bot.tree.command(name="rcon", description="ส่งคำสั่งไปที่เซิฟ PZ ผ่าน RCON (ถ้าเปิดไว้)")
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(command="เช่น players หรือ servermsg \"รีสตาร์ทใน 10 นาที\"")
async def cmd_rcon(interaction: discord.Interaction, command: str):
    if not await require(interaction, is_admin):
        return
    if not cfg.rcon_enabled:
        return await reply(interaction, "RCON ปิดอยู่ (RCON_ENABLED=false)")
    await interaction.response.defer(ephemeral=True, thinking=True)
    ok, resp = await run_rcon(command)
    await mod_log(interaction.guild, f"🖥️ {interaction.user.mention} ใช้ RCON: `{trunc(command, 200)}`")
    await interaction.followup.send(f"```{trunc(resp, 1900)}```" if ok else f"❌ {resp}", ephemeral=True)


for _group in (ticket_group, wl_group, steam_group, item_group, order_group):
    bot.tree.add_command(_group)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    if isinstance(original, discord.Forbidden):
        msg = "บอทขาดสิทธิ์ทำสิ่งนี้ — รัน /check ดูว่าขาดตรงไหน"
    elif type(error) is app_commands.AppCommandError:  # ข้อความที่เราโยนเอง (เช่น ราคาผิด)
        msg = str(error)
    else:
        log.error("คำสั่ง /%s พัง", interaction.command.name if interaction.command else "?", exc_info=original)
        msg = f"เกิดข้อผิดพลาด: `{trunc(str(original), 300)}`"
    try:
        await reply(interaction, msg)
    except discord.HTTPException:
        pass


# =====================================================================
# main
# =====================================================================

def setup_logging(data_dir: Optional[Path] = None):
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    if data_dir:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            file = RotatingFileHandler(data_dir / "bot.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8")
            file.setFormatter(fmt)
            root.addHandler(file)
        except OSError:
            pass
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def main():
    global cfg, db, rcon, TZ
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if load_dotenv:
        load_dotenv(BASE_DIR / ".env")
    try:
        cfg = load_config(os.environ)
    except ConfigError as e:
        setup_logging()
        log.error("%s", e)
        sys.exit(EXIT_CONFIG)
    setup_logging(cfg.data_dir)
    TZ = timezone(timedelta(hours=cfg.utc_offset))
    db = Database(cfg.data_dir / "cookiecheetah.db")
    log.info("เก็บข้อมูลที่ %s", cfg.data_dir)
    if cfg.rcon_enabled:
        rcon = Rcon(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password)
    try:
        bot.run(cfg.token, log_handler=None)
    except discord.LoginFailure:
        log.error("DISCORD_TOKEN ผิด — Developer Portal → Bot → Reset Token แล้วใส่ใหม่ใน Variables")
        sys.exit(EXIT_CONFIG)
    except discord.PrivilegedIntentsRequired:
        log.error("ต้องเปิด MESSAGE CONTENT INTENT: Developer Portal → Bot → Privileged Gateway Intents")
        sys.exit(EXIT_CONFIG)


if __name__ == "__main__":
    main()
