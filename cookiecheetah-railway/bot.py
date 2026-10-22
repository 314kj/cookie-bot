"""
CookieCheetah Bot — welcome + ticket (private thread) + whitelist + Steam + Donate (Stripe)
รันบน Railway (ตั้งค่าผ่าน Variables) ไม่ต้องใช้ akapanel

- ข้อความต้อนรับ (Components V2) มีปุ่มไปห้องกฎ + ปุ่ม 🍪 Join
- Join / ปุ่มเปิด Ticket → เลือกหมวด: ขอ White List (เฉพาะคนที่ยังไม่มี) / Donate / แจ้งบั๊ก / รีพอร์ต / ติดต่อแอดมิน
- ทุก ticket เป็น private thread ในห้อง ticket ห้องเดียว (ไม่สร้างห้องใหม่)
- White List: กรอก Steam ID → เช็คผ่าน Steam Web API → แอดมินกดอนุมัติ / ไม่ผ่าน
- Donate: ตะกร้า 5 รายการ → การ์ดสรุป → ยืนยัน → บิล Stripe (PromptPay QR / บัตร)
  → จ่ายแล้ว: ของที่ผูกรหัส Cookie Express ส่งเข้าเกมเอง · แพ็กคุกกี้เข้ากระเป๋าเอง · ที่เหลือแอดมินกด 📦
- แอดมินจัดการรายการ Donate ด้วย /item, ดูออเดอร์ด้วย /order
- แจ้งบั๊ก / ติดต่อแอดมิน: บอทถามตอบตาม faq.json ก่อน แล้วค่อยส่งต่อแอดมิน
- คุกกี้ 🍪: หมุนวงล้อรายวัน · กระเป๋าส่วนตัว (private thread) · ร้านแลกของ → ส่งเข้าเกมผ่าน Cookie Express
- ห้องสรุป ticket สำหรับแอดมิน (แก้ข้อความเดิม ไม่ส่งใหม่) · เตือนคนที่ยังไม่ขอ White List ทุกวัน
- หน้าเว็บแคตตาล็อกร้าน (บอทเปิดเองบน Railway ไม่ต้อง host เพิ่ม)
"""

import asyncio
import hashlib
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
from aiohttp import web
from discord import app_commands, ui

import faq_engine
import ckx_link
import web_catalog
import web_site

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
    "รอแอดมินอนุมัติภายใน 24 ชม. แล้วจะได้วิธีเข้าเกม ✅",
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
    faq_start: str = ""  # ไม่ว่าง = เริ่มด้วยบอทถามตอบ (faq.json) ก่อนเรียกแอดมิน


TICKET_TYPES = {
    "wl": TicketType(
        key="wl", label="ขอ White List", emoji="📝", prefix="wl", color=0x2ECC71,
        menu_text="สมัครเข้าเล่นเซิฟ (กรอก Steam + แบบสอบถาม)", modal_title="คำขอ White List",
        welcome=("{user} ได้รับคำขอแล้ว แอดมินจะตรวจข้อมูลด้านล่างและตอบในห้องนี้ภายใน 24 ชม. "
                 "อย่าเพิ่งออกจากเซิฟ Discord นะ"),
        questions=(
            Question("steam", "Steam ID หรือลิงก์โปรไฟล์ Steam", required=True, max_length=200,
                     placeholder="เช่น https://steamcommunity.com/id/xxx หรือ 7656119xxxxxxxxxx"),
            Question("username", "ชื่อในเกมที่จะตั้ง (ใช้ส่งของให้)", required=True,
                     max_length=32, placeholder="ตั้งชื่อนี้ตอนสมัครในเกมครั้งแรก เช่น Somchai_99"),
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
        menu_text="เข้าเกมไม่ได้ กระตุก จอดำ หรือเจอบั๊ก",
        welcome=("{user} เชฟจะช่วยเช็กให้ก่อนนะคะ ปัญหาที่เจอบ่อยแก้ได้ทันที "
                 "ถ้าไม่หาย กด **คุยกับแอดมิน** ได้ทุกเมื่อ"),
        faq_start="menu",
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
        menu_text="เรื่องอื่นๆ",
        welcome="{user} ขอเช็กนิดนึงก่อนเรียกแอดมินนะคะ เผื่อมีวิธีแก้ให้ทันที",
        faq_start="contact_start",
    ),
}

# username ใส่ลงคำสั่ง removeuserfromwhitelist "..." จึงห้ามมี " หรือเว้นวรรค
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,32}$")
ITEM_CODE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,20}$")
MAX_CART_LINES = 5
COOKIE = "🍪"


def valid_username(name: str) -> bool:
    return bool(USERNAME_RE.fullmatch(name or ""))


def fmt_cookies(n) -> str:
    return f"{int(n or 0):,} {COOKIE}"


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
    set_nickname: bool = True
    # --- ห้องใหม่ ---
    join_channel: int = 0          # ห้อง #วิธีเข้าเซิฟ (ที่มีปุ่ม Join)
    newbie_channel: int = 0        # ห้อง newbie-cookies (การ์ดเตือนขอ White List)
    admin_alert_channel: int = 0   # ห้องแอดมินที่รับสรุปรายวัน (ว่าง = mod-logs)
    board_channel: int = 0         # ห้องสรุป ticket ของแอดมิน
    spin_channel: int = 0          # ห้องหมุนวงล้อรายวัน
    wallet_channel: int = 0        # ห้องที่เก็บกระเป๋าคุกกี้ (private thread) ว่าง = ห้องหมุน
    redeem_channel: int = 0        # ห้องร้านแลกของ
    redeem_log: int = 0            # log การแลกของ (ว่าง = donate-log / mod-logs)
    ckx_channel: int = 0           # ห้องลับของ Cookie Express relay
    ckx_relay_bot: int = 0         # user ID ของบอท relay (ว่าง = เชื่อทุกคนในห้องนั้นที่ไม่ใช่บอทนี้)
    mod_collection_url: str = "https://steamcommunity.com/sharedfiles/filedetails/?id=3820533354"
    wl_remind_hour: int = 20
    wl_remind_after_days: int = 3
    wl_remind_repeat_days: int = 3
    spin_result_seconds: int = 300
    public_url: str = ""
    web_enabled: bool = True
    web_port: int = 8080
    discord_client_id: str = ""      # ว่าง = ใช้ Application ID ของบอทนี้
    discord_client_secret: str = ""  # มีค่า = เปิดล็อกอินด้วย Discord + แลกของบนเว็บ
    invite_url: str = ""             # ลิงก์เชิญเข้าดิส (โชว์บนเว็บถ้าคนล็อกอินไม่ได้อยู่ในเซิฟ)
    web_editor_ids: list = field(default_factory=list)  # user ID ที่แก้ร้านบนเว็บได้ (ว่าง = เจ้าของเซิฟคนเดียว)
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
        set_nickname=_bool(env, "SET_NICKNAME", True),
        join_channel=_int(env, "JOIN_CHANNEL_ID"),
        newbie_channel=_int(env, "NEWBIE_CHANNEL_ID"),
        admin_alert_channel=_int(env, "ADMIN_ALERT_CHANNEL_ID"),
        board_channel=_int(env, "TICKET_BOARD_CHANNEL_ID"),
        spin_channel=_int(env, "SPIN_CHANNEL_ID"),
        wallet_channel=_int(env, "WALLET_CHANNEL_ID") or _int(env, "SPIN_CHANNEL_ID"),
        redeem_channel=_int(env, "REDEEM_CHANNEL_ID"),
        redeem_log=_int(env, "REDEEM_LOG_CHANNEL_ID"),
        ckx_channel=_int(env, "CKX_CHANNEL_ID"),
        ckx_relay_bot=_int(env, "CKX_RELAY_BOT_ID"),
        mod_collection_url=_str(env, "MOD_COLLECTION_URL",
                                "https://steamcommunity.com/sharedfiles/filedetails/?id=3820533354"),
        wl_remind_hour=max(0, min(23, _int(env, "WL_REMIND_HOUR", 20))),
        wl_remind_after_days=max(0, _int(env, "WL_REMIND_AFTER_DAYS", 3)),
        wl_remind_repeat_days=max(1, _int(env, "WL_REMIND_REPEAT_DAYS", 3)),
        spin_result_seconds=max(30, min(840, _int(env, "SPIN_RESULT_SECONDS", 300))),
        public_url=(_str(env, "PUBLIC_URL") or (f"https://{_str(env, 'RAILWAY_PUBLIC_DOMAIN')}"
                                                 if _str(env, "RAILWAY_PUBLIC_DOMAIN") else "")).rstrip("/"),
        web_enabled=_bool(env, "WEB_ENABLED", True),
        web_port=_int(env, "PORT", 8080),
        discord_client_id=_str(env, "DISCORD_CLIENT_ID"),
        discord_client_secret=_str(env, "DISCORD_CLIENT_SECRET"),
        invite_url=_str(env, "DISCORD_INVITE_URL"),
        web_editor_ids=_ids(env, "WEB_EDITOR_IDS"),
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
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS wallets(
                discord_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                ingame TEXT NOT NULL DEFAULT '',
                thread_id INTEGER,
                card_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ledger(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                kind TEXT NOT NULL,
                ref TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                by_id INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ledger_user ON ledger(discord_id, id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_once ON ledger(discord_id, kind, ref) WHERE ref != '';
            CREATE TABLE IF NOT EXISTS spin_pool(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                cookies INTEGER NOT NULL,
                weight INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS spins(
                discord_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                pool_id INTEGER,
                label TEXT NOT NULL,
                cookies INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(discord_id, day)
            );
            CREATE TABLE IF NOT EXISTS shop_items(
                code TEXT PRIMARY KEY COLLATE NOCASE,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price INTEGER NOT NULL,
                ckx TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                image TEXT NOT NULL DEFAULT '',
                per_user_limit INTEGER NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT -1,
                start_at TEXT NOT NULL DEFAULT '',
                end_at TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                sort INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS redemptions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                qty INTEGER NOT NULL,
                ckx TEXT NOT NULL DEFAULT '',
                ingame TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued',
                job_id INTEGER,
                receipt_id INTEGER,
                log_id INTEGER,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_redeem_user ON redemptions(discord_id, code);
            CREATE TABLE IF NOT EXISTS ckx_jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                ref_id INTEGER NOT NULL,
                discord_id INTEGER NOT NULL,
                ingame TEXT NOT NULL,
                items TEXT NOT NULL,
                msg_id INTEGER UNIQUE,
                status TEXT NOT NULL DEFAULT 'posting',
                lines_total INTEGER NOT NULL DEFAULT 0,
                lines_done INTEGER NOT NULL DEFAULT 0,
                info TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS remind_log(
                discord_id INTEGER PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0,
                last_at TEXT
            );
            CREATE TABLE IF NOT EXISTS relay_seen(msg_id INTEGER PRIMARY KEY, at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS carts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL,
                nonce TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                ingame TEXT NOT NULL DEFAULT '',
                receipt_id INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(discord_id, nonce)
            );
            CREATE TABLE IF NOT EXISTS remind_batches(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_ids TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                sent_by INTEGER,
                admin_msg_id INTEGER
            );
            """
        )
        # ฐานข้อมูลจากเวอร์ชันก่อน: เติมคอลัมน์ที่ยังไม่มี (ข้อมูลเดิมไม่หาย)
        for table, column in (
                ("whitelist", "steam_id TEXT"),
                ("tickets", "mode TEXT NOT NULL DEFAULT ''"),
                ("tickets", "faq_node TEXT NOT NULL DEFAULT ''"),
                ("tickets", "faq_path TEXT NOT NULL DEFAULT '[]'"),
                ("tickets", "last_user_at TEXT"),
                ("tickets", "last_staff_at TEXT"),
                ("tickets", "scanned INTEGER NOT NULL DEFAULT 0"),
                ("items", "cookies INTEGER NOT NULL DEFAULT 0"),
                ("items", "ckx TEXT NOT NULL DEFAULT ''"),
                ("orders", "ingame TEXT NOT NULL DEFAULT ''"),
                ("orders", "job_id INTEGER"),
                ("orders", "cookies_given INTEGER NOT NULL DEFAULT 0"),
                ("redemptions", "cart_id INTEGER"),
                ("orders", "web_nonce TEXT"),
                ("items", "image TEXT NOT NULL DEFAULT ''")):
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column}")
            except sqlite3.OperationalError:
                pass
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_redeem_cart ON redemptions(cart_id)")
        self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_web ON orders(owner_id, web_nonce) "
                          "WHERE web_nonce IS NOT NULL")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_owner ON orders(owner_id, id)")
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

    def item_add(self, code, name, price, description="", sort=0, cookies=0, ckx="", active=1, image=""):
        with self.conn:
            self.conn.execute(
                "INSERT INTO items(code, name, price, description, active, sort, updated_at, cookies, ckx, image) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (code, name, price, description, int(active), sort, self._now(), cookies, ckx, image or ""))

    def item_update(self, old_code, **fields):
        """fields: code (รหัสใหม่) / name / price / description / active / sort / cookies / ckx / image — None = ไม่แก้"""
        allowed = {"code", "name", "price", "description", "active", "sort", "cookies", "ckx", "image"}
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
                   "stripe_expires", "attempt", "paid_at", "delivered_at", "delivered_by", "ingame", "job_id",
                   "cookies_given"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if "lines" in sets and not isinstance(sets["lines"], str):
            sets["lines"] = json.dumps(sets["lines"], ensure_ascii=False)
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE orders SET {cols} WHERE id=?", (*sets.values(), order_id))

    def order_create_web(self, ticket_id, thread_id, owner_id, nonce, lines, total, ingame):
        """ออเดอร์จากหน้าเว็บ (ข้ามขั้นตะกร้า → รอยืนยัน) — nonce เดิมของคนเดิม = None (กดซ้ำ)"""
        try:
            with self.conn:
                return self.conn.execute(
                    "INSERT INTO orders(ticket_id, thread_id, owner_id, lines, total, status, ingame, web_nonce, "
                    "created_at) VALUES(?,?,?,?,?,'review',?,?,?)",
                    (ticket_id, thread_id, owner_id, json.dumps(lines, ensure_ascii=False), total, ingame, nonce,
                     self._now())).lastrowid
        except sqlite3.IntegrityError:
            return None

    def order_by_nonce(self, owner_id, nonce):
        return self.conn.execute("SELECT * FROM orders WHERE owner_id=? AND web_nonce=?", (owner_id, nonce)).fetchone()

    def orders_of(self, owner_id, limit=10):
        """ออเดอร์ล่าสุดของคนนี้ (ไม่รวมตะกร้าที่ยังไม่ส่งใน Discord)"""
        return self.conn.execute("SELECT * FROM orders WHERE owner_id=? AND status != 'cart' ORDER BY id DESC LIMIT ?",
                                 (owner_id, limit)).fetchall()

    def orders_in_thread(self, thread_id, statuses):
        marks = ",".join("?" * len(statuses))
        return self.conn.execute(f"SELECT * FROM orders WHERE thread_id=? AND status IN ({marks}) ORDER BY id DESC",
                                 (thread_id, *statuses)).fetchall()

    # --- settings (แก้ใน Discord ได้) ---
    def setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        with self.conn:
            if value is None:
                self.conn.execute("DELETE FROM settings WHERE key=?", (key,))
            else:
                self.conn.execute("INSERT INTO settings(key, value) VALUES(?,?) "
                                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    # --- ticket activity / FAQ ---
    def ticket_update(self, ticket_id, **fields):
        allowed = {"mode", "faq_node", "faq_path", "last_user_at", "last_staff_at", "scanned", "claimed_by"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE tickets SET {cols} WHERE id=?", (*sets.values(), ticket_id))

    def tickets_for_board(self, closed_since_iso: str):
        return self.conn.execute(
            "SELECT * FROM tickets WHERE status='open' OR (status IN ('closed','deleted') AND closed_at >= ?) "
            "OR id IN (SELECT ticket_id FROM orders WHERE status='paid') "
            "ORDER BY id DESC LIMIT 400", (closed_since_iso,)).fetchall()

    def order_paid_in_thread(self, thread_id):
        return self.conn.execute("SELECT * FROM orders WHERE thread_id=? AND status='paid' ORDER BY id LIMIT 1",
                                 (thread_id,)).fetchone()

    def ever_requested_wl(self) -> set:
        return {r[0] for r in self.conn.execute("SELECT DISTINCT owner_id FROM tickets WHERE type='wl'")}

    def order_latest_in_thread(self, thread_id):
        return self.conn.execute("SELECT * FROM orders WHERE thread_id=? ORDER BY id DESC LIMIT 1",
                                 (thread_id,)).fetchone()

    # --- คุกกี้ 🍪 ---
    def wallet_get(self, discord_id):
        return self.conn.execute("SELECT * FROM wallets WHERE discord_id=?", (discord_id,)).fetchone()

    def wallet_ensure(self, discord_id):
        now = self._now()
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO wallets(discord_id, created_at, updated_at) VALUES(?,?,?)",
                              (discord_id, now, now))
        return self.wallet_get(discord_id)

    def wallet_update(self, discord_id, **fields):
        allowed = {"ingame", "thread_id", "card_id"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        self.wallet_ensure(discord_id)
        sets["updated_at"] = self._now()
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE wallets SET {cols} WHERE discord_id=?", (*sets.values(), discord_id))

    def wallet_by_thread(self, thread_id):
        return self.conn.execute("SELECT * FROM wallets WHERE thread_id=?", (thread_id,)).fetchone()

    def _cookies(self, discord_id, delta, kind, ref="", note="", by=None, allow_negative=False):
        """ใช้ใน transaction ที่เปิดอยู่แล้ว — คืน (ok, balance_or_reason)"""
        now = self._now()
        self.conn.execute("INSERT OR IGNORE INTO wallets(discord_id, created_at, updated_at) VALUES(?,?,?)",
                          (discord_id, now, now))
        if ref and self.conn.execute("SELECT 1 FROM ledger WHERE discord_id=? AND kind=? AND ref=?",
                                     (discord_id, kind, ref)).fetchone():
            return False, "dup"
        balance = self.conn.execute("SELECT balance FROM wallets WHERE discord_id=?", (discord_id,)).fetchone()[0]
        new = balance + int(delta)
        if new < 0 and not allow_negative:
            return False, "poor"
        self.conn.execute("UPDATE wallets SET balance=?, updated_at=? WHERE discord_id=?", (new, now, discord_id))
        self.conn.execute("INSERT INTO ledger(discord_id, delta, balance_after, kind, ref, note, by_id, created_at) "
                          "VALUES(?,?,?,?,?,?,?,?)", (discord_id, int(delta), new, kind, ref, note, by, now))
        return True, new

    def cookies_add(self, discord_id, delta, kind, ref="", note="", by=None, allow_negative=False):
        with self.conn:
            return self._cookies(discord_id, delta, kind, ref, note, by, allow_negative)

    def ledger_recent(self, discord_id, limit=8):
        return self.conn.execute("SELECT * FROM ledger WHERE discord_id=? ORDER BY id DESC LIMIT ?",
                                 (discord_id, limit)).fetchall()

    # --- วงล้อรายวัน ---
    def spin_pool(self, active_only=True):
        q = "SELECT * FROM spin_pool" + (" WHERE active=1" if active_only else "") + " ORDER BY cookies, id"
        return self.conn.execute(q).fetchall()

    def spin_pool_get(self, pool_id):
        return self.conn.execute("SELECT * FROM spin_pool WHERE id=?", (pool_id,)).fetchone()

    def spin_pool_add(self, label, cookies, weight) -> int:
        with self.conn:
            return self.conn.execute("INSERT INTO spin_pool(label, cookies, weight) VALUES(?,?,?)",
                                     (label, cookies, weight)).lastrowid

    def spin_pool_update(self, pool_id, **fields):
        sets = {k: v for k, v in fields.items() if k in {"label", "cookies", "weight", "active"} and v is not None}
        if not sets:
            return
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE spin_pool SET {cols} WHERE id=?", (*sets.values(), pool_id))

    def spin_pool_delete(self, pool_id) -> bool:
        with self.conn:
            return self.conn.execute("DELETE FROM spin_pool WHERE id=?", (pool_id,)).rowcount > 0

    def spin_today(self, discord_id, day):
        return self.conn.execute("SELECT * FROM spins WHERE discord_id=? AND day=?", (discord_id, day)).fetchone()

    def spin_record(self, discord_id, day, prize) -> Optional[int]:
        """บันทึกผลหมุน + เติมคุกกี้ในทีเดียว — คืนยอดใหม่ หรือ None ถ้าวันนี้หมุนไปแล้ว"""
        with self.conn:
            try:
                self.conn.execute("INSERT INTO spins(discord_id, day, pool_id, label, cookies, created_at) "
                                  "VALUES(?,?,?,?,?,?)", (discord_id, day, prize["id"], prize["label"],
                                                          prize["cookies"], self._now()))
            except sqlite3.IntegrityError:
                return None
            ok, balance = self._cookies(discord_id, prize["cookies"], "spin", ref=day, note=prize["label"])
            if not ok:
                raise sqlite3.IntegrityError("spin ledger dup")
            return balance

    def spin_reset(self, discord_id, day) -> bool:
        with self.conn:
            return self.conn.execute("DELETE FROM spins WHERE discord_id=? AND day=?", (discord_id, day)).rowcount > 0

    # --- ร้านแลกของ ---
    def shop_get(self, code):
        return self.conn.execute("SELECT * FROM shop_items WHERE code=?", ((code or "").strip(),)).fetchone()

    def shop_items(self, active_only=True):
        q = "SELECT * FROM shop_items" + (" WHERE active=1" if active_only else "") + " ORDER BY sort, code"
        return self.conn.execute(q).fetchall()

    def shop_add(self, **f):
        f.setdefault("updated_at", self._now())
        cols = ", ".join(f)
        with self.conn:
            self.conn.execute(f"INSERT INTO shop_items({cols}) VALUES({','.join('?' * len(f))})", tuple(f.values()))

    def shop_update(self, old_code, **fields):
        allowed = {"code", "name", "description", "price", "ckx", "category", "image", "per_user_limit", "stock",
                   "start_at", "end_at", "active", "sort"}
        sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not sets:
            return
        sets["updated_at"] = self._now()
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE shop_items SET {cols} WHERE code=?", (*sets.values(), old_code))
            if sets.get("code") and sets["code"] != old_code:  # เปลี่ยนรหัส → ใบแลกเดิมตามไปด้วย (สิทธิ์ต่อคน/คืนสต็อก)
                self.conn.execute("UPDATE redemptions SET code=? WHERE code=? COLLATE NOCASE",
                                  (sets["code"], old_code))

    def shop_delete(self, code) -> bool:
        with self.conn:
            return self.conn.execute("DELETE FROM shop_items WHERE code=?", (code,)).rowcount > 0

    def redeemed_qty(self, discord_id, code) -> int:
        row = self.conn.execute("SELECT COALESCE(SUM(qty),0) FROM redemptions WHERE discord_id=? "
                                "AND code=? COLLATE NOCASE AND status != 'refunded'", (discord_id, code)).fetchone()
        return int(row[0])

    def redeem(self, discord_id, code, qty, ingame, now: datetime):
        """หักคุกกี้ + จองของ + สร้างใบแลก ในทีเดียว — คืน (redemption_id, None) หรือ (None, เหตุผล)"""
        try:
            with self.conn:
                return self._redeem_line(discord_id, code, qty, ingame, now), None
        except _Rollback as e:
            return None, str(e)

    def _redeem_line(self, discord_id, code, qty, ingame, now: datetime, cart_id=None, prefix="") -> int:
        """ใช้ใน with self.conn: — ผิดเงื่อนไขโยน _Rollback(เหตุผล) ให้ยกเลิกทั้ง transaction"""
        item = self.shop_get(code)
        problem = shop_problem(item, now)
        if problem:
            raise _Rollback(prefix + problem)
        if qty < 1:
            raise _Rollback(prefix + "จำนวนต้องมากกว่า 0")
        if item["per_user_limit"]:
            left = item["per_user_limit"] - self.redeemed_qty(discord_id, item["code"])
            if left <= 0:
                raise _Rollback(f"แลก {item['name']} ครบ {item['per_user_limit']} ครั้งแล้ว")
            if qty > left:
                raise _Rollback(prefix + f"แลกได้อีกแค่ {left} ชิ้น")
        if item["stock"] >= 0 and qty > item["stock"]:
            raise _Rollback(prefix + ("ของหมดแล้ว" if item["stock"] == 0 else f"เหลือแค่ {item['stock']} ชิ้น"))
        cost = item["price"] * qty
        now_iso = now.isoformat()
        cur = self.conn.execute(
            "INSERT INTO redemptions(discord_id, code, name, price, qty, ckx, ingame, status, cart_id, created_at, "
            "updated_at) VALUES(?,?,?,?,?,?,?,'queued',?,?,?)",
            (discord_id, item["code"], item["name"], item["price"], qty, item["ckx"], ingame, cart_id, now_iso,
             now_iso))
        rid = cur.lastrowid
        ok, why = self._cookies(discord_id, -cost, "redeem", ref=f"rd-{rid}", note=f"{item['name']} × {qty}")
        if not ok:
            raise _Rollback("คุกกี้ไม่พอ" if why == "poor" else "แลกซ้ำ ลองใหม่อีกครั้ง")
        if item["stock"] >= 0:
            self.conn.execute("UPDATE shop_items SET stock=stock-? WHERE code=?", (qty, item["code"]))
        return rid

    # --- ตะกร้า (แลกหลายชิ้นจากหน้าเว็บ) ---
    def redeem_cart(self, discord_id, lines, ingame, now: datetime, nonce: str, ckx_items: dict = None):
        """แลกทั้งตะกร้าใน transaction เดียว: ผ่านทุกชิ้นหรือไม่ได้สักชิ้น
        (หักคุกกี้ + ตัดสต็อก + ใบแลก + งานส่งเข้าเกม + ชื่อในเกม — commit พร้อมกันหมด)
        lines = [(code, qty)] · ckx_items = {code: รหัสที่คูณจำนวนแล้ว}
        → (cart_id, [redemption_id], None) หรือ (None, None, เหตุผล)"""
        ckx_items = ckx_items or {}
        try:
            with self.conn:
                now_iso = now.isoformat()
                cart_id = self.conn.execute(
                    "INSERT INTO carts(discord_id, nonce, ingame, created_at) VALUES(?,?,?,?)",
                    (discord_id, nonce, ingame, now_iso)).lastrowid
                rids, total = [], 0
                for code, qty in lines:
                    item = self.shop_get(code)
                    prefix = f"{item['name']}: " if item else f"{code}: "
                    rid = self._redeem_line(discord_id, code, qty, ingame, now, cart_id=cart_id, prefix=prefix)
                    rids.append(rid)
                    total += item["price"] * qty
                    items = ckx_items.get(code)
                    if items:
                        job_id = self.conn.execute(
                            "INSERT INTO ckx_jobs(kind, ref_id, discord_id, ingame, items, lines_total, created_at, "
                            "updated_at) VALUES('redeem',?,?,?,?,?,?,?)",
                            (rid, discord_id, ingame, items, ckx_link.count_lines(items), now_iso, now_iso)).lastrowid
                        self.conn.execute("UPDATE redemptions SET job_id=?, status='posting' WHERE id=?", (job_id, rid))
                    else:
                        self.conn.execute("UPDATE redemptions SET status='manual' WHERE id=?", (rid,))
                self.conn.execute("UPDATE carts SET total=? WHERE id=?", (total, cart_id))
                if ingame:
                    self.conn.execute("UPDATE wallets SET ingame=?, updated_at=? WHERE discord_id=?",
                                      (ingame, now_iso, discord_id))
                return cart_id, rids, None
        except _Rollback as e:
            return None, None, str(e)
        except sqlite3.IntegrityError:
            return None, None, "dup"

    def cart_get(self, cart_id):
        return self.conn.execute("SELECT * FROM carts WHERE id=?", (cart_id,)).fetchone()

    def cart_by_nonce(self, discord_id, nonce):
        return self.conn.execute("SELECT * FROM carts WHERE discord_id=? AND nonce=?", (discord_id, nonce)).fetchone()

    def cart_lines(self, cart_id):
        return self.conn.execute("SELECT * FROM redemptions WHERE cart_id=? ORDER BY id", (cart_id,)).fetchall()

    def carts_unfinished(self, days=7):
        """ตะกร้าที่ยังโพสต์ใน Discord ไม่ครบ (บอทรีสตาร์ทกลางทาง) — ทำต่อตอนเปิดบอท"""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return self.conn.execute(
            "SELECT * FROM carts WHERE created_at >= ? AND (receipt_id IS NULL OR id IN "
            "(SELECT cart_id FROM redemptions WHERE cart_id IS NOT NULL AND log_id IS NULL)) ORDER BY id",
            (since,)).fetchall()

    def cart_set_receipt(self, cart_id, receipt_id):
        with self.conn:
            self.conn.execute("UPDATE carts SET receipt_id=? WHERE id=?", (receipt_id, cart_id))

    def redemption_get(self, rid):
        return self.conn.execute("SELECT * FROM redemptions WHERE id=?", (rid,)).fetchone()

    def redemption_update(self, rid, **fields):
        allowed = {"status", "job_id", "receipt_id", "log_id", "note", "ingame"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        sets["updated_at"] = self._now()
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE redemptions SET {cols} WHERE id=?", (*sets.values(), rid))

    def redeem_stats(self, discord_id) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(price*qty),0), "
            "SUM(CASE WHEN status IN ('queued','posting','sent','inqueue','seen','partial','manual') THEN 1 ELSE 0 END) "
            "FROM redemptions WHERE discord_id=? AND status != 'refunded'", (discord_id,)).fetchone()
        return {"count": int(row[0] or 0), "spent": int(row[1] or 0), "pending": int(row[2] or 0)}

    def redemptions_of(self, discord_id, limit=6):
        return self.conn.execute("SELECT * FROM redemptions WHERE discord_id=? ORDER BY id DESC LIMIT ?",
                                 (discord_id, limit)).fetchall()

    def redemptions_recent(self, limit=20, statuses=None):
        if statuses:
            marks = ",".join("?" * len(statuses))
            return self.conn.execute(f"SELECT * FROM redemptions WHERE status IN ({marks}) ORDER BY id DESC LIMIT ?",
                                     (*statuses, limit)).fetchall()
        return self.conn.execute("SELECT * FROM redemptions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def refund(self, rid, by=None, note="คืนคุกกี้"):
        """คืนคุกกี้ + คืนสต็อก (ครั้งเดียวต่อใบ) — คืนยอดใหม่ หรือ None ถ้าคืนไปแล้ว"""
        with self.conn:
            r = self.redemption_get(rid)
            if r is None or r["status"] == "refunded":
                return None
            ok, balance = self._cookies(r["discord_id"], r["price"] * r["qty"], "refund", ref=f"rd-{rid}",
                                        note=note, by=by)
            if not ok:
                return None
            self.conn.execute("UPDATE redemptions SET status='refunded', updated_at=? WHERE id=?", (self._now(), rid))
            self.conn.execute("UPDATE shop_items SET stock=stock+? WHERE code=? AND stock >= 0", (r["qty"], r["code"]))
            return balance

    # --- งานส่งของผ่าน Cookie Express ---
    def job_create(self, kind, ref_id, discord_id, ingame, items, lines_total) -> int:
        now = self._now()
        with self.conn:
            return self.conn.execute(
                "INSERT INTO ckx_jobs(kind, ref_id, discord_id, ingame, items, lines_total, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?)", (kind, ref_id, discord_id, ingame, items, lines_total, now, now)).lastrowid

    def job_get(self, job_id):
        return self.conn.execute("SELECT * FROM ckx_jobs WHERE id=?", (job_id,)).fetchone()

    def job_by_msg(self, msg_id):
        return self.conn.execute("SELECT * FROM ckx_jobs WHERE msg_id=?", (msg_id,)).fetchone()

    def job_update(self, job_id, **fields):
        allowed = {"msg_id", "status", "lines_done", "info"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        sets["updated_at"] = self._now()
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE ckx_jobs SET {cols} WHERE id=?", (*sets.values(), job_id))

    def jobs_unsent(self):
        return self.conn.execute("SELECT * FROM ckx_jobs WHERE status='posting' ORDER BY id").fetchall()

    def relay_mark(self, msg_id) -> bool:
        """จดว่าอ่านข้อความ relay นี้แล้ว — False = เคยอ่านแล้ว (กันนับซ้ำตอนอ่านย้อนหลัง)"""
        with self.conn:
            return self.conn.execute("INSERT OR IGNORE INTO relay_seen(msg_id, at) VALUES(?,?)",
                                     (msg_id, self._now())).rowcount > 0

    def relay_prune(self, days=30):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.conn:
            self.conn.execute("DELETE FROM relay_seen WHERE at < ?", (cutoff,))

    # --- เตือนขอ White List ---
    def remind_info(self, discord_id):
        return self.conn.execute("SELECT * FROM remind_log WHERE discord_id=?", (discord_id,)).fetchone()

    def remind_mark(self, ids):
        now = self._now()
        with self.conn:
            for i in ids:
                self.conn.execute("INSERT INTO remind_log(discord_id, count, last_at) VALUES(?,1,?) "
                                  "ON CONFLICT(discord_id) DO UPDATE SET count=count+1, last_at=excluded.last_at",
                                  (i, now))

    def batch_create(self, ids) -> int:
        with self.conn:
            return self.conn.execute("INSERT INTO remind_batches(user_ids, created_at) VALUES(?,?)",
                                     (json.dumps(list(ids)), self._now())).lastrowid

    def batch_claim(self, batch_id, by) -> bool:
        """จองชุดนี้ไว้ส่ง — กันกดส่งซ้ำ 2 ครั้ง"""
        with self.conn:
            return self.conn.execute("UPDATE remind_batches SET sent_at=?, sent_by=? WHERE id=? AND sent_at IS NULL",
                                     (self._now(), by, batch_id)).rowcount > 0

    def batch_get(self, batch_id):
        return self.conn.execute("SELECT * FROM remind_batches WHERE id=?", (batch_id,)).fetchone()

    def batch_update(self, batch_id, **fields):
        sets = {k: v for k, v in fields.items() if k in {"sent_at", "sent_by", "admin_msg_id", "user_ids"}}
        if "user_ids" in sets and not isinstance(sets["user_ids"], str):
            sets["user_ids"] = json.dumps(list(sets["user_ids"]))
        cols = ", ".join(f"{k}=?" for k in sets)
        with self.conn:
            self.conn.execute(f"UPDATE remind_batches SET {cols} WHERE id=?", (*sets.values(), batch_id))


class _Rollback(Exception):
    """โยนใน with self.conn: เพื่อยกเลิก transaction ทั้งก้อน"""


def shop_problem(item, now: datetime) -> Optional[str]:
    """ของชิ้นนี้แลกได้ตอนนี้ไหม — None = ได้"""
    if item is None or not item["active"]:
        return "ไม่มีของชิ้นนี้ หรือปิดอยู่"
    if item["start_at"] and now < datetime.fromisoformat(item["start_at"]):
        return "ยังไม่เปิดให้แลก"
    if item["end_at"] and now > datetime.fromisoformat(item["end_at"]):
        return "หมดเวลาแลกแล้ว"
    if item["stock"] == 0:
        return "ของหมดแล้ว"
    return None


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
            line.update(name=item["name"], unit=item["price"], cookies=item["cookies"], ckx=item["ckx"])
            return new
    if len(new) >= MAX_CART_LINES:
        raise CartError(f"ใส่ได้สูงสุด {MAX_CART_LINES} รายการต่อรอบ — ลบรายการเดิมก่อน หรือส่งรอบนี้แล้วทำรอบใหม่")
    if qty > max_qty:
        raise CartError(f"ใส่ได้ไม่เกิน {max_qty} ชิ้นต่อรายการ")
    new.append({"code": item["code"], "name": item["name"], "unit": item["price"], "qty": qty,
                "cookies": item["cookies"], "ckx": item["ckx"]})  # จำไว้ตอนใส่ตะกร้า แอดมินแก้ทีหลังไม่กระทบ
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
        if item["cookies"]:
            row += f" → **{fmt_cookies(item['cookies'])}**"
        elif item["ckx"]:
            row += " · 📦 ส่งเข้าเกมเอง"
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
                              idempotency_key: str, cancel_url: str = "") -> dict:
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
        if cancel_url:  # ปุ่มย้อนกลับในหน้าจ่าย (ออเดอร์จากเว็บ)
            data["cancel_url"] = cancel_url
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
        intents.message_content = True  # ใช้อ่านข้อความทำ transcript + เลขที่ผู้เล่นพิมพ์ตอบบอท + ข้อความจาก relay
        intents.members = True  # หาทีมแอดมินเพื่อดึงเข้า ticket + หาคนที่ยังไม่ขอ White List
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
                     TicketView(whitelist_buttons=True), ClosedView(), SpinPanelView(), ShopPanelView(),
                     WalletCardView(), ShopOpenRouter()):
            self.add_view(view)
        self.add_dynamic_items(FaqButton, RemindButton, RedeemAdminButton, OrderNameButton)
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
        self._tasks = [asyncio.create_task(board_loop()), asyncio.create_task(remind_loop()),
                       asyncio.create_task(ckx_retry_loop())]
        await start_web()

    async def close(self):
        if self._poller:
            self._poller.cancel()
        for task in getattr(self, "_tasks", []):
            task.cancel()
        if getattr(self, "web_runner", None):
            await self.web_runner.cleanup()
        if self.session:
            await self.session.close()
        await super().close()

    async def on_message(self, message: discord.Message):
        if message.guild is None or message.guild.id != cfg.guild_id:
            return
        try:
            if cfg.ckx_channel and message.channel.id == cfg.ckx_channel:
                return await on_ckx_message(message)
            if message.author.bot or not isinstance(message.channel, discord.Thread):
                return
            ticket = db.by_channel(message.channel.id)
            if ticket is None or ticket["status"] != "open":
                return
            note_ticket_activity(message, ticket)
            if (ticket["mode"] == "bot" and FAQ is not None and message.author.id == ticket["owner_id"]):
                await faq_on_typed(message, db.by_id(ticket["id"]))
        except Exception:  # noqa: BLE001
            log.exception("on_message พัง")

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
        if not getattr(self, "_panels_refreshed", False):  # ป้ายร้านเก่า → ปุ่มตามโหมดปัจจุบัน (เว็บ/ดิส)
            self._panels_refreshed = True
            await update_panel("shop", ShopPanelView)
            spawn(cart_sweep(), "ตะกร้าค้าง")

    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent):
        ticket = db.by_channel(payload.thread_id)
        if ticket and ticket["status"] != "deleted":
            db.set_status(ticket["id"], "deleted")
            board_dirty()
        wallet = db.wallet_by_thread(payload.thread_id)
        if wallet:  # มีคนลบกระเป๋าทิ้ง → สร้างใหม่ตอนใช้ครั้งหน้า (ยอดคุกกี้ไม่หาย)
            db.wallet_update(wallet["discord_id"], thread_id=None, card_id=None)


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
    t = TICKET_TYPES[key]
    if t.questions:
        return await interaction.response.send_modal(TicketModal(t))
    # ไม่มีฟอร์ม (แจ้งบั๊ก / ติดต่อแอดมิน) → เปิดห้องเลย แล้วบอทถามต่อในห้อง
    await interaction.response.defer(ephemeral=True, thinking=True)
    async with user_lock(interaction.user.id):
        existing = db.open_tickets(interaction.user.id, key)
        if len(existing) >= cfg.max_open_per_type:
            return await interaction.followup.send(
                f"คุณมี ticket ประเภทนี้เปิดอยู่แล้ว: <#{existing[0]['channel_id']}>", ephemeral=True)
        thread = await create_ticket(interaction, t, {})
    if thread:
        await interaction.followup.send(f"เปิด ticket แล้ว: {thread.mention}", ephemeral=True)


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
        if ckx_link.valid_ingame(username):
            checks.append("✅ ชื่อในเกมใช้ส่งของได้")
        else:
            checks.append("⚠️ ชื่อในเกมมีตัวที่ส่งของไม่ได้ (\" | `) — ผู้เล่นแก้เองได้ทีหลังในกระเป๋าคุกกี้")
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


def staff_members(guild, limit: int = 25) -> list:
    """คนที่มี role ทีมแอดมิน (ไม่รวมบอท) — ต้องเปิด Server Members Intent"""
    out, seen = [], set()
    for rid in dict.fromkeys(cfg.staff_roles + cfg.admin_roles):
        role = guild.get_role(rid)
        if role is None or rid in (guild.id, cfg.survivor_role, cfg.member_role):  # กันตั้งผิดแล้วดึงผู้เล่นทั้งเซิฟ
            continue
        for m in getattr(role, "members", []):
            if not m.bot and m.id not in seen:
                seen.add(m.id)
                out.append(m)
    return out[:limit]


def staff_ping(guild, exclude: int = 0) -> str:
    """แท็กทีมแอดมินเป็นรายคน (แท็ก role จะไม่เด้งถ้า role ไม่ได้เปิดให้ทุกคนแท็ก)"""
    people = [m.mention for m in staff_members(guild) if m.id != exclude]
    if people:
        return " ".join(people)
    return " ".join(r.mention for r in (guild.get_role(i) for i in dict.fromkeys(cfg.staff_roles + cfg.admin_roles))
                    if r and r.id != guild.id)


async def add_staff_to_thread(guild, thread, exclude: int = 0) -> int:
    """ดึงทีมแอดมินเข้า thread — ticket จะขึ้นใน sidebar ของแอดมินทุกคน"""
    added = 0
    for m in staff_members(guild):
        if m.id == exclude:
            continue
        try:
            await thread.add_user(m)
            added += 1
        except discord.HTTPException as e:
            log.warning("ดึง %s เข้า thread ไม่ได้: %s", m, e)
    return added


async def create_ticket(interaction: discord.Interaction, t: TicketType, answers: dict):
    thread, err = await open_ticket_thread(interaction.guild, interaction.user, t, answers)
    if err:
        await interaction.followup.send(err, ephemeral=True)
    return thread


async def open_ticket_thread(guild, member, t: TicketType, answers: dict, via: str = ""):
    """สร้างห้อง ticket — คืน (thread, None) หรือ (None, ข้อความ error) · ไม่ต้องมี interaction (เว็บเรียกได้)"""
    parent = guild.get_channel(cfg.ticket_channel)
    if not isinstance(parent, discord.TextChannel):
        return None, "ตั้ง TICKET_CHANNEL_ID ไม่ถูก (ต้องเป็น ID ของห้องข้อความ) — แจ้งแอดมิน"
    number = db.next_number(t.key)
    try:
        thread = await parent.create_thread(
            name=trunc(f"{t.prefix}-{number:04d} {member.display_name}", 100),
            type=discord.ChannelType.private_thread, invitable=False, auto_archive_duration=10080,
            reason=f"ticket โดย {member}")
        await thread.add_user(member)
    except discord.Forbidden:
        return None, ("บอทสร้าง ticket ไม่ได้ — ขาดสิทธิ์ในห้อง ticket (Create Private Threads / Manage Threads) "
                      "แจ้งแอดมินให้รัน /check")
    except discord.HTTPException as e:
        return None, f"สร้าง ticket ไม่สำเร็จ: {e.text or e}"

    ticket_id = db.create_ticket(t.key, number, thread.id, member.id, answers)
    bot_first = bool(t.faq_start) and FAQ is not None
    if bot_first:  # คุยกับบอทก่อน — ยังไม่ดึง/แท็กแอดมิน จนกว่าผู้เล่นจะกดคุยกับแอดมิน
        db.ticket_update(ticket_id, mode="bot")
    else:
        await add_staff_to_thread(guild, thread, exclude=member.id)
    mentions = [member.mention]
    if cfg.ping_staff_on_new and not bot_first:
        mentions.append(staff_ping(guild, exclude=member.id))
    try:
        await thread.send(" ".join(m for m in mentions if m), embed=build_ticket_embed(t, number, member, answers),
                          view=TicketView(whitelist_buttons=(t.key == "wl")))
        if t.key == "donate":
            await thread.send(embed=catalog_embed(in_thread=True), view=CatalogView())
        if bot_first:
            start = FAQ.start if t.faq_start == "menu" else FAQ.contact_start
            await faq_show(thread, db.by_id(ticket_id), start, first=True)
    except discord.HTTPException as e:
        log.error("ส่งข้อความแรกใน ticket ไม่ได้: %s", e)
    await mod_log(guild, f"🎫 เปิด {thread.mention} ({t.label}) โดย {member.mention} · ticket #{ticket_id}"
                         + (" · 🤖 บอทถามตอบก่อน" if bot_first else "")
                         + (" · 🌐 จากหน้าเว็บ" if via == "web" else ""), COLOR_INFO)
    board_dirty()
    return thread, None


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
        if ticket["type"] in ("bug", "help"):
            return await ask_close(interaction, ticket)
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
        if not ticket:
            return
        tid = ticket["id"]

        async def go(i: discord.Interaction):
            await approve_whitelist(i, tid)

        await reply(interaction, f"อนุมัติ <@{ticket['owner_id']}>? บอทจะให้ role + แปะวิธีเข้าเซิฟในห้องนี้",
                    view=ConfirmView(go, "อนุมัติเลย", discord.ButtonStyle.success))

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
        board_dirty()
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
    board_dirty()
    await mod_log(guild, f"🔒 ปิด {thread.mention} โดย {by.mention}" + (f" — {reason}" if reason else ""))


async def delete_ticket(guild, thread, ticket, by, transcript: bool = True, reason: str = ""):
    if ticket is None:
        return
    if transcript and not ticket["transcript_saved"]:
        await save_transcript(guild, thread, ticket, by)
    db.set_status(ticket["id"], "deleted")
    db.conn.execute("UPDATE tickets SET closed_at=? WHERE id=? AND closed_at IS NULL",
                    (datetime.now(timezone.utc).isoformat(), ticket["id"]))
    db.conn.commit()
    board_dirty()
    await mod_log(guild, f"⛔ ลบ thread {thread.name} โดย {by.mention}" + (f" — {reason}" if reason else ""))
    try:
        await thread.delete(reason=f"ลบ ticket โดย {by}")
    except discord.HTTPException as e:
        log.warning("ลบ thread ไม่ได้: %s", e)


# ---------------------------------------------------------------------
# อนุมัติ / ไม่ผ่าน White List
# ---------------------------------------------------------------------

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


DEFAULT_JOININFO = (
    "1. โหลด **Radmin VPN** ที่ https://www.radmin-vpn.com/ แล้วติดตั้ง\n"
    "2. เปิด Radmin → เมนู **เครือข่าย** → **เข้าร่วมเครือข่าย** → ใส่ชื่อเครือข่ายกับรหัสจาก {server_info}\n"
    "3. โหลดม็อดก่อน: เปิด {collection} แล้วกด **Subscribe to all** รอ Steam โหลดเสร็จ\n"
    "4. เปิดเกม → **Join** → ใส่ IP และ Port จาก {server_info}\n"
    "5. ตอนเข้าเซิฟครั้งแรก ตั้ง Username / Password เองได้เลย (ใช้ชื่อเดียวกับที่กรอกตอนขอ White List)")


def fill_placeholders(text: str) -> str:
    return faq_engine.fill(text or "", {
        "server_info": f"<#{cfg.connect_info_channel}>" if cfg.connect_info_channel else "ห้อง server-info",
        "collection": cfg.mod_collection_url or "คอลเลกชันม็อดของเซิฟ",
        "join": f"<#{cfg.join_channel}>" if cfg.join_channel else "ห้องวิธีเข้าเซิฟ",
        "redeem": f"<#{cfg.redeem_channel}>" if cfg.redeem_channel else "ห้องแลกของ",
        "spin": f"<#{cfg.spin_channel}>" if cfg.spin_channel else "ห้องหมุนวงล้อ",
    })


def joininfo_embed() -> discord.Embed:
    text = fill_placeholders(db.setting("joininfo") or DEFAULT_JOININFO)
    embed = discord.Embed(title="🎮 วิธีเข้าเซิฟ", description=trunc(text, 4000), color=COLOR_INFO)
    if cfg.game_version:
        embed.set_footer(text=f"เวอร์ชันเกม {cfg.game_version}")
    return embed


def connect_view() -> Optional[ui.View]:
    url = channel_link(cfg.connect_info_channel)
    if not url:
        return None
    view = ui.View(timeout=None)
    view.add_item(ui.Button(label="ไปห้อง Server info", emoji="📌", url=url))
    return view


async def approve_whitelist(interaction: discord.Interaction, ticket_id: int):
    """อนุมัติ: ให้ role คุกกี้ (ROLE_SURVIVOR) + แปะวิธีเข้าเซิฟ + ปุ่มไปห้อง server-info
    (ไม่สร้าง username/รหัสผ่านแล้ว — ผู้เล่นตั้งเองตอนเข้าเซิฟครั้งแรก)"""
    guild = interaction.guild
    ticket = db.by_id(ticket_id)
    send = interaction.followup.send
    if ticket is None or ticket["decision"]:
        return await send("ticket นี้ถูกตัดสินไปแล้ว", ephemeral=True)
    owner = await fetch_member(guild, ticket["owner_id"])
    if owner is None:
        return await send("ผู้เล่นออกจากเซิฟ Discord ไปแล้ว — กดไม่ผ่านแล้วปิด ticket ได้เลย", ephemeral=True)
    username = (answers_of(ticket).get("username") or "").strip()
    notes = []
    survivor = guild.get_role(cfg.survivor_role)
    if survivor:
        try:
            await owner.add_roles(survivor, reason=f"อนุมัติ whitelist โดย {interaction.user}")
            notes.append(f"ให้ role {survivor.mention} แล้ว")
        except discord.Forbidden:
            notes.append(f"❌ ให้ role {survivor.mention} ไม่ได้ (role บอทต้องอยู่เหนือ role นี้) — ให้เอง")
    if cfg.set_nickname and username and owner.display_name != username:
        try:
            await owner.edit(nick=trunc(username, 32), reason="ตั้งชื่อให้ตรงกับในเกม")
            notes.append(f"เปลี่ยน nickname เป็น `{username}` แล้ว")
        except discord.HTTPException:
            notes.append("⚠️ เปลี่ยน nickname ไม่ได้ (เจ้าของเซิฟหรือ role สูงกว่าบอท) — ข้ามไป")

    steam_id = answers_of(ticket).get("steam", "")
    if not re.fullmatch(r"\d{17}", steam_id):
        link = db.steam_get(owner.id)
        steam_id = link["steam_id"] if link else None
    if username:
        existing = db.wl_get(username)
        if existing and existing["active"] and existing["discord_id"] != owner.id:
            notes.append(f"⚠️ ชื่อ `{trunc(username, 40)}` เป็นของ <@{existing['discord_id']}> อยู่แล้ว — ไม่บันทึกชื่อนี้ "
                         "(ให้ผู้เล่นใช้ชื่ออื่นในเกม แล้วแก้ชื่อรับของในกระเป๋า)")
        else:
            db.wl_add(username, owner.id, interaction.user.id, ticket_id, steam_id)
        wallet = db.wallet_ensure(owner.id)
        if not wallet["ingame"] and ckx_link.valid_ingame(username):
            db.wallet_update(owner.id, ingame=username)  # ใช้เป็นชื่อรับของในเกม (แก้เองได้ในกระเป๋า)
    db.set_decision(ticket_id, "approved")

    done = discord.Embed(title="อนุมัติแล้ว 🎉", color=COLOR_OK,
                         description=f"ยินดีต้อนรับ {owner.mention}! ได้ role "
                                     f"{survivor.mention if survivor else 'คุกกี้'} แล้ว ทำตามขั้นตอนข้างล่างเข้าเซิฟได้เลย")
    done.set_footer(text=f"อนุมัติโดย {interaction.user}")
    view = connect_view()
    channel = interaction.channel
    kwargs = {"view": view} if view else {}
    await channel.send(owner.mention, embeds=[done, joininfo_embed()],
                       allowed_mentions=discord.AllowedMentions(users=[owner]), **kwargs)
    try:
        await owner.send(embeds=[discord.Embed(title=f"ผ่าน White List แล้ว — {guild.name}", color=COLOR_OK,
                                               description="ยินดีต้อนรับ! ทำตามขั้นตอนนี้เข้าเซิฟได้เลย 🍪"),
                                 joininfo_embed()], **kwargs)
        notes.append("ส่งวิธีเข้าเซิฟทาง DM แล้ว")
    except discord.HTTPException:
        notes.append("ผู้เล่นปิด DM — ดูวิธีเข้าเซิฟในห้อง ticket ได้")

    steam_note = f" · Steam `{steam_id}`" if steam_id else ""
    await log_to(guild, cfg.whitelist_log, discord.Embed(
        color=COLOR_OK, timestamp=datetime.now(timezone.utc),
        description=f"**[APPROVE]** `{trunc(username, 40) or '-'}` · {owner.mention}{steam_note} · โดย {interaction.user.mention}"))
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

    @ui.button(label="เติมคุกกี้", emoji="🍪", style=discord.ButtonStyle.secondary, custom_id="cc:donate:topup")
    async def topup(self, interaction: discord.Interaction, button: ui.Button):
        ticket = db.by_channel(interaction.channel_id)
        if ticket is None or ticket["type"] != "donate":
            return await reply(interaction, "ใช้ปุ่มนี้ในห้อง Donate เท่านั้น")
        if interaction.user.id != ticket["owner_id"] and not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับเจ้าของห้อง")
        if ticket["status"] != "open":
            return await reply(interaction, "ห้องนี้ปิดแล้ว — เปิดห้อง Donate ใหม่ได้เลย")
        rate = int(db.setting("cookie_rate", "0") or 0)
        if rate <= 0:
            return await reply(interaction, "ยังไม่เปิดเติมคุกกี้ตามยอด — เลือกแพ็กคุกกี้ในรายการแทนได้")
        order = db.order_open_in_thread(interaction.channel_id)
        if order and order["status"] in ("review", "pending", "expired"):
            link = f"https://discord.com/channels/{cfg.guild_id}/{order['thread_id']}/{order['message_id']}"
            return await reply(interaction, f"มีรายการ #{order['id']:04d} ค้างอยู่ — จัดการที่การ์ดนี้ก่อน: {link}")
        order_id = order["id"] if order else db.order_create(ticket["id"], interaction.channel_id, ticket["owner_id"])
        await interaction.response.send_modal(TopupModal(order_id, rate))


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
    if order_ckx_lines(lines):
        name = order_ingame(order)
        embed.add_field(name="🎮 รับของในเกมชื่อ", value=discord.utils.escape_markdown(name) if name else
                        "ยังไม่ได้ใส่ — กด 🎮 ชื่อในเกม", inline=False)
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


def paid_embed(order, lines: list) -> discord.Embed:
    embed = discord.Embed(title=f"💝 ได้รับยอด Donate แล้ว — #{order['id']:04d}",
                          color=COLOR_DONATE,
                          description=f"ขอบคุณ <@{order['owner_id']}> ที่ช่วยสนับสนุนเซิฟ 🍪\n\n{cart_text(lines)}")
    embed.add_field(name="ยอดรวม", value=f"**{fmt_baht(order['total'])}**")
    embed.add_field(name="ชำระเมื่อ", value=fmt_time(order["paid_at"]))
    embed.add_field(name="สถานะ", value=trunc(delivery_text(order, lines), 1024), inline=False)
    if order["status"] == "delivered":
        embed.color = COLOR_OK
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
        if order_ckx_lines(lines_of(order)) and not ckx_link.valid_ingame(order_ingame(order)):
            return await interaction.response.send_modal(IngameNameModal(
                order_ingame(order), after=_order_name_then_bill(order["id"]), target=order["owner_id"]))
        if order_ckx_lines(lines_of(order)) and not order["ingame"]:
            db.order_update(order["id"], ingame=order_ingame(order))
        await interaction.response.defer()
        await create_bill(interaction, order["id"])

    @ui.button(label="ชื่อในเกม", emoji="🎮", style=discord.ButtonStyle.secondary, custom_id="cc:order:name")
    async def name(self, interaction: discord.Interaction, button: ui.Button):
        order = await order_from_message(interaction)
        if order is None:
            return
        oid = order["id"]

        async def after(i: discord.Interaction, name: str):
            db.order_update(oid, ingame=name)
            o = db.order_get(oid)
            if o["status"] == "review":
                await i.response.edit_message(embed=review_embed(o, lines_of(o)), view=ReviewView())
            else:
                await i.response.send_message("บันทึกแล้ว ✅", ephemeral=True)

        await interaction.response.send_modal(IngameNameModal(order_ingame(order), after=after,
                                                              target=order["owner_id"]))

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


def _order_name_then_bill(order_id: int):
    async def after(i: discord.Interaction, name: str):
        db.order_update(order_id, ingame=name)
        await i.response.defer()
        await create_bill(i, order_id)
    return after


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
    order = db.order_get(order_id)
    if order is None:
        return await interaction.followup.send("ไม่พบรายการนี้แล้ว", ephemeral=True)
    # สร้างบิลทีละใบต่อคน (กดในดิสพร้อมกับสั่งบนเว็บ → ไม่ได้บิลค้างสองใบ) · ลำดับล็อก: user → order เหมือนฝั่งเว็บ
    async with user_lock(order["owner_id"]), order_lock(order_id):
        order, err = await _bill_locked(order_id, interaction.guild)
        if err:
            return await interaction.followup.send(err, ephemeral=True)
        await interaction.message.edit(embed=payment_embed(order, lines_of(order)), view=PaymentView(order["stripe_url"]))


async def _bill_locked(order_id: int, guild, via: str = "discord"):
    """สร้างบิล Stripe ให้ออเดอร์ review/expired — คืน (order, None) หรือ (None, error)
    ต้องถือ user_lock(เจ้าของ) แล้ว order_lock อยู่ · via='web' → จ่ายเสร็จ/กดย้อนกลับ กลับมาหน้า Donate บนเว็บ"""
    order = db.order_get(order_id)
    if order is None or order["status"] not in ("review", "expired"):
        return None, "รายการนี้ไม่อยู่ในสถานะที่ยืนยันได้แล้ว"
    other = [o for o in db.orders_in_thread(order["thread_id"], ("pending",))
             if o["owner_id"] == order["owner_id"] and o["id"] != order_id]
    if other:  # ห้องเดียวมีบิลรอจ่ายได้ใบเดียว (กันจ่ายซ้ำสองใบ)
        return None, f"มีบิล #{other[0]['id']:04d} รอจ่ายอยู่ — จ่ายหรือยกเลิกบิลนั้นก่อน"
    lines = lines_of(order)
    # ราคาอิงตอนใส่ตะกร้า ถ้าแอดมินปิดรายการระหว่างนั้น ให้แจ้งก่อน
    gone = [line["code"] for line in lines if line["code"] != TOPUP_CODE
            and not (db.item_get(line["code"]) or {"active": 0})["active"]]
    if gone:
        if via == "web":
            how = "ยกเลิกรายการนี้แล้วเลือกใหม่"
        else:
            how = "กด 📝 แก้ไข เพื่อเอาออก" if order["status"] == "review" else "กดยกเลิกแล้วทำรายการใหม่"
        return None, f"รายการ {', '.join(gone)} ถูกปิดไปแล้ว — {how}"
    if stripe is None:
        return None, "ระบบ Donate ปิดอยู่ (ยังไม่ได้ตั้ง STRIPE_SECRET_KEY)"
    attempt = order["attempt"] + 1
    # จดรอบไว้ก่อนเรียก Stripe: ถ้าหมดเวลาแต่ Stripe สร้างไปแล้ว รอบหน้าใช้ key ใหม่ (ไม่ชน idempotency)
    # บิลที่หลุดไปไม่เคยโชว์ลิงก์ให้ใคร จึงจ่ายไม่ได้ และหมดอายุไปเอง
    db.order_update(order_id, attempt=attempt)
    expires_at = int(time.time()) + cfg.stripe_session_minutes * 60
    if via == "web" and cfg.public_url:
        back = f"{cfg.public_url}/donate?order={order['id']}"
        urls = {"success_url": f"{cfg.public_url}/donate?paid={order['id']}", "cancel_url": back}
    else:
        urls = {"success_url": f"https://discord.com/channels/{cfg.guild_id}/{order['thread_id']}"}
    try:
        session = await stripe.create_checkout(
            order_id=order["id"], owner_id=order["owner_id"], lines=lines, currency=cfg.stripe_currency,
            expires_at=expires_at, payment_methods=cfg.stripe_payment_methods,
            idempotency_key=f"cookiecheetah-order-{order['id']}-{attempt}", **urls)
    except StripeError as e:
        log.error("สร้างบิล Stripe ไม่ได้ (order %s): %s", order_id, e)
        await mod_log(guild, f"❌ สร้างบิล Stripe ไม่ได้ (Donate #{order_id:04d}): {e}", COLOR_BAD)
        return None, "❌ สร้างบิลไม่สำเร็จ ลองกดยืนยันอีกครั้ง (ถ้ายังไม่ได้ แจ้งแอดมิน)"
    db.order_update(order_id, status="pending", attempt=attempt, stripe_session=session["id"],
                    stripe_url=session["url"], stripe_expires=session.get("expires_at") or expires_at,
                    total=cart_total(lines))
    order = db.order_get(order_id)
    await mod_log(guild, f"💳 บิล Donate #{order_id:04d} {fmt_baht(order['total'])} "
                         f"โดย <@{order['owner_id']}> · <#{order['thread_id']}>" + (" · 🌐 เว็บ" if via == "web" else ""),
                  COLOR_WAIT)
    return order, None


async def _cancel_locked(order_id: int) -> tuple:
    """ยกเลิกออเดอร์ (ต้องถือ order_lock) — คืน ('cancelled'|'paid'|'closed'|'error', ข้อความ)
    บิลที่ยังเปิดอยู่ที่ Stripe จะถูกปิดก่อน · ถ้าจ่ายไปแล้วจะไม่ยกเลิก"""
    order = db.order_get(order_id)
    if order is None or order["status"] in ("paid", "delivered", "cancelled"):
        return "closed", "ยกเลิกรายการนี้ไม่ได้แล้ว"
    if order["status"] == "pending" and order["stripe_session"]:
        if stripe is None:  # ปิดบิลที่ Stripe ไม่ได้ → ห้ามยกเลิก (บิลยังจ่ายได้อยู่)
            return "error", "ยกเลิกบิลไม่ได้ตอนนี้ (ยังไม่ได้ตั้ง STRIPE_SECRET_KEY)"
        try:
            session = await stripe.get_session(order["stripe_session"])
            if session.get("payment_status") == "paid":
                return "paid", "บิลนี้จ่ายแล้ว ยกเลิกไม่ได้"
            if session.get("status") == "open":
                await stripe.expire_session(order["stripe_session"])
            elif session.get("status") != "expired":  # complete แต่ยังไม่ paid = เงินกำลังยืนยัน
                return "error", "บิลนี้กำลังรอยืนยันการจ่ายเงิน — ยกเลิกไม่ได้ตอนนี้ ลองกดเช็คสถานะอีกครั้ง"
        except StripeError as e:
            return "error", f"ยกเลิกบิลที่ Stripe ไม่ได้: {e}"
    db.order_update(order_id, status="cancelled")
    return "cancelled", ""


async def cancel_order(interaction: discord.Interaction, order):
    await interaction.response.defer()  # คุยกับ Stripe อาจเกิน 3 วินาที
    async with order_lock(order["id"]):
        result, text = await _cancel_locked(order["id"])
        if result == "cancelled":
            order = db.order_get(order["id"])
            await interaction.edit_original_response(
                embed=closed_order_embed(order, lines_of(order), "ยกเลิกแล้ว"), view=None)
    if result in ("closed", "error"):
        return await interaction.followup.send(text, ephemeral=True)
    if result == "paid":
        await interaction.followup.send("บิลนี้จ่ายแล้ว ยกเลิกไม่ได้ — อัปเดตการ์ดให้แล้ว", ephemeral=True)
        await sync_payment(order["id"])


async def post_order_card(order_id: int, note: str = "", title: str = ""):
    """การ์ดออเดอร์ในห้อง Donate ตามสถานะตอนนี้ (ใช้ตอนสั่ง/จ่าย/ยกเลิกจากเว็บ)
    มีการ์ดเดิม → แก้การ์ดเดิม · ไม่มี → โพสต์ใหม่พร้อม note · จ่ายแล้วไม่แตะ (on_paid ดูแลเอง)"""
    guild = bot.get_guild(cfg.guild_id)
    if guild is None:
        return
    async with order_lock(order_id):
        order = db.order_get(order_id)
        if order is None:
            return
        lines = lines_of(order)
        if order["status"] == "pending":
            embed, view = payment_embed(order, lines), PaymentView(order["stripe_url"])
        elif order["status"] == "review":
            embed, view = review_embed(order, lines), ReviewView()
        elif order["status"] == "expired":
            embed = closed_order_embed(order, lines, "บิลหมดอายุ", COLOR_MUTED).set_footer(
                text="กด 🔁 สร้างบิลใหม่ ถ้ายังต้องการ Donate รายการนี้")
            view = ExpiredView()
        elif order["status"] == "cancelled":
            embed, view = closed_order_embed(order, lines, title or "ยกเลิกแล้ว"), None
        else:
            return
        thread = await get_thread(guild, order["thread_id"], unarchive=True)
        if thread is None:
            return
        if order["message_id"]:
            try:
                await thread.get_partial_message(order["message_id"]).edit(embed=embed, view=view)
                return
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                log.warning("แก้การ์ด Donate #%s ไม่ได้: %s", order_id, e)
                return
        if order["status"] == "cancelled":
            return
        try:
            msg = await thread.send(note or None, embed=embed, view=view,
                                    allowed_mentions=discord.AllowedMentions(users=True))
            db.order_update(order_id, message_id=msg.id)
        except discord.HTTPException as e:
            log.warning("โพสต์การ์ด Donate #%s ไม่ได้: %s", order_id, e)


async def sync_payment(order_id: int) -> str:
    """เช็คบิลกับ Stripe — คืน 'paid' / 'pending' / 'expired' / ข้อความ error"""
    async with order_lock(order_id):
        result = await _sync_payment_locked(order_id)
    if result == "paid_now":  # ส่งของ/เติมคุกกี้นอก lock (auto_fulfil ล็อกออเดอร์เดียวกันเอง)
        try:
            await auto_fulfil(bot.get_guild(cfg.guild_id), order_id)
        except Exception:  # noqa: BLE001
            log.exception("ส่งของอัตโนมัติ Donate #%s พัง", order_id)
        return "paid"
    return result


async def _sync_payment_locked(order_id: int) -> str:
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
        return "paid_now"
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
        manual = bool(order_manual_lines(lines))
        staff = staff_ping(guild, exclude=order["owner_id"]) if cfg.ping_staff_on_new and manual else ""
        try:
            msg = await thread.send(f"<@{order['owner_id']}> {staff}".strip(), embed=paid_embed(order, lines),
                                    view=DeliverView() if manual else None)
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
                        embed=paid_embed(order, lines), view=None)
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
        board_dirty()
        return "ok"


async def payment_poller():
    """เช็คบิลที่รอจ่ายกับ Stripe เป็นระยะ (ไม่ต้องตั้ง webhook / โดเมน)"""
    await bot.wait_until_ready()
    try:  # ออเดอร์ที่จ่ายแล้วแต่ยังส่งไม่ครบ (เช่น บอทรีสตาร์ทกลางทาง) → ทำต่อ
        for order in db.orders_with_status("paid", limit=200):
            await auto_fulfil(bot.get_guild(cfg.guild_id), order["id"])
    except Exception:  # noqa: BLE001
        log.exception("ทำออเดอร์ที่ค้างตอนเปิดบอทไม่สำเร็จ")
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
# บอทถามตอบ (faq.json) — ticket แจ้งบั๊ก / ติดต่อแอดมิน
# =====================================================================

FAQ: Optional[faq_engine.FaqTree] = None
FAQ_PATH = BASE_DIR / "faq.json"
FAQ_ASSETS = ASSETS_DIR / "faq"
FAQ_ERROR = ""
_faq_hint_at: dict = {}


def load_faq():
    global FAQ, FAQ_ERROR
    try:
        FAQ = faq_engine.FaqTree.load(FAQ_PATH)
        FAQ_ERROR = ""
        log.info("โหลด faq.json แล้ว %d ข้อ", len(FAQ.nodes))
    except faq_engine.FaqError as e:
        FAQ, FAQ_ERROR = None, str(e)
        log.error("%s — ticket แจ้งบั๊ก/ติดต่อแอดมิน จะส่งตรงถึงแอดมินแทน", e)


def faq_start_of(ticket) -> str:
    t = TICKET_TYPES.get(ticket["type"])
    return FAQ.contact_start if t and t.faq_start == "contact_start" else FAQ.start


def faq_path_of(ticket) -> list:
    try:
        return json.loads(ticket["faq_path"] or "[]")
    except (TypeError, ValueError):
        return []


class FaqButton(ui.DynamicItem[ui.Button], template=r"cc:faq:(?P<tid>\d+):(?P<go>@?[a-z0-9_]{1,40})"):
    """ปุ่มในคำตอบของบอท — กดได้แม้บอทรีสตาร์ท (ข้อมูลอยู่ใน custom_id)"""

    def __init__(self, tid: int, go: str, label: str = "ต่อ", style=discord.ButtonStyle.primary, emoji=None):
        super().__init__(ui.Button(label=trunc(label, 80), style=style, emoji=emoji,
                                   custom_id=f"cc:faq:{tid}:{go}"))
        self.tid, self.go = tid, go

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["tid"]), match["go"])

    async def callback(self, interaction: discord.Interaction):
        ticket = db.by_id(self.tid)
        if ticket is None or ticket["channel_id"] != interaction.channel_id:
            return await reply(interaction, "ปุ่มนี้ใช้ไม่ได้แล้ว")
        if interaction.user.id != ticket["owner_id"] and not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับเจ้าของห้อง")
        if ticket["status"] != "open":
            return await reply(interaction, "ห้องนี้ปิดแล้ว")
        if ticket["mode"] == "closing":
            return await reply(interaction, "ห้องนี้กำลังปิด — มีปัญหาอีกเปิด ticket ใหม่ได้เลยนะคะ")
        if FAQ is None and self.go not in ("@close", "@admin"):
            return await reply(interaction, "ระบบถามตอบปิดอยู่ — กดคุยกับแอดมินได้เลย")
        if self.go == "@close":
            return await ask_close(interaction, ticket)
        await interaction.response.defer()
        await faq_go(interaction.channel, ticket, self.go, interaction.user)


def faq_message(ticket, key: str):
    """(embeds, files, view) ของข้อ key"""
    node = FAQ.node(key)
    text = fill_placeholders(node.get("text", ""))
    if node.get("ask"):
        text += f"\n\n**{fill_placeholders(node['ask'])}**"
    numbered = "\n".join(f"`{o['n']}` {o['label']}" for o in node.get("options", []))
    if numbered:
        text += "\n" + numbered
    embed = discord.Embed(title=node.get("title") or None, description=trunc(text, 4000), color=COLOR_INFO)
    embed.set_footer(text="กดปุ่ม หรือพิมพ์เลขข้อในแชทนี้ได้เลย")
    embeds, files = [embed], []
    images = [n for n in FAQ.images(key) if (FAQ_ASSETS / n).is_file()]
    for name in FAQ.images(key):
        if name not in images:
            log.warning("faq.json: ไม่เจอรูป assets/faq/%s", name)
    for i, name in enumerate(images):
        path = FAQ_ASSETS / name
        fname = f"faq{i}{path.suffix.lower()}"
        files.append(discord.File(path, filename=fname))
        target = embed if i == 0 else discord.Embed(color=COLOR_INFO)
        if len(images) > 1:
            target.url = "https://discord.com/channels/@me"  # embed ที่ url เดียวกันจะรวมรูปเป็นแกลเลอรี
        target.set_image(url=f"attachment://{fname}")
        if target is not embed:
            embeds.append(target)
    view = ui.View(timeout=None)
    has_admin = False
    for o in node.get("options", []):
        go = o["go"]
        style = (discord.ButtonStyle.success if go == "@solved" else
                 discord.ButtonStyle.secondary if go == "@admin" else discord.ButtonStyle.primary)
        has_admin |= go == "@admin"
        view.add_item(FaqButton(ticket["id"], go, f"{o['n']}. {o['label']}", style))
    if key != faq_start_of(ticket):
        view.add_item(FaqButton(ticket["id"], "@menu", "เมนูแรก", discord.ButtonStyle.secondary, "🏠"))
    if not has_admin:
        view.add_item(FaqButton(ticket["id"], "@admin", "คุยกับแอดมิน", discord.ButtonStyle.secondary, "🙋"))
    view.add_item(FaqButton(ticket["id"], "@close", "ปิดห้อง", discord.ButtonStyle.secondary, "🔒"))
    return embeds, files, view


async def faq_show(thread, ticket, key: str, first: bool = False):
    embeds, files, view = faq_message(ticket, key)
    await thread.send(embeds=embeds, files=files, view=view)
    path = ([] if first else faq_path_of(ticket)) + [key]
    db.ticket_update(ticket["id"], faq_node=key, faq_path=json.dumps(path[-30:]))


async def faq_go(thread, ticket, go: str, actor):
    if go == "@menu":
        return await faq_show(thread, ticket, faq_start_of(ticket))
    if go == "@admin":
        return await faq_to_admin(thread, ticket, actor)
    if go == "@solved":
        return await faq_solved(thread, ticket, actor)
    if FAQ.node(go) is None:
        return await thread.send("ข้อนี้ไม่มีแล้ว — กลับเมนูแรกนะคะ")
    await faq_show(thread, ticket, go)


def faq_breadcrumb(ticket) -> str:
    path = [FAQ.title_of(k) for k in faq_path_of(ticket)[1:]] if FAQ else []
    return " → ".join(path) if path else "ยังไม่ได้เลือกหัวข้อ"


async def faq_to_admin(thread, ticket, actor):
    ticket = db.by_id(ticket["id"])
    if ticket["mode"] == "admin":
        return await thread.send("แจ้งแอดมินไว้แล้วนะคะ รอสักครู่ ระหว่างนี้พิมพ์เล่าเพิ่มหรือแนบรูปได้เลย 🍪")
    db.ticket_update(ticket["id"], mode="admin")
    guild = thread.guild
    await add_staff_to_thread(guild, thread, exclude=ticket["owner_id"])
    t = TICKET_TYPES.get(ticket["type"])
    ask = ("เล่าอาการที่เจอ + แนบ **รูปหน้าจอ** หรือไฟล์ `console.txt` ไว้ได้เลย "
           "(กด Windows+R พิมพ์ `%UserProfile%\\Zomboid` → ลากไฟล์ console.txt มาวาง)"
           if ticket["type"] == "bug" else "พิมพ์เรื่องที่อยากติดต่อไว้ได้เลย แนบรูปได้")
    embed = discord.Embed(title="🙋 เรียกแอดมินแล้วค่ะ", color=COLOR_WAIT,
                          description=f"แอดมินจะมาตอบในห้องนี้ภายใน 24 ชม.\n\n{ask}")
    embed.add_field(name="ที่ลองกับบอทแล้ว (สำหรับแอดมิน)", value=trunc(faq_breadcrumb(ticket), 1024), inline=False)
    ping = staff_ping(guild, exclude=ticket["owner_id"]) if cfg.ping_staff_on_new else ""
    await thread.send(f"<@{ticket['owner_id']}> {ping}".strip(), embed=embed,
                      allowed_mentions=discord.AllowedMentions(users=True, roles=True))
    await mod_log(guild, f"🙋 {thread.mention} ({t.label if t else ticket['type']}) ขอคุยกับแอดมิน · "
                         f"{trunc(faq_breadcrumb(ticket), 300)}", COLOR_WAIT)
    board_dirty()


async def faq_solved(thread, ticket, actor):
    ticket = db.by_id(ticket["id"])
    if ticket["mode"] == "admin":
        return await thread.send("ดีใจด้วยค่ะ 🎉 ปิดห้องได้เลย", view=CloseChoiceView(ticket["id"]))
    if ticket["mode"] == "closing":
        return
    db.ticket_update(ticket["id"], mode="closing")  # ปุ่ม/เลขอื่นๆ ไม่ทำงานระหว่างรอลบ
    await thread.send(f"ดีใจด้วยค่ะ 🎉 ห้องนี้จะถูกลบใน {FAQ_DELETE_SECONDS} วินาที ถ้าเจอปัญหาอีกเปิด ticket ใหม่ได้เลยนะคะ 🍪")
    await asyncio.sleep(FAQ_DELETE_SECONDS)
    ticket = db.by_id(ticket["id"])
    if ticket is None or ticket["status"] != "open" or ticket["mode"] != "closing":
        return  # แอดมินเข้ามาคุยระหว่างนั้น → ไม่ลบ
    await mod_log(thread.guild, f"🤖 {thread.name} แก้ได้กับบอท: {trunc(faq_breadcrumb(ticket), 300)}", COLOR_OK)
    await delete_ticket(thread.guild, thread, ticket, actor, transcript=False, reason="แก้ได้กับบอท")


FAQ_DELETE_SECONDS = 10


class CloseChoiceView(ui.View):
    """โหมดคุยกับแอดมิน: เลือกเองว่าจะเก็บห้องไว้ หรือปิดแล้วลบ"""

    def __init__(self, ticket_id: int):
        super().__init__(timeout=600)
        self.ticket_id = ticket_id

    async def _check(self, interaction):
        ticket = db.by_id(self.ticket_id)
        if ticket is None or ticket["status"] != "open":
            await reply(interaction, "ห้องนี้ปิดไปแล้ว")
            return None
        is_owner = interaction.user.id == ticket["owner_id"]
        if not (is_staff(interaction.user) or (is_owner and cfg.allow_owner_close)):
            await reply(interaction, "ปิดห้องได้เฉพาะเจ้าของห้องหรือทีมแอดมิน")
            return None
        return ticket

    @ui.button(label="ปิด (เก็บไว้ดูย้อนหลัง)", emoji="🔒", style=discord.ButtonStyle.secondary)
    async def keep(self, interaction: discord.Interaction, button: ui.Button):
        ticket = await self._check(interaction)
        if ticket:
            await interaction.response.defer()
            await close_ticket(interaction.guild, interaction.channel, ticket, interaction.user)

    @ui.button(label="ปิดและลบห้อง", emoji="⛔", style=discord.ButtonStyle.danger)
    async def drop(self, interaction: discord.Interaction, button: ui.Button):
        ticket = await self._check(interaction)
        if ticket:
            await interaction.response.defer()
            await delete_ticket(interaction.guild, interaction.channel, ticket, interaction.user)

    async def on_error(self, interaction, error, item):
        await _report_error(interaction, error, "ปุ่มปิดห้อง")


async def ask_close(interaction: discord.Interaction, ticket):
    """ปุ่มปิดของ ticket แจ้งบั๊ก/ติดต่อแอดมิน: คุยกับบอทอยู่ = ลบเลย · คุยกับแอดมินแล้ว = ให้เลือก"""
    is_owner = interaction.user.id == ticket["owner_id"]
    if not (is_staff(interaction.user) or (is_owner and cfg.allow_owner_close)):
        return await reply(interaction, "ปิดห้องได้เฉพาะเจ้าของห้องหรือทีมแอดมิน")
    if ticket["mode"] == "bot":
        tid = ticket["id"]

        async def go(i: discord.Interaction):
            await delete_ticket(i.guild, i.channel, db.by_id(tid), i.user, transcript=False, reason="ปิดเองตอนคุยกับบอท")

        return await reply(interaction, "ปิดและลบห้องนี้เลยไหมคะ?", view=ConfirmView(go, "ปิดและลบ"))
    await reply(interaction, "จะเก็บห้องไว้ หรือปิดแล้วลบเลย?", view=CloseChoiceView(ticket["id"]))


async def faq_on_typed(message: discord.Message, ticket):
    """ผู้เล่นพิมพ์เลขตอบบอท"""
    number = faq_engine.typed_number(message.content)
    if number is None:
        last = _faq_hint_at.get(ticket["id"], 0)
        if time.time() - last > 90:
            _faq_hint_at[ticket["id"]] = time.time()
            await message.channel.send("พิมพ์**เลขข้อ** หรือกดปุ่มข้างบนได้เลยค่ะ ถ้าอยากคุยกับแอดมินเลย พิมพ์ `0` 🍪")
        return
    option = FAQ.option_by_number(ticket["faq_node"] or faq_start_of(ticket), number)
    if option is None:
        if number == 0:
            return await faq_to_admin(message.channel, ticket, message.author)
        return await message.channel.send(f"ไม่มีข้อ {number} ในหน้านี้ค่ะ ลองดูเลขในปุ่มอีกทีนะคะ")
    await faq_go(message.channel, ticket, option["go"], message.author)


# =====================================================================
# ห้องสรุป ticket ของแอดมิน (แก้ข้อความเดิมเรื่อยๆ ไม่ส่งใหม่)
# =====================================================================

BOARD_ORDER = ("wl", "donate", "bug", "report", "help")
_board = {"dirty": True, "hash": {}, "last": 0.0}


def board_dirty():
    _board["dirty"] = True


def _ts(iso) -> Optional[int]:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp())
    except ValueError:
        return None


def ticket_state(ticket, order=None):
    """(ลำดับความด่วน, อีโมจิ, ข้อความ)"""
    if order is not None and order["status"] == "paid":  # จ่ายแล้วต้องโชว์เสมอ แม้ห้องปิดไปแล้ว
        job = db.job_get(order["job_id"]) if order["job_id"] else None
        if job is not None and job["status"] in JOB_IN_FLIGHT and not order_manual_lines(lines_of(order)):
            return 4, "📦", "ส่งเข้าเกมแล้ว รอผู้เล่นกดรับ"
        return 0, "💝", "จ่ายแล้ว รอส่งของ"
    if ticket["status"] == "deleted":
        return 9, "⚫", "ลบแล้ว"
    if ticket["status"] == "closed":
        decision = {"approved": "อนุมัติแล้ว", "rejected": "ไม่ผ่าน"}.get(ticket["decision"] or "", "")
        return 9, "⚫", "ปิดแล้ว" + (f" · {decision}" if decision else "")
    if ticket["mode"] in ("bot", "closing"):
        return 6, "🤖", "คุยกับบอทอยู่ (ยังไม่ต้องตอบ)"
    if order is not None:
        if order["status"] == "pending":
            return 4, "💳", "รอผู้เล่นจ่าย"
        if order["status"] in ("cart", "review"):
            return 5, "🛒", "กำลังเลือกรายการ"
    staff_at, user_at = _ts(ticket["last_staff_at"]), _ts(ticket["last_user_at"])
    if staff_at is None:
        return 1, "🔴", "ยังไม่มีแอดมินตอบ"
    if user_at and user_at > staff_at:
        return 2, "🟡", "ผู้เล่นตอบล่าสุด รอแอดมิน"
    return 3, "🟢", "ตอบแล้ว รอผู้เล่น"


def board_embed(ttype: TicketType, tickets: list) -> discord.Embed:
    rows, counts = [], {}
    for tk in tickets:
        order = ((db.order_paid_in_thread(tk["channel_id"]) or db.order_latest_in_thread(tk["channel_id"]))
                 if tk["type"] == "donate" else None)
        rank, icon, text = ticket_state(tk, order)
        counts[icon] = counts.get(icon, 0) + 1
        last = max(filter(None, (_ts(tk["last_user_at"]), _ts(tk["last_staff_at"]))), default=None)
        link = f"https://discord.com/channels/{cfg.guild_id}/{tk['channel_id']}"
        line = (f"{icon} [{ttype.prefix}-{tk['number']:04d}]({link}) <@{tk['owner_id']}> — {text}"
                f" · เปิด <t:{_ts(tk['created_at'])}:R>" + (f" · ล่าสุด <t:{last}:R>" if last else ""))
        if order is not None and order["status"] in ("paid", "pending"):
            line += f" · {fmt_baht(order['total'])}"
        rows.append((rank, -(last or _ts(tk["created_at"]) or 0), line))
    rows.sort(key=lambda r: (r[0], r[1]))
    open_rows = [r[2] for r in rows if r[0] < 9]
    closed_rows = [r[2] for r in rows if r[0] >= 9][:5]
    parts = open_rows or ["ไม่มี ticket ค้าง ✨"]
    if closed_rows:
        parts += ["", "**ปิดไปใน 24 ชม.**"] + closed_rows
    text, used = [], 0
    for p in parts:
        if used + len(p) > 3900:
            text.append(f"…และอีก {len(parts) - len(text)} รายการ")
            break
        text.append(p)
        used += len(p) + 1
    worst = min((r[0] for r in rows), default=9)
    color = COLOR_BAD if worst <= 1 else COLOR_WAIT if worst == 2 else COLOR_OK
    embed = discord.Embed(title=f"{ttype.emoji} {ttype.label} — ค้าง {len(open_rows)}", description="\n".join(text),
                          color=color, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=" · ".join(f"{k} {v}" for k, v in counts.items()) or "อัปเดตอัตโนมัติ")
    return embed


def redeem_board_embed() -> discord.Embed:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = [r for r in db.redemptions_recent(40) if r["updated_at"] >= since
            or r["status"] in ("problem", "failed", "manual")]
    lines = []
    for r in rows[:20]:
        icon, text = REDEEM_STATUS.get(r["status"], ("•", r["status"]))
        lines.append(f"{icon} `RD-{r['id']:04d}` <@{r['discord_id']}> {discord.utils.escape_markdown(r['name'])}"
                     f" × {r['qty']} — {text} · <t:{_ts(r['created_at'])}:R>")
    bad = any(r["status"] in ("problem", "failed", "manual") for r in rows)
    return discord.Embed(title="🛍️ แลกของด้วยคุกกี้ (24 ชม.)", description="\n".join(lines) or "ยังไม่มีการแลก",
                         color=COLOR_WAIT if bad else COLOR_OK, timestamp=datetime.now(timezone.utc))


async def scan_activity(guild, ticket):
    """ticket จากเวอร์ชันก่อน: อ่านข้อความล่าสุดเพื่อรู้ว่าใครตอบล่าสุด (ทำครั้งเดียว)"""
    thread = await get_thread(guild, ticket["channel_id"])
    last_user = last_staff = None
    if thread is not None:
        try:
            async for msg in thread.history(limit=60):
                if msg.author.bot:
                    continue
                staff = is_staff(msg.author)  # ออกจากเซิฟแล้ว (User) = ไม่มี role = ไม่ใช่แอดมิน
                if staff and last_staff is None:
                    last_staff = msg.created_at.isoformat()
                if not staff and last_user is None:
                    last_user = msg.created_at.isoformat()
                if last_user and last_staff:
                    break
        except discord.HTTPException:
            pass
    db.ticket_update(ticket["id"], last_user_at=last_user, last_staff_at=last_staff, scanned=1)


async def refresh_board(force: bool = False):
    guild = bot.get_guild(cfg.guild_id)
    if guild is None or not cfg.board_channel:
        return
    channel = guild.get_channel(cfg.board_channel)
    if channel is None:
        return
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    tickets = db.tickets_for_board(since)
    scanned = 0
    for tk in tickets:
        if tk["status"] == "open" and not tk["scanned"] and scanned < 5:
            await scan_activity(guild, tk)
            scanned += 1
    tickets = db.tickets_for_board(since)
    cards = [(key, board_embed(TICKET_TYPES[key], [t for t in tickets if t["type"] == key]))
             for key in BOARD_ORDER if key in TICKET_TYPES and (key != "donate" or cfg.donate_enabled)]
    if cfg.redeem_channel or db.redemptions_recent(1):
        cards.append(("redeem", redeem_board_embed()))
    for key, embed in cards:
        digest = json.dumps([embed.title, embed.description, embed.color.value if embed.color else 0,
                             embed.footer.text])
        if not force and _board["hash"].get(key) == digest:
            continue
        msg_id = int(db.setting(f"board:{key}", "0") or 0)
        try:
            if msg_id:
                try:
                    await channel.get_partial_message(msg_id).edit(embed=embed)
                except discord.NotFound:
                    msg_id = 0
            if not msg_id:
                msg = await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                db.set_setting(f"board:{key}", msg.id)
        except discord.HTTPException as e:
            log.warning("อัปเดตห้องสรุป ticket ไม่ได้: %s", e)
            continue
        _board["hash"][key] = digest
    _board["last"] = time.time()


async def board_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            if _board["dirty"] or time.time() - _board["last"] > 300:
                _board["dirty"] = False
                await refresh_board()
        except Exception:  # noqa: BLE001
            log.exception("ห้องสรุป ticket พัง")
        await asyncio.sleep(20)


def note_ticket_activity(message: discord.Message, ticket):
    if message.author.bot:
        return
    now = message.created_at.isoformat()
    if is_staff(message.author):
        fields = {"last_staff_at": now}
        if ticket["mode"] in ("bot", "closing"):  # แอดมินเข้ามาคุยเอง = โหมดคุยกับแอดมิน (ยกเลิกการลบห้อง)
            fields["mode"] = "admin"
        db.ticket_update(ticket["id"], **fields)
    else:
        db.ticket_update(ticket["id"], last_user_at=now)
    board_dirty()


# =====================================================================
# เตือนคนที่ยังไม่ขอ White List (สรุปให้แอดมินทุกวัน → กดส่งการ์ดแท็กรวมใน newbie)
# =====================================================================

DEFAULT_REMIND_TEXT = ("สวัสดีค่ะ 🍪 เข้ามาแล้วอย่าลืมขอ **White List** เพื่อรับ role **คุกกี้** "
                       "แล้วจะเห็นห้องอื่นๆ ในเซิฟนะคะ ติดขั้นตอนไหนแจ้งได้เลย\n"
                       "ขอได้ที่ห้อง {join}")


def remind_text() -> str:
    return fill_placeholders(db.setting("remind_text") or DEFAULT_REMIND_TEXT)


def remind_candidates(guild) -> list:
    now = datetime.now(timezone.utc)
    joined_before = now - timedelta(days=cfg.wl_remind_after_days)
    repeat_after = now - timedelta(days=cfg.wl_remind_repeat_days)
    requested = db.ever_requested_wl()
    out = []
    for m in guild.members:
        if m.bot or len(m.roles) > 1 or m.id in requested:  # roles มี @everyone เสมอ
            continue
        if m.joined_at is None or m.joined_at > joined_before:
            continue
        info = db.remind_info(m.id)
        if info and info["last_at"] and datetime.fromisoformat(info["last_at"]) > repeat_after:
            continue
        out.append(m)
    out.sort(key=lambda m: m.joined_at)
    return out[:90]


def remind_card(batch, members: list, done_by=None) -> discord.Embed:
    now = datetime.now(timezone.utc)
    rows = []
    for m in members:
        info = db.remind_info(m.id)
        days = (now - m.joined_at).days if m.joined_at else 0
        rows.append(f"{m.mention} · เข้ามา {days} วัน" + (f" · เคยเตือน {info['count']} ครั้ง" if info else ""))
    title = f"🍪 ยังไม่ขอ White List — {len(members)} คน"
    embed = discord.Embed(title=("✅ " if done_by else "") + title, color=COLOR_OK if done_by else COLOR_WAIT,
                          description=trunc("\n".join(rows) or "ไม่มี", 3500), timestamp=now)
    embed.add_field(name="ข้อความที่จะส่งใน newbie", value=trunc(remind_text(), 1024), inline=False)
    embed.set_footer(text=f"ชุด #{batch['id']}" + (f" · ส่งแล้วโดย {done_by}" if done_by else
                                                   f" · นับคนไม่มี role เข้ามาเกิน {cfg.wl_remind_after_days} วัน"))
    return embed


class RemindButton(ui.DynamicItem[ui.Button], template=r"cc:remind:(?P<act>send|skip|edit):(?P<bid>\d+)"):
    def __init__(self, act: str, bid: int):
        labels = {"send": ("ส่งเตือนใน newbie", "📣", discord.ButtonStyle.success),
                  "edit": ("แก้ข้อความ", "📝", discord.ButtonStyle.secondary),
                  "skip": ("ข้าม", "⏩", discord.ButtonStyle.secondary)}
        label, emoji, style = labels[act]
        super().__init__(ui.Button(label=label, emoji=emoji, style=style, custom_id=f"cc:remind:{act}:{bid}"))
        self.act, self.bid = act, bid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["act"], int(match["bid"]))

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับแอดมิน")
        batch = db.batch_get(self.bid)
        if batch is None or batch["sent_at"]:
            return await reply(interaction, "ชุดนี้ส่ง/ข้ามไปแล้ว")
        if self.act == "edit":
            return await interaction.response.send_modal(TextSettingModal(
                "remind_text", "ข้อความเตือนขอ White List", DEFAULT_REMIND_TEXT,
                hint="{join} = ลิงก์ห้องวิธีเข้าเซิฟ", after=lambda i: refresh_remind_card(i, self.bid)))
        if not db.batch_claim(self.bid, interaction.user.id):  # กดซ้ำ/กดพร้อมกัน 2 คน → ส่งครั้งเดียว
            return await reply(interaction, "ชุดนี้ส่ง/ข้ามไปแล้ว")
        if self.act == "skip":
            return await interaction.response.edit_message(content="ข้ามชุดนี้แล้ว", view=None)
        await interaction.response.defer()
        await send_reminder(interaction, batch)


def remind_view(bid: int) -> ui.View:
    view = ui.View(timeout=None)
    for act in ("send", "edit", "skip"):
        view.add_item(RemindButton(act, bid))
    return view


async def refresh_remind_card(interaction, bid):
    batch = db.batch_get(bid)
    if batch is None or not batch["admin_msg_id"]:
        return
    members = [m for m in (interaction.guild.get_member(i) for i in json.loads(batch["user_ids"])) if m]
    try:
        await interaction.channel.get_partial_message(batch["admin_msg_id"]).edit(
            embed=remind_card(batch, members), view=remind_view(bid))
    except discord.HTTPException:
        pass


async def post_remind_card(guild, *, manual_by=None):
    """สร้างการ์ดสรุปในห้องแอดมิน — คืนข้อความ หรือ None ถ้าไม่มีใครค้าง"""
    members = remind_candidates(guild)
    if not members:
        return None
    bid = db.batch_create([m.id for m in members])
    batch = db.batch_get(bid)
    msg = await log_to(guild, cfg.admin_alert_channel or cfg.mod_logs, remind_card(batch, members),
                       view=remind_view(bid))
    if msg:
        db.batch_update(bid, admin_msg_id=msg.id)
    return msg


async def send_reminder(interaction: discord.Interaction, batch):
    guild = interaction.guild
    target = guild.get_channel(cfg.newbie_channel) if cfg.newbie_channel else None
    if target is None:
        db.batch_update(batch["id"], sent_at=None, sent_by=None)  # ปล่อยให้กดใหม่ได้หลังตั้งห้อง
        return await interaction.followup.send("ยังไม่ได้ตั้ง NEWBIE_CHANNEL_ID หรือบอทมองไม่เห็นห้องนั้น", ephemeral=True)
    members = []
    for uid in json.loads(batch["user_ids"]):
        m = guild.get_member(uid)
        if m and len(m.roles) == 1:  # ยังอยู่และยังไม่มี role
            members.append(m)
    if not members:
        db.batch_update(batch["id"], sent_at=datetime.now(timezone.utc).isoformat(), sent_by=interaction.user.id)
        return await interaction.followup.send("ทุกคนในชุดนี้ได้ role แล้ว หรือออกจากเซิฟไปแล้ว", ephemeral=True)
    card = discord.Embed(title="🍪 อย่าลืมขอ White List นะคะ", description=remind_text(), color=cfg.accent_color)
    view = None
    url = channel_link(cfg.join_channel)
    if url:
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="ไปห้องวิธีเข้าเซิฟ", emoji="🍪", url=url))
    chunks, cur = [], []
    for m in members:  # ข้อความหนึ่งแท็กได้ไม่เกิน ~80 คน
        if len(" ".join(x.mention for x in cur + [m])) > 1900:
            chunks.append(cur)
            cur = []
        cur.append(m)
    chunks.append(cur)
    for i, chunk in enumerate(chunks):
        kwargs = {"embed": card, **({"view": view} if view else {})} if i == len(chunks) - 1 else {}
        await target.send(" ".join(m.mention for m in chunk),
                          allowed_mentions=discord.AllowedMentions(users=chunk, roles=False, everyone=False), **kwargs)
    db.remind_mark([m.id for m in members])
    db.batch_update(batch["id"], sent_at=datetime.now(timezone.utc).isoformat(), sent_by=interaction.user.id)
    try:
        await interaction.message.edit(embed=remind_card(db.batch_get(batch["id"]), members,
                                                         done_by=interaction.user.display_name), view=None)
    except discord.HTTPException:
        pass
    await interaction.followup.send(f"ส่งเตือน {len(members)} คนใน {target.mention} แล้ว", ephemeral=True)


async def remind_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now(TZ)
            today = now.strftime("%Y-%m-%d")
            if now.hour == cfg.wl_remind_hour and db.setting("remind:last_day") != today:
                db.set_setting("remind:last_day", today)
                guild = bot.get_guild(cfg.guild_id)
                if guild is not None:
                    await post_remind_card(guild)
        except Exception:  # noqa: BLE001
            log.exception("สรุปคนที่ยังไม่ขอ White List พัง")
        await asyncio.sleep(60)


class TextSettingModal(BaseModal):
    """แก้ข้อความยาวๆ ที่เก็บใน settings (วิธีเข้าเซิฟ / ข้อความเตือน)"""

    def __init__(self, key: str, title: str, default: str, hint: str = "", after=None):
        super().__init__(title=trunc(title, 45), timeout=900)
        self.key, self.after = key, after
        self.text = ui.TextInput(label=trunc(f"ข้อความ {hint}".strip(), 45), style=discord.TextStyle.paragraph,
                                 default=trunc(db.setting(key) or default, 4000), max_length=4000, required=True)
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        db.set_setting(self.key, self.text.value.strip())
        await reply(interaction, "บันทึกแล้ว ✅")
        if self.after:
            await self.after(interaction)


# =====================================================================
# คุกกี้ 🍪 — วงล้อรายวัน · กระเป๋าส่วนตัว · ร้านแลกของ · ส่งเข้าเกมผ่าน Cookie Express
# =====================================================================

IMAGES_DIR: Path = BASE_DIR / "data" / "images"  # main() ตั้งเป็น <DATA_DIR>/images
_rng = secrets.SystemRandom()
_wallet_locks: dict = {}
SHOP_PAGE = 4
MAX_REDEEM_QTY = 20
COLOR_COOKIE = 0xD9A066

LEDGER_TH = {"spin": "🎡 วงล้อรายวัน", "topup": "💝 Donate", "redeem": "🛍️ แลก", "refund": "↩️ คืน",
             "admin": "🎁 แอดมินให้", "take": "➖ แอดมินหัก"}
REDEEM_STATUS = {
    "queued": ("⏳", "กำลังส่งเข้าเกม"), "posting": ("⏳", "รอส่งคำสั่ง"), "sent": ("⏳", "ส่งคำสั่งแล้ว รอเซิฟรับ"),
    "inqueue": ("📦", "อยู่ในคิวแล้ว — เข้าเกมแล้วกดรับที่ปุ่มบ้านคุกกี้"), "seen": ("👀", "ขึ้นในเกมแล้ว รอกดรับ"),
    "partial": ("✅", "รับไปบางส่วน"), "claimed": ("✅", "รับในเกมแล้ว"), "failed": ("❌", "ส่งไม่สำเร็จ"),
    "problem": ("⚠️", "มีปัญหา รอแอดมินดู"), "cancelled": ("🗑️", "ยกเลิก"), "refunded": ("↩️", "คืนคุกกี้แล้ว"),
    "manual": ("🙋", "รอแอดมินส่งของ"), "done": ("✅", "แอดมินส่งให้แล้ว"),
}


def wallet_lock(uid: int) -> asyncio.Lock:
    return _wallet_locks.setdefault(uid, asyncio.Lock())


def today_key() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")


def next_reset_ts() -> int:
    now = datetime.now(TZ)
    return int((now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def pick_prize(pool):
    pool = [p for p in pool if p["weight"] > 0]
    return _rng.choices(pool, weights=[p["weight"] for p in pool], k=1)[0]


def pool_odds(pool) -> str:
    total = sum(p["weight"] for p in pool if p["weight"] > 0)
    if not total:
        return "_แอดมินยังไม่ได้ตั้งรางวัล_"
    return "\n".join(f"{discord.utils.escape_markdown(p['label'])} · **{fmt_cookies(p['cookies'])}** · "
                     f"{p['weight'] / total * 100:.1f}%" for p in pool if p["weight"] > 0)


def schedule_delete(interaction: discord.Interaction, seconds: int = None):
    async def later():
        await asyncio.sleep(seconds or cfg.spin_result_seconds)
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass
    asyncio.create_task(later())


def parse_when(text: str, end: bool = False) -> Optional[datetime]:
    """'2026-10-31' '31/10/2026 23:59' '31/10/2569' → datetime (เวลาไทย) · ว่าง/'-' → None"""
    text = (text or "").strip()
    if not text or text == "-":
        return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2}))?", text) or \
        re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", text)
    if not m:
        raise app_commands.AppCommandError(f"วันที่ `{text}` อ่านไม่ออก — ใช้ 2026-10-31 หรือ 31/10/2026 23:59")
    a, b, c, hh, mm = m.groups()
    year, month, day = (int(a), int(b), int(c)) if len(a) == 4 else (int(c), int(b), int(a))
    if year > 2400:  # ปี พ.ศ.
        year -= 543
    if hh is None:
        hh, mm = (23, 59) if end else (0, 0)
    try:
        return datetime(year, month, day, int(hh), int(mm), tzinfo=TZ)
    except ValueError:
        raise app_commands.AppCommandError(f"วันที่ `{text}` ไม่มีจริง")


def item_state(item, now: datetime) -> str:
    if item["stock"] == 0:
        return "soldout"
    if item["start_at"] and now < datetime.fromisoformat(item["start_at"]):
        return "soon"
    if item["end_at"]:
        end = datetime.fromisoformat(item["end_at"])
        if now > end:
            return "ended"
        if end - now < timedelta(hours=48):
            return "hot"
    return "open"


def item_image_url(item) -> Optional[str]:
    if not item["image"] or not cfg.public_url:
        return None
    return f"{cfg.public_url}/img/{item['image']}?v={_ts(item['updated_at']) or 0}"


def item_chips(item, uid: int = 0) -> list:
    chips = []
    if item["per_user_limit"]:
        left = item["per_user_limit"] - (db.redeemed_qty(uid, item["code"]) if uid else 0)
        chips.append(f"แลกได้ {item['per_user_limit']} ครั้ง/คน" + (f" (เหลือ {max(0, left)})" if uid else ""))
    if item["stock"] >= 0:
        chips.append(f"เหลือ {item['stock']} ชิ้น")
    if item["start_at"] and datetime.fromisoformat(item["start_at"]) > datetime.now(timezone.utc):
        chips.append(f"เปิด <t:{_ts(item['start_at'])}:R>")
    if item["end_at"]:
        chips.append(f"ถึง <t:{_ts(item['end_at'])}:f>")
    chips.append("📦 ส่งเข้าเกมเอง" if item["ckx"] else "🙋 แอดมินส่งให้")
    return chips


# ---------------------------------------------------------------- วงล้อรายวัน

class SpinPanelView(BaseLayout):
    def __init__(self):
        super().__init__(timeout=None)
        spin = ui.Button(label="หมุนเลย", emoji="🎡", style=discord.ButtonStyle.success, custom_id="cc:spin:go")
        spin.callback = do_spin
        wallet = ui.Button(label="กระเป๋าของฉัน", emoji="👛", style=discord.ButtonStyle.secondary,
                           custom_id="cc:wallet:open")
        wallet.callback = open_wallet
        mins = max(1, cfg.spin_result_seconds // 60)
        self.add_item(ui.Container(
            ui.TextDisplay(f"## 🎡 วงล้อคุกกี้รายวัน\nหมุนได้วันละ 1 ครั้ง รีเซ็ตเที่ยงคืน · ผลเห็นแค่คุณคนเดียว "
                           f"และหายไปเองใน {mins} นาที\nคุกกี้ที่ได้เอาไปแลกของได้ที่ {fill_placeholders('{redeem}')}"),
            ui.Separator(),
            ui.TextDisplay(f"**รางวัล**\n{pool_odds(db.spin_pool())}"),
            ui.ActionRow(spin, wallet),
            accent_colour=COLOR_COOKIE))


async def do_spin(interaction: discord.Interaction):
    pool = db.spin_pool()
    if not pool or not any(p["weight"] > 0 for p in pool):
        return await reply(interaction, "วงล้อยังไม่เปิด — รอแอดมินตั้งรางวัลก่อนนะ")
    uid, day = interaction.user.id, today_key()
    prev = db.spin_today(uid, day)
    if prev is None:
        balance = db.spin_record(uid, day, dict(pick_prize(pool)))
        prev = None if balance is not None else db.spin_today(uid, day)
    if prev is not None:
        embed = discord.Embed(title="วันนี้หมุนไปแล้วนะ 🍪", color=COLOR_MUTED,
                              description=f"ได้ **{fmt_cookies(prev['cookies'])}** ({prev['label']})\n"
                                          f"หมุนใหม่ได้ <t:{next_reset_ts()}:R>")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return schedule_delete(interaction)
    got = db.spin_today(uid, day)
    await interaction.response.send_message(embed=discord.Embed(title="🎡 กำลังหมุน...", color=COLOR_COOKIE,
                                                                description="🍪 · 🍩 · 🍪 · 🧁 · 🍪"), ephemeral=True)
    schedule_delete(interaction)
    await asyncio.sleep(1.4)
    embed = discord.Embed(title=f"🎉 ได้ {fmt_cookies(got['cookies'])}", color=COLOR_OK,
                          description=f"{got['label']}\n\nคุกกี้ตอนนี้: **{fmt_cookies(balance)}**\n"
                                      f"เอาไปแลกของได้ที่ {fill_placeholders('{redeem}')}\n\n"
                                      f"-# ข้อความนี้จะหายไปเองใน {max(1, cfg.spin_result_seconds // 60)} นาที")
    try:
        await interaction.edit_original_response(embed=embed)
    except discord.HTTPException:
        pass
    try:
        await ensure_wallet(interaction.guild, interaction.user, create=True)
    except discord.HTTPException as e:
        log.warning("สร้าง/อัปเดตกระเป๋าไม่ได้: %s", e)


# ---------------------------------------------------------------- กระเป๋า (private thread ต่อคน)

class WalletCardView(BaseLayout):
    def __init__(self, uid: int = 0):
        super().__init__(timeout=None)
        if web_shop_on():
            shop = web_shop_button()
        else:
            shop = ui.Button(label="เปิดร้าน", emoji="🛒", style=discord.ButtonStyle.success, custom_id="cc:shop:open")
            shop.callback = open_shop
        name = ui.Button(label="ชื่อในเกม", emoji="🎮", style=discord.ButtonStyle.secondary, custom_id="cc:wallet:name")
        name.callback = change_name
        buttons = [shop, name]
        spin_url = channel_link(cfg.spin_channel)
        if spin_url:
            buttons.append(ui.Button(label="ไปหมุนวงล้อ", emoji="🎡", url=spin_url))
        if not uid:  # แบบเปล่าไว้ลงทะเบียนปุ่ม
            self.add_item(ui.Container(ui.TextDisplay("🍪 กระเป๋าคุกกี้"), ui.ActionRow(*buttons)))
            return
        w = db.wallet_ensure(uid)
        spin = db.spin_today(uid, today_key())
        spin_line = (f"🎡 วันนี้ได้ **{fmt_cookies(spin['cookies'])}** ({spin['label']})" if spin else
                     f"🎡 วันนี้ยังไม่ได้หมุน → {fill_placeholders('{spin}')}")
        name_line = (f"🎮 ชื่อรับของในเกม: **{discord.utils.escape_markdown(w['ingame'])}**" if w["ingame"] else
                     "🎮 ยังไม่ได้ตั้งชื่อในเกม — กด **ชื่อในเกม** ก่อนแลกของ")
        hist = [f"`{e['delta']:+,}` {LEDGER_TH.get(e['kind'], e['kind'])}"
                + (f" · {discord.utils.escape_markdown(trunc(e['note'], 40))}" if e["note"] else "")
                + f" · <t:{_ts(e['created_at'])}:R>" for e in db.ledger_recent(uid, 6)]
        reds = [f"{REDEEM_STATUS.get(r['status'], ('•', ''))[0]} `RD-{r['id']:04d}` "
                f"{discord.utils.escape_markdown(r['name'])} × {r['qty']} — {REDEEM_STATUS.get(r['status'], ('', r['status']))[1]}"
                for r in db.redemptions_of(uid, 5)]
        parts = [ui.TextDisplay(f"## 🍪 กระเป๋าคุกกี้ของ <@{uid}>\n# {fmt_cookies(w['balance'])}\n{spin_line}\n{name_line}")]
        if hist:
            parts += [ui.Separator(), ui.TextDisplay("**ล่าสุด**\n" + "\n".join(hist))]
        if reds:
            parts += [ui.Separator(), ui.TextDisplay("**ของที่แลก**\n" + "\n".join(reds))]
        parts.append(ui.ActionRow(*buttons))
        self.add_item(ui.Container(*parts, accent_colour=COLOR_COOKIE))


async def ensure_wallet(guild, member, create: bool = True):
    """หา/สร้าง private thread กระเป๋าของคนนี้ แล้วอัปเดตการ์ด — คืน thread หรือ None"""
    if guild is None:
        return None
    uid = member.id
    async with wallet_lock(uid):
        w = db.wallet_ensure(uid)
        thread = await get_thread(guild, w["thread_id"], unarchive=True) if w["thread_id"] else None
        if thread is None and create and cfg.wallet_channel:
            parent = guild.get_channel(cfg.wallet_channel)
            if not isinstance(parent, discord.TextChannel):
                log.warning("WALLET_CHANNEL_ID / SPIN_CHANNEL_ID ต้องเป็นห้องข้อความ")
                return None
            thread = await parent.create_thread(
                name=trunc(f"🍪 {getattr(member, 'display_name', uid)}", 100), type=discord.ChannelType.private_thread,
                invitable=False, auto_archive_duration=10080, reason="กระเป๋าคุกกี้")
            await thread.add_user(member)
            db.wallet_update(uid, thread_id=thread.id, card_id=None)
            w = db.wallet_get(uid)
        if thread is None:
            return None
        view = WalletCardView(uid)
        if w["card_id"]:
            try:
                await thread.get_partial_message(w["card_id"]).edit(view=view)
                return thread
            except discord.NotFound:
                pass
        msg = await thread.send(view=view, allowed_mentions=discord.AllowedMentions.none())
        db.wallet_update(uid, card_id=msg.id)
        return thread


async def refresh_wallet(guild, uid: int):
    """อัปเดตการ์ดกระเป๋า (ถ้ามี thread แล้ว)"""
    if guild is None or not (db.wallet_get(uid) or {"thread_id": None})["thread_id"]:
        return
    member = guild.get_member(uid) or discord.Object(id=uid)
    try:
        await ensure_wallet(guild, member, create=False)
    except discord.HTTPException as e:
        log.warning("อัปเดตกระเป๋า %s ไม่ได้: %s", uid, e)


async def open_wallet(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    thread = None
    try:
        thread = await ensure_wallet(interaction.guild, interaction.user, create=True)
    except discord.HTTPException as e:
        log.warning("เปิดกระเป๋าไม่ได้: %s", e)
    w = db.wallet_ensure(interaction.user.id)
    where = f"\nดูประวัติได้ที่ {thread.mention}" if thread else ""
    await interaction.followup.send(f"คุกกี้ของคุณ: **{fmt_cookies(w['balance'])}**{where}", ephemeral=True)


class IngameNameModal(BaseModal):
    def __init__(self, default: str = "", after=None, target: int = 0):
        super().__init__(title="ชื่อในเกม (ใช้รับของ)", timeout=600)
        self.after, self.target = after, target
        self.name = ui.TextInput(label="ชื่อที่ใช้ล็อกอินเข้าเซิฟ", default=trunc(default, 40) or None,
                                 max_length=40, placeholder="ตัวพิมพ์เล็ก/ใหญ่ไม่ต้องตรง")
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        name = self.name.value.strip()
        if not ckx_link.valid_ingame(name):
            return await reply(interaction, "ชื่อนี้ใช้ไม่ได้ (ห้ามมี \" | ` และยาวไม่เกิน 40 ตัว)")
        target = self.target or interaction.user.id  # แอดมินกรอกแทนผู้เล่น → เขียนลงกระเป๋าผู้เล่น ไม่ใช่ของแอดมิน
        db.wallet_update(target, ingame=name)
        if self.after:
            await self.after(interaction, name)
        else:
            await reply(interaction, f"ตั้งชื่อรับของในเกมเป็น **{discord.utils.escape_markdown(name)}** แล้ว ✅")
        await refresh_wallet(interaction.guild, target)


async def change_name(interaction: discord.Interaction):
    w = db.wallet_ensure(interaction.user.id)
    await interaction.response.send_modal(IngameNameModal(w["ingame"]))


# ---------------------------------------------------------------- ร้านแลกของ (เห็นคนเดียว)

def shop_visible(now: datetime) -> list:
    return [i for i in db.shop_items() if item_state(i, now) != "ended"]


class ShopView(BaseLayout):
    def __init__(self, user, page: int = 0, category: Optional[str] = None):
        super().__init__(timeout=900)
        self.user, self.category = user, category
        now = datetime.now(timezone.utc)
        items = shop_visible(now)
        cats = sorted({i["category"] for i in items if i["category"]})
        if category:
            items = [i for i in items if i["category"] == category]
        pages = max(1, -(-len(items) // SHOP_PAGE))
        self.page = page = max(0, min(page, pages - 1))
        w = db.wallet_ensure(user.id)
        name = discord.utils.escape_markdown(w["ingame"]) if w["ingame"] else "ยังไม่ได้ตั้ง"
        children = [ui.TextDisplay(f"## 🛍️ Cookie Shop\nคุกกี้ของคุณ **{fmt_cookies(w['balance'])}** · "
                                   f"ชื่อรับของในเกม **{name}**")]
        if cats:
            select = ui.Select(placeholder=f"หมวด: {category or 'ทั้งหมด'}", options=[
                discord.SelectOption(label="ทั้งหมด", value="*", default=not category)] + [
                discord.SelectOption(label=trunc(c, 100), value=trunc(c, 100), default=c == category) for c in cats[:24]])
            select.callback = self._pick_category
            self.select = select
            children.append(ui.ActionRow(select))
        if not items:
            children.append(ui.TextDisplay("_ยังไม่มีของในร้าน รอแอดมินเติมของก่อนนะ_ 🍪"))
        for item in items[page * SHOP_PAGE:(page + 1) * SHOP_PAGE]:
            state = item_state(item, now)
            text = (f"### {discord.utils.escape_markdown(item['name'])}\n"
                    + (f"{trunc(item['description'], 300)}\n" if item["description"] else "")
                    + f"**{fmt_cookies(item['price'])}** · " + " · ".join(item_chips(item, user.id)))
            url = item_image_url(item)
            children.append(ui.Separator())
            children.append(ui.Section(ui.TextDisplay(text), accessory=ui.Thumbnail(url)) if url
                            else ui.TextDisplay(text))
            short = item["price"] - w["balance"]
            if state == "soon":
                label, disabled = "ยังไม่เปิด", True
            elif state == "soldout":
                label, disabled = "หมดแล้ว", True
            elif short > 0:
                label, disabled = f"ขาดอีก {short:,} 🍪", True
            else:
                label, disabled = f"แลก · {item['price']:,} 🍪", False
            btn = ui.Button(label=label, style=discord.ButtonStyle.success, disabled=disabled)
            btn.callback = self._redeem_cb(item["code"])
            children.append(ui.ActionRow(btn))
        children.append(ui.Separator())
        prev = ui.Button(label="◀", style=discord.ButtonStyle.secondary, disabled=page == 0)
        prev.callback = self._goto(page - 1)
        info = ui.Button(label=f"หน้า {page + 1}/{pages}", style=discord.ButtonStyle.secondary, disabled=True)
        nxt = ui.Button(label="▶", style=discord.ButtonStyle.secondary, disabled=page >= pages - 1)
        nxt.callback = self._goto(page + 1)
        row = [prev, info, nxt]
        if cfg.public_url and cfg.web_enabled:
            row.append(ui.Button(label="ดูบนเว็บ", emoji="🌐", url=cfg.public_url + "/"))
        wallet = ui.Button(label="กระเป๋า", emoji="👛", style=discord.ButtonStyle.secondary)
        wallet.callback = open_wallet
        row.append(wallet)
        children.append(ui.ActionRow(*row))
        self.add_item(ui.Container(*children, accent_colour=COLOR_DONATE))

    def _goto(self, page):
        async def cb(interaction: discord.Interaction):
            await interaction.response.edit_message(view=ShopView(self.user, page, self.category))
        return cb

    async def _pick_category(self, interaction: discord.Interaction):
        value = self.select.values[0]
        await interaction.response.edit_message(view=ShopView(self.user, 0, None if value == "*" else value))

    def _redeem_cb(self, code):
        async def cb(interaction: discord.Interaction):
            item = db.shop_get(code)
            problem = shop_problem(item, datetime.now(timezone.utc))
            if problem:
                return await reply(interaction, f"❌ {problem}")
            w = db.wallet_ensure(interaction.user.id)
            limit = min(redeem_cap(item, interaction.user.id), w["balance"] // max(1, item["price"]))
            if limit < 1:
                return await reply(interaction, "แลกชิ้นนี้ไม่ได้แล้ว (ครบสิทธิ์ / ของหมด / คุกกี้ไม่พอ)")
            await interaction.response.send_modal(RedeemModal(item, w["ingame"], limit))
        return cb


def web_shop_button(label: str = "เปิดร้าน") -> ui.Button:
    return ui.Button(label=label, emoji="🛒", url=cfg.public_url + "/")


async def open_shop(interaction: discord.Interaction):
    if web_shop_on():  # ร้านย้ายไปหน้าเว็บ (ปุ่มเก่าในข้อความเดิมยังกดได้)
        w = db.wallet_ensure(interaction.user.id)
        view = ui.View()
        view.add_item(web_shop_button("เปิดร้านบนเว็บ"))
        return await interaction.response.send_message(
            f"🛍️ ร้านคุกกี้อยู่บนเว็บแล้ว — ล็อกอินด้วย Discord ใส่ตะกร้าแล้วกดแลกได้เลย\n"
            f"คุกกี้ของคุณตอนนี้ **{fmt_cookies(w['balance'])}**", view=view, ephemeral=True)
    await interaction.response.send_message(view=ShopView(interaction.user), ephemeral=True)


class ShopOpenRouter(BaseLayout):
    """จับปุ่ม cc:shop:open ในข้อความเก่า (ป้ายร้าน/กระเป๋าที่โพสต์ก่อนเปิดร้านบนเว็บ)"""

    def __init__(self):
        super().__init__(timeout=None)
        btn = ui.Button(label="เปิดร้าน", custom_id="cc:shop:open")
        btn.callback = open_shop
        self.add_item(ui.ActionRow(btn))


class RedeemModal(BaseModal):
    def __init__(self, item, ingame: str, max_qty: int):
        super().__init__(title=trunc(f"แลก {item['name']}", 45), timeout=600)
        self.code, self.max_qty, self.needs_name = item["code"], max_qty, bool(item["ckx"])
        self.name = ui.TextInput(label="ชื่อในเกมที่จะรับของ", default=trunc(ingame, 40) or None, max_length=40,
                                 required=self.needs_name, placeholder="ชื่อที่ใช้ล็อกอินเข้าเซิฟ")
        self.add_item(self.name)
        self.qty = None
        if max_qty > 1:
            self.qty = ui.TextInput(label=f"จำนวน (สูงสุด {max_qty})", default="1", max_length=2)
            self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        qty_text = (self.qty.value.strip() if self.qty else "1")
        if not qty_text.isdigit() or not 1 <= int(qty_text) <= self.max_qty:
            return await reply(interaction, f"จำนวนต้องเป็น 1–{self.max_qty}")
        name = self.name.value.strip()
        if self.needs_name and not ckx_link.valid_ingame(name):
            return await reply(interaction, "ชื่อในเกมใช้ไม่ได้ (ห้ามมี \" | ` และยาวไม่เกิน 40 ตัว)")
        await interaction.response.defer(ephemeral=True, thinking=True)
        await do_redeem(interaction, self.code, int(qty_text), name)


async def do_redeem(interaction: discord.Interaction, code: str, qty: int, ingame: str):
    uid = interaction.user.id
    item = db.shop_get(code)
    if item is None:
        return await interaction.followup.send("ไม่มีของชิ้นนี้แล้ว", ephemeral=True)
    if item["ckx"]:
        try:
            items = ckx_link.normalize_items(item["ckx"], multiply=qty)
        except ValueError as e:
            await mod_log(interaction.guild, f"❌ ร้านคุกกี้: รหัสของ `{item['code']}` ผิด ({e})", COLOR_BAD)
            return await interaction.followup.send("ของชิ้นนี้ตั้งค่าผิด แจ้งแอดมินแล้ว ลองชิ้นอื่นก่อนนะ", ephemeral=True)
    rid, err = db.redeem(uid, code, qty, ingame, datetime.now(timezone.utc))
    if err:
        return await interaction.followup.send(f"❌ {err}", ephemeral=True)
    if ingame and ckx_link.valid_ingame(ingame):
        db.wallet_update(uid, ingame=ingame)
    if item["ckx"]:
        job_id = db.job_create("redeem", rid, uid, ingame, items, ckx_link.count_lines(items))
        db.redemption_update(rid, job_id=job_id, status="posting")
        await ckx_post(job_id)
    else:
        db.redemption_update(rid, status="manual")
    await redemption_changed(interaction.guild, rid, notify_staff=not item["ckx"])
    r = db.redemption_get(rid)
    icon, text = REDEEM_STATUS.get(r["status"], ("", r["status"]))
    w = db.wallet_get(uid)
    where = f"\nดูสถานะในกระเป๋า <#{w['thread_id']}>" if w and w["thread_id"] else ""
    await interaction.followup.send(
        f"🎉 แลก **{item['name']}** × {qty} แล้ว · ใบแลก `RD-{rid:04d}`\n{icon} {text}\n"
        f"คุกกี้เหลือ **{fmt_cookies(w['balance'] if w else 0)}**{where}", ephemeral=True)


def receipt_embed(r) -> discord.Embed:
    icon, text = REDEEM_STATUS.get(r["status"], ("•", r["status"]))
    color = (COLOR_OK if r["status"] in ("claimed", "done") else COLOR_BAD if r["status"] in ("failed", "problem")
             else COLOR_MUTED if r["status"] in ("refunded", "cancelled") else COLOR_COOKIE)
    embed = discord.Embed(title=f"🧾 ใบแลก RD-{r['id']:04d}", color=color, timestamp=datetime.fromisoformat(r["created_at"]))
    embed.add_field(name="ของ", value=f"{discord.utils.escape_markdown(r['name'])} × {r['qty']}")
    embed.add_field(name="ใช้คุกกี้", value=fmt_cookies(r["price"] * r["qty"]))
    if r["ingame"]:
        embed.add_field(name="ชื่อในเกม", value=discord.utils.escape_markdown(r["ingame"]))
    embed.add_field(name="สถานะ", value=f"{icon} {text}" + (f"\n-# {trunc(r['note'], 200)}" if r["note"] else ""),
                    inline=False)
    embed.set_footer(text=f"{r['code']} · ผู้แลก {r['discord_id']}")
    return embed


class RedeemAdminButton(ui.DynamicItem[ui.Button], template=r"cc:rd:(?P<act>refund|resend|done):(?P<rid>\d+)"):
    LABELS = {"refund": ("คืนคุกกี้", "🔙", discord.ButtonStyle.danger),
              "resend": ("ส่งเข้าเกมอีกครั้ง", "🔁", discord.ButtonStyle.primary),
              "done": ("ส่งให้แล้ว", "📦", discord.ButtonStyle.success)}

    def __init__(self, act: str, rid: int):
        label, emoji, style = self.LABELS[act]
        super().__init__(ui.Button(label=label, emoji=emoji, style=style, custom_id=f"cc:rd:{act}:{rid}"))
        self.act, self.rid = act, rid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["act"], int(match["rid"]))

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับแอดมิน")
        await interaction.response.defer(ephemeral=True, thinking=True)
        msg = await redeem_admin_action(interaction.guild, self.act, self.rid, interaction.user)
        await interaction.followup.send(msg, ephemeral=True)


REFUNDABLE = ("failed", "problem", "manual", "posting", "sent", "inqueue", "seen", "queued", "cancelled")
RESENDABLE = ("failed", "problem", "cancelled", "posting")


def redeem_delivered_some(r) -> bool:
    job = db.job_get(r["job_id"]) if r["job_id"] else None
    return job is not None and job["lines_done"] > 0


async def redeem_admin_action(guild, act: str, rid: int, by) -> str:
    r = db.redemption_get(rid)
    if r is None:
        return "ไม่พบใบแลกนี้"
    if act == "refund":
        if not is_admin(by):
            return "คืนคุกกี้ได้เฉพาะแอดมิน (Manage Server / ROLE_ADMIN)"
        if r["status"] == "refunded":
            return "คืนไปแล้ว"
        if r["status"] not in REFUNDABLE or redeem_delivered_some(r):
            return "ผู้เล่นรับของในเกมไปแล้ว (บางส่วน) คืนคุกกี้ไม่ได้ — ให้คุกกี้เองด้วย /cookies give ถ้าจำเป็น"
        if r["job_id"] and not await ckx_cancel(r["job_id"]):
            return "ยกเลิกออเดอร์ในเกมไม่ได้ (ผู้เล่นรับไปแล้ว หรือส่งคำสั่งยกเลิกไม่ได้) — ยังไม่ได้คืนคุกกี้"
        if db.refund(rid, by=by.id, note=f"แอดมินคืน RD-{rid:04d}") is None:
            return "คืนไปแล้ว"
        result = f"คืน {fmt_cookies(r['price'] * r['qty'])} ให้ <@{r['discord_id']}> แล้ว"
    elif act == "resend":
        if r["status"] not in RESENDABLE or redeem_delivered_some(r):
            return "ส่งซ้ำได้เฉพาะใบที่ล้มเหลว/มีปัญหา/ยกเลิก และผู้เล่นยังไม่ได้รับอะไรเลย"
        if not r["ckx"]:
            return "ของชิ้นนี้ไม่มีรหัส Cookie Express — กด 📦 ส่งให้แล้ว เมื่อส่งเอง"
        ingame = (db.wallet_get(r["discord_id"]) or {"ingame": ""})["ingame"] or r["ingame"]
        if not ckx_link.valid_ingame(ingame):
            return "ผู้เล่นยังไม่มีชื่อในเกมที่ใช้ได้"
        if r["job_id"] and not await ckx_cancel(r["job_id"]):
            return "ยกเลิกออเดอร์เดิมไม่ได้ (ผู้เล่นอาจรับไปแล้ว) — ไม่ได้ส่งซ้ำ"
        items = ckx_link.normalize_items(r["ckx"], multiply=r["qty"])
        job_id = db.job_create("redeem", rid, r["discord_id"], ingame, items, ckx_link.count_lines(items))
        db.redemption_update(rid, job_id=job_id, status="posting", ingame=ingame, note="")
        await ckx_post(job_id)
        result = f"ส่ง RD-{rid:04d} เข้าคิวใหม่แล้ว (ชื่อ {ingame})"
    else:
        if r["status"] == "refunded":
            return "ใบนี้คืนคุกกี้ไปแล้ว"
        db.redemption_update(rid, status="done", note=f"ส่งโดย {by.display_name}")
        result = f"บันทึกว่าส่ง RD-{rid:04d} แล้ว"
    await redemption_changed(guild, rid)
    await log_to(guild, cfg.redeem_log or cfg.donate_log or cfg.mod_logs,
                 discord.Embed(description=f"🛠️ {by.mention}: {result}", color=COLOR_INFO))
    return result


def redeem_admin_view(r) -> Optional[ui.View]:
    acts = []
    some = redeem_delivered_some(r)
    if r["status"] in REFUNDABLE and not some:
        acts.append("refund")
    if r["ckx"] and r["status"] in RESENDABLE and not some:
        acts.append("resend")
    if r["status"] in ("manual", "problem"):
        acts.append("done")
    if not acts:
        return None
    view = ui.View(timeout=None)
    for a in acts:
        view.add_item(RedeemAdminButton(a, r["id"]))
    return view


async def redemption_changed(guild, rid: int, notify_staff: bool = False, cart_receipt: bool = True):
    """อัปเดตใบแลกในกระเป๋า + log แอดมิน + การ์ดกระเป๋า + ห้องสรุป
    ใบที่มาจากตะกร้าเว็บ → อัปเดตใบแลกรวมของตะกร้าแทนใบเดี่ยว"""
    if guild is None:
        return
    r = db.redemption_get(rid)
    embed = receipt_embed(r)
    thread = None
    if r["cart_id"]:
        if cart_receipt:
            await cart_receipt_update(guild, r["cart_id"])
    else:
        member = guild.get_member(r["discord_id"])
        try:
            thread = await ensure_wallet(guild, member or discord.Object(id=r["discord_id"]),
                                         create=member is not None)
        except discord.HTTPException as e:
            log.warning("กระเป๋าของ %s: %s", r["discord_id"], e)
    if thread is not None:
        try:
            if r["receipt_id"]:
                await thread.get_partial_message(r["receipt_id"]).edit(embed=embed)
            else:
                msg = await thread.send(embed=embed)
                db.redemption_update(rid, receipt_id=msg.id)
        except discord.HTTPException as e:
            log.warning("ใบแลก RD-%s: %s", rid, e)
    log_channel = cfg.redeem_log or cfg.donate_log or cfg.mod_logs
    view = redeem_admin_view(r)
    log_embed = receipt_embed(r)
    log_embed.description = f"<@{r['discord_id']}>" + (f" · 🛒 ตะกร้าเว็บ C-{r['cart_id']:04d}" if r["cart_id"] else "")
    try:
        if r["log_id"] and guild.get_channel(log_channel):
            await guild.get_channel(log_channel).get_partial_message(r["log_id"]).edit(embed=log_embed, view=view)
        else:
            content = staff_ping(guild) if notify_staff and cfg.ping_staff_on_new else None
            kwargs = {"view": view} if view else {}
            msg = await log_to(guild, log_channel, log_embed, content=content,
                               allowed_mentions=discord.AllowedMentions(users=True), **kwargs)
            if msg:
                db.redemption_update(rid, log_id=msg.id)
    except discord.HTTPException as e:
        log.warning("log ใบแลก RD-%s: %s", rid, e)
    board_dirty()


# ---------------------------------------------------------------- ส่งเข้าเกมผ่าน Cookie Express relay

JOB_DONE = ("claimed", "cancelled")
JOB_IN_FLIGHT = ("posting", "sent", "inqueue", "seen", "partial")
_job_locks: dict = {}


def job_lock(job_id: int) -> asyncio.Lock:
    return _job_locks.setdefault(job_id, asyncio.Lock())


async def ckx_post(job_id: int) -> bool:
    """โพสต์คำสั่ง ckx ให้ relay — กันส่งซ้ำ (relay แยกออเดอร์ตาม id ข้อความ ส่งซ้ำ = ได้ของซ้ำ)
    ใช้ lock เดียวกับ ckx_cancel: ยกเลิกระหว่างกำลังส่งจะรอให้ส่งเสร็จแล้วค่อยยกเลิกข้อความนั้น"""
    async with job_lock(job_id):
        return await _ckx_post(job_id)


async def _ckx_post(job_id: int) -> bool:
    job = db.job_get(job_id)
    if job is None or job["status"] != "posting":
        return True
    guild = bot.get_guild(cfg.guild_id)
    channel = guild.get_channel(cfg.ckx_channel) if guild and cfg.ckx_channel else None
    if channel is None:
        log.warning("ยังส่งคำสั่ง Cookie Express ไม่ได้ (ตั้ง CKX_CHANNEL_ID / บอทมองไม่เห็นห้อง) — งาน #%s รอไว้", job_id)
        return False
    note = (f"rd-{job['ref_id']}" if job["kind"] == "redeem" else f"donate-{job['ref_id']}")
    try:
        cmd = ckx_link.build_command(job["ingame"], job["items"], note)
        # nonce: Discord ไม่สร้างข้อความซ้ำถ้าส่งซ้ำด้วย nonce เดิม (กันตอน 5xx แล้วลองใหม่)
        msg = await channel.send(cmd, allowed_mentions=discord.AllowedMentions.none(), nonce=f"ckx{job_id}")
    except ValueError as e:
        db.job_update(job_id, status="failed", info=str(e))
        await job_changed(job_id)
        return False
    except discord.HTTPException as e:
        log.warning("ส่งคำสั่ง Cookie Express ไม่ได้: %s", e)
        return False
    db.job_update(job_id, msg_id=msg.id, status="sent")
    await job_changed(job_id)
    return True


async def ckx_cancel(job_id: int) -> bool:
    """ยกเลิกงานที่ผู้เล่นยังไม่ได้รับ — False = รับไปแล้ว (บางส่วน) ยกเลิกไม่ได้"""
    async with job_lock(job_id):
        job = db.job_get(job_id)
        if job is None or job["status"] == "cancelled":
            return True
        if job["lines_done"] > 0 or job["status"] in ("claimed", "partial"):
            return False
        if job["msg_id"]:
            guild = bot.get_guild(cfg.guild_id)
            channel = guild.get_channel(cfg.ckx_channel) if guild and cfg.ckx_channel else None
            if channel is None:
                return False
            try:
                await channel.send(f"ckx cancel dc-{job['msg_id']}", allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException as e:
                log.warning("ส่งคำสั่งยกเลิกไม่ได้: %s", e)
                return False
        db.job_update(job_id, status="cancelled")
        return True


async def on_ckx_message(message: discord.Message):
    if message.author.id == bot.user.id:
        return
    if cfg.ckx_relay_bot:
        if message.author.id != cfg.ckx_relay_bot:
            return
    elif not message.author.bot:  # ไม่ได้ตั้ง CKX_RELAY_BOT_ID → เชื่อเฉพาะบอท (คนพิมพ์ปลอมไม่ได้)
        return
    if not db.relay_mark(message.id):
        return
    ref = message.reference.message_id if message.reference else None
    for kind, msg_id, line in ckx_link.parse_relay(message.content, is_reply=bool(ref)):
        job = db.job_by_msg(msg_id or ref)
        if job is not None:
            await apply_job_event(job, kind, line)
    if message.id > int(db.setting("ckx:last", "0") or 0):
        db.set_setting("ckx:last", message.id)


async def ckx_catch_up():
    """บอทปิดอยู่ (เช่น Railway deploy) แล้ว relay ตอบมา → อ่านย้อนหลังต่อจากข้อความล่าสุดที่อ่านแล้ว"""
    guild = bot.get_guild(cfg.guild_id)
    channel = guild.get_channel(cfg.ckx_channel) if guild and cfg.ckx_channel else None
    last = int(db.setting("ckx:last", "0") or 0)
    if channel is None or not last:
        return
    n = 0
    async for message in channel.history(after=discord.Object(id=last), oldest_first=True, limit=500):
        await on_ckx_message(message)
        n += 1
    db.relay_prune()
    if n:
        log.info("อ่านข้อความ relay ย้อนหลัง %d ข้อความ", n)


async def apply_job_event(job, kind: str, line: str):
    async with job_lock(job["id"]):
        await _apply_job_event(db.job_get(job["id"]), kind, line)


async def _apply_job_event(job, kind: str, line: str):
    status, done, info = job["status"], job["lines_done"], job["info"]
    if kind == "queued":
        if status in ("posting", "sent"):
            status = "inqueue"
    elif kind == "error":
        status, info = "failed", line
    elif kind == "seen":
        if status in ("posting", "sent", "inqueue"):
            status = "seen"
    elif kind == "claimed":
        done = min(done + 1, job["lines_total"])
        status = "claimed" if done >= job["lines_total"] else "partial"
    elif kind == "undo":
        done = max(0, done - 1)
        status = "partial" if done else "inqueue"
    elif kind in ("rejected", "short"):
        status, info = "problem", line
    elif kind == "vehicle":
        info = line
    elif kind == "cancelled":
        status = "cancelled"
    else:
        return
    db.job_update(job["id"], status=status, lines_done=done, info=trunc(info, 500))
    await job_changed(job["id"])


async def job_changed(job_id: int):
    job = db.job_get(job_id)
    guild = bot.get_guild(cfg.guild_id)
    if job["kind"] == "redeem":
        r = db.redemption_get(job["ref_id"])
        if r is not None and r["status"] == "refunded" and job["lines_done"] > 0 and "[alert]" not in job["info"]:
            db.job_update(job_id, info=(job["info"] + " [alert]").strip())
            await log_to(guild, cfg.redeem_log or cfg.donate_log or cfg.mod_logs, discord.Embed(
                color=COLOR_BAD, description=f"⚠️ `RD-{r['id']:04d}` <@{r['discord_id']}> **คืนคุกกี้ไปแล้ว แต่รับของในเกม"
                                             f"ไปแล้วด้วย** ({r['name']} × {r['qty']}) — หักคุกกี้คืนด้วย /cookies take "
                                             f"ถ้าต้องการ"), content=staff_ping(guild) or None,
                allowed_mentions=discord.AllowedMentions(users=True))
            return
        if r is None or r["job_id"] != job_id or r["status"] in ("refunded", "done"):
            return
        note = ""
        if job["status"] in ("failed", "problem") and job["info"]:
            note = job["info"]
        db.redemption_update(r["id"], status=job["status"], note=note)
        if job["status"] in ("failed", "cancelled") and job["lines_done"] == 0:
            db.refund(r["id"], note=f"ส่งไม่สำเร็จ คืนอัตโนมัติ RD-{r['id']:04d}")
        await redemption_changed(guild, r["id"], notify_staff=job["status"] == "problem")
        await refresh_wallet(guild, r["discord_id"])
    elif job["kind"] == "donate":
        order = db.order_get(job["ref_id"])
        if order is not None and order["job_id"] == job_id:
            if order["status"] == "paid" and auto_done(order):
                db.order_update(order["id"], status="delivered", delivered_by=guild.me.id if guild else None,
                                delivered_at=datetime.now(timezone.utc).isoformat())
            await update_paid_card(guild, order["id"])
            if job["status"] in ("failed", "problem"):
                await log_to(guild, cfg.donate_log or cfg.mod_logs, discord.Embed(
                    color=COLOR_BAD, description=f"⚠️ ส่งของ Donate #{order['id']:04d} เข้าเกมไม่สำเร็จ "
                                                 f"<@{order['owner_id']}> — {trunc(job['info'], 300)}\n"
                                                 f"ห้อง: <#{order['thread_id']}> · ส่งเองแล้วกด 📦"),
                             content=staff_ping(guild) if cfg.ping_staff_on_new else None,
                             allowed_mentions=discord.AllowedMentions(users=True))
    board_dirty()


async def ckx_retry_loop():
    await bot.wait_until_ready()
    try:
        await ckx_catch_up()
    except Exception:  # noqa: BLE001
        log.exception("อ่านข้อความ relay ย้อนหลังไม่สำเร็จ")
    while not bot.is_closed():
        try:
            for job in db.jobs_unsent():
                if not await ckx_post(job["id"]):
                    break
                await asyncio.sleep(1)
        except Exception:  # noqa: BLE001
            log.exception("ส่งคำสั่ง Cookie Express ซ้ำพัง")
        await asyncio.sleep(60)


# ---------------------------------------------------------------- ป้ายร้านในห้อง #redeem

class ShopPanelView(BaseLayout):
    def __init__(self):
        super().__init__(timeout=None)
        if web_shop_on():
            shop = web_shop_button()
        else:
            shop = ui.Button(label="เปิดร้าน", emoji="🛒", style=discord.ButtonStyle.success, custom_id="cc:shop:open")
            shop.callback = open_shop
        wallet = ui.Button(label="กระเป๋าของฉัน", emoji="👛", style=discord.ButtonStyle.secondary,
                           custom_id="cc:wallet:open")
        wallet.callback = open_wallet
        topup = ui.Button(label="เติมคุกกี้", emoji="💝", style=discord.ButtonStyle.secondary, custom_id="cc:shop:topup")
        topup.callback = start_donate_ticket
        row = [shop, wallet] + ([topup] if cfg.donate_enabled else [])
        if cfg.public_url and cfg.web_enabled and not web_shop_on():
            row.append(ui.Button(label="แคตตาล็อก", emoji="🌐", url=cfg.public_url + "/"))
        rate = int(db.setting("cookie_rate", "0") or 0)
        ways = [f"🎡 หมุนวงล้อรายวันที่ {fill_placeholders('{spin}')}"]
        if cfg.donate_enabled:
            ways.append("💝 Donate: เติมตามยอด" + (f" (1 บาท = {fmt_cookies(rate)})" if rate else "")
                        + " หรือเลือกแพ็กคุกกี้")
        self.add_item(ui.Container(
            ui.TextDisplay("## 🛍️ Cookie Shop\nเอาคุกกี้ 🍪 มาแลกของในเกม — ของส่งเข้าเกมให้เองผ่านคุกกี้ส่งของ "
                           "เข้าเกมแล้วกดรับที่ปุ่มบ้านคุกกี้ได้เลย"),
            ui.Separator(),
            ui.TextDisplay("**หาคุกกี้ได้จาก**\n" + "\n".join(ways)),
            ui.ActionRow(*row),
            accent_colour=COLOR_DONATE))


def web_shop_on() -> bool:
    """ล็อกอิน Discord + แลกของบนเว็บ (ต้องมีโดเมน https และ DISCORD_CLIENT_SECRET)"""
    secure = cfg.public_url.startswith("https://") or cfg.public_url.startswith("http://localhost")
    return bool(cfg.web_enabled and secure and cfg.discord_client_secret)


def _local_input(iso: str) -> str:
    """ISO (UTC) → '2026-10-25T18:00' เวลาไทย สำหรับช่อง datetime-local"""
    return datetime.fromisoformat(iso).astimezone(TZ).strftime("%Y-%m-%dT%H:%M") if iso else ""


def web_item(i, now: datetime) -> dict:
    """ของ 1 ชิ้นสำหรับหน้าเว็บ (ใช้กรอง/เรียงฝั่งเว็บด้วย)"""
    state = item_state(i, now)
    return {
        "code": i["code"], "name": i["name"], "description": i["description"], "price": i["price"],
        "category": i["category"], "limit": i["per_user_limit"], "ckx": bool(i["ckx"]),
        "stock": i["stock"] if i["stock"] >= 0 else None, "state": state, "active": bool(i["active"]),
        "image_url": f"/img/{i['image']}?v={_ts(i['updated_at']) or 0}" if i["image"] else "",
        "start": datetime.fromisoformat(i["start_at"]).astimezone(TZ) if i["start_at"] else None,
        "end": datetime.fromisoformat(i["end_at"]).astimezone(TZ) if i["end_at"] else None,
        "end_ts": _ts(i["end_at"]) if i["end_at"] else 0, "updated_ts": _ts(i["updated_at"]) or 0,
        "sort": i["sort"],
    }


def web_page_data():
    now = datetime.now(timezone.utc)
    items = [web_item(i, now) for i in db.shop_items() if item_state(i, now) != "ended"]
    custom_sub = db.setting("web:subtitle") or ""
    meta = {"title": db.setting("web:title") or "Cookie Shop",
            "subtitle": custom_sub or "แลกของในเกมด้วยคุกกี้ 🍪 จากวงล้อรายวันและการ Donate · กดแลกได้ในดิสคอร์ด",
            "subtitle_login": custom_sub or "ล็อกอินด้วย Discord เพื่อดูคุกกี้ของคุณ แล้วเลือกของใส่ตะกร้าแลกได้เลย 🍪",
            "subtitle_user": custom_sub or "เลือกของใส่ตะกร้า แล้วกดยืนยันแลกได้เลย — สรุปจะไปอยู่ในกระเป๋าคุกกี้บน Discord",
            "subtitle_raw": custom_sub, "notice": db.setting("web:notice") or "",
            "cat_info": web_cat_info(),
            "redeem_url": channel_link(cfg.redeem_channel) or "",
            "invite_url": cfg.invite_url, "discord_url": channel_link(cfg.redeem_channel) or "",
            "footer": f"Cookie Cheetah · อัปเดต {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}",
            "site": web_site.load(db.setting("web:site")), "site_rev": site_rev(), "spin_url": channel_link(cfg.spin_channel) or "",
            "support_url": channel_link(cfg.ticket_channel) or "", "donate_on": bool(cfg.donate_enabled and stripe)}
    return items, meta


def web_cat_info() -> dict:
    """คำอธิบายหมวด (แก้บนเว็บ) {ชื่อหมวด: ข้อความ}"""
    try:
        data = json.loads(db.setting("web:catinfo") or "{}")
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def sniff_image(data: bytes) -> Optional[str]:
    """ดูจากเนื้อไฟล์จริง ไม่เชื่อนามสกุล"""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def write_item_image(code: str, ext: str, data: bytes) -> str:
    """ชื่อไฟล์ไม่ซ้ำทุกครั้ง (ของเปลี่ยนรหัสแล้วมีของใหม่ใช้รหัสเดิม → ไม่ทับรูปกัน) · ลบรูปเก่าที่ผู้เรียก"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", code).lower()
    name = f"{safe}-{secrets.token_hex(4)}.{ext}"
    tmp = IMAGES_DIR / f".{name}.tmp"
    tmp.write_bytes(data)
    tmp.replace(IMAGES_DIR / name)
    return name


def drop_item_image(name: str):
    if name and re.fullmatch(r"[A-Za-z0-9_\-]{1,40}\.(png|jpg|jpeg|webp|gif)", name):
        (IMAGES_DIR / name).unlink(missing_ok=True)


WEB_CART_LINES = 20
NONCE_RE = re.compile(r"^[A-Za-z0-9_\-.]{8,64}$")
_cart_locks: dict = {}
_cart_receipt_locks: dict = {}
_bg_tasks: set = set()


def cart_lock(uid: int) -> asyncio.Lock:
    return _cart_locks.setdefault(uid, asyncio.Lock())


def spawn(coro, what: str):
    """งานเบื้องหลัง (เก็บ reference ไว้ไม่ให้โดนเก็บขยะ + log ถ้าพัง)"""
    async def run():
        try:
            await coro
        except Exception:  # noqa: BLE001
            log.exception("งานเบื้องหลังพัง: %s", what)
    task = asyncio.create_task(run())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return task


def redeem_cap(item, uid: int) -> int:
    """แลกชิ้นนี้ได้อีกสูงสุดกี่ชิ้น (ยังไม่นับคุกกี้)"""
    limit = MAX_REDEEM_QTY
    if item["per_user_limit"]:
        limit = min(limit, item["per_user_limit"] - db.redeemed_qty(uid, item["code"]))
    if item["stock"] >= 0:
        limit = min(limit, item["stock"])
    if item["ckx"]:  # จำนวนต่อรหัสในคำสั่งเดียวต้องไม่เกิน 999
        try:
            limit = min(limit, ckx_link.MAX_COUNT // max(1, ckx_link.max_count(item["ckx"])))
        except ValueError:
            return 0
    return max(0, limit)


def can_redeem(member) -> tuple:
    if is_staff(member) or has_role(member, cfg.survivor_role):
        return True, ""
    role = member.guild.get_role(cfg.survivor_role) if getattr(member, "guild", None) else None
    name = role.name if role else "คุกกี้"
    return False, f"ต้องได้ role {name} ก่อน (ขอ White List ในดิส) ถึงจะแลกของได้"


def redemption_brief(r) -> dict:
    icon, text = REDEEM_STATUS.get(r["status"], ("•", r["status"]))
    return {"rid": f"RD-{r['id']:04d}", "name": r["name"], "qty": r["qty"], "cost": r["price"] * r["qty"],
            "icon": icon, "status": text, "key": r["status"], "cart": f"C-{r['cart_id']:04d}" if r["cart_id"] else None}


def cart_summary(cart_id: int) -> dict:
    cart = db.cart_get(cart_id)
    lines = db.cart_lines(cart_id)
    return {"id": cart_id, "label": f"C-{cart_id:04d}", "total": cart["total"],
            "has_ckx": any(r["ckx"] for r in lines), "lines": [redemption_brief(r) for r in lines]}


# ---------------------------------------------------------------- Donate บนเว็บ (ใช้ระบบออเดอร์เดียวกับห้อง Donate)

DONATE_STATUS_WEB = {"cart": "ยังไม่ส่ง", "review": "รอยืนยัน", "pending": "รอชำระเงิน", "expired": "บิลหมดอายุ",
                     "paid": "ได้รับยอดแล้ว · กำลังส่งของ", "delivered": "ส่งของครบแล้ว", "cancelled": "ยกเลิกแล้ว"}
DONATE_STEP = {"review": 1, "pending": 1, "expired": 1, "paid": 2, "delivered": 3}
DONATE_TOPUP_MAX = 100_000  # บาท ต่อรอบ (เท่ากับในห้อง Donate)
_donate_checked: dict = {}
_site_lock = asyncio.Lock()


def site_rev() -> str:
    """เลขรุ่นของการตั้งค่าหน้าเว็บ (กันแก้ทับกันจากสองหน้าต่าง)"""
    return hashlib.sha1((db.setting("web:site") or "").encode()).hexdigest()[:12]


def donate_rate() -> int:
    try:
        return max(0, int(db.setting("cookie_rate", "0") or 0))
    except ValueError:
        return 0


def donate_item_web(i) -> dict:
    kind = "pack" if i["cookies"] else ("game" if i["ckx"] else "manual")
    image = i["image"] if "image" in i.keys() else ""
    return {"code": i["code"], "name": i["name"], "description": i["description"], "price": i["price"],
            "cookies": i["cookies"], "ckx": bool(i["ckx"]), "kind": kind, "active": bool(i["active"]),
            "image_url": f"/img/{image}?v={_ts(i['updated_at']) or 0}" if image else ""}


def donate_progress(order, lines: list) -> list:
    """สถานะส่งของแบบอ่านง่ายบนเว็บ [{k: ok|wait|bad, t: ข้อความ}] (คู่กับ delivery_text ในดิส)"""
    out, delivered = [], order["status"] == "delivered"
    cookies = sum(int(line.get("cookies") or 0) * int(line["qty"]) for line in lines)
    if cookies:
        out.append({"k": "ok", "t": f"เติม {cookies:,} คุกกี้เข้ากระเป๋าแล้ว"} if order["cookies_given"]
                   else {"k": "wait", "t": f"รอเติม {cookies:,} คุกกี้"})
    if order_ckx_lines(lines):
        job = db.job_get(order["job_id"]) if order["job_id"] else None
        if job is not None and job["status"] == "claimed":
            out.append({"k": "ok", "t": f"ของในเกม: รับในเกมแล้ว (ชื่อ {job['ingame']})"})
        elif delivered:
            out.append({"k": "ok", "t": "ของในเกม: แอดมินยืนยันส่งแล้ว"})
        elif job is None:
            out.append({"k": "wait", "t": "รอใส่ชื่อในเกมเพื่อส่งของ (กดในห้อง Donate บน Discord)"})
        else:
            _, text = REDEEM_STATUS.get(job["status"], ("", job["status"]))
            bad = job["status"] in ("failed", "problem", "cancelled")
            out.append({"k": "bad" if bad else "wait",
                        "t": f"ของในเกม: {text} (ชื่อ {job['ingame']})" + (" — แอดมินจะส่งให้เอง" if bad else "")})
    manual = order_manual_lines(lines)
    if manual:
        names = ", ".join(f"{line['name']} × {line['qty']}" for line in manual)
        out.append({"k": "ok", "t": f"แอดมินส่งแล้ว: {names}"} if delivered
                   else {"k": "wait", "t": f"รอแอดมินส่งในเกม: {names}"})
    return out or [{"k": "ok" if delivered else "wait", "t": "ส่งของครบแล้ว" if delivered else "รอแอดมินส่งของ"}]


def donate_brief(order) -> dict:
    """ออเดอร์ 1 รายการสำหรับหน้าเว็บ (ของเจ้าของเท่านั้น)"""
    lines = lines_of(order)
    status = order["status"]
    live = status == "pending" and (order["stripe_expires"] or 0) > time.time() + 30
    url = order["stripe_url"] or ""
    ckx = bool(order_ckx_lines(lines))
    ingame = order_ingame(order) if ckx else ""
    actions = {"review": ["pay", "cancel"], "pending": (["pay"] if live else []) + ["check", "cancel"],
               "expired": ["renew", "cancel"]}.get(status, [])
    return {"id": order["id"], "label": f"#{order['id']:04d}", "status": status,
            "text": DONATE_STATUS_WEB.get(status, status), "step": DONATE_STEP.get(status, 0),
            "lines": [{"code": line["code"], "name": line["name"], "qty": line["qty"], "unit": line["unit"]}
                      for line in lines],
            "total": order["total"] or cart_total(lines), "created": _ts(order["created_at"]) or 0,
            "paid": _ts(order["paid_at"]) or 0, "expires": order["stripe_expires"] if live else 0,
            "pay_url": url if live and url.startswith("https://checkout.stripe.com/") else "",
            "thread_url": channel_link(order["thread_id"]) or "", "web": bool(order["web_nonce"]),
            "progress": donate_progress(order, lines) if status in ("paid", "delivered") else [],
            "ckx": ckx, "ingame": ingame, "needs_name": ckx and not ckx_link.valid_ingame(ingame),
            "actions": actions}


class WebShop:
    """ข้อมูลที่ web_catalog ใช้ — แยกออกมาให้ทดสอบหน้าเว็บได้โดยไม่ต้องมี Discord จริง"""

    @staticmethod
    def login_enabled() -> bool:
        return web_shop_on()

    @property
    def secure(self) -> bool:
        return cfg.public_url.startswith("https://")

    @property
    def public_url(self) -> str:
        return cfg.public_url

    @property
    def client_secret(self) -> str:
        return cfg.discord_client_secret

    @staticmethod
    def client_id() -> str:
        return cfg.discord_client_id or str(bot.application_id or "")

    @staticmethod
    def redirect_uri() -> str:
        return cfg.public_url + "/auth/callback"

    @staticmethod
    def secret() -> bytes:
        value = db.setting("web:secret")
        if not value:
            value = secrets.token_hex(32)
            db.set_setting("web:secret", value)
        return value.encode()

    @staticmethod
    def session_version(uid: int) -> int:
        return int(db.setting(f"web:sv:{uid}", "0") or 0)

    @staticmethod
    def end_sessions(uid: int):
        """ออกจากระบบ = session ทุกเครื่องของคนนี้ใช้ไม่ได้"""
        db.set_setting(f"web:sv:{uid}", int(db.setting(f"web:sv:{uid}", "0") or 0) + 1)

    @staticmethod
    def is_editor(member) -> bool:
        """แก้ร้านบนเว็บได้ไหม: WEB_EDITOR_IDS · ไม่ตั้ง = เจ้าของเซิฟ Discord คนเดียว"""
        if member is None:
            return False
        if cfg.web_editor_ids:
            return member.id in cfg.web_editor_ids
        owner = getattr(getattr(member, "guild", None), "owner_id", None)
        return owner is not None and member.id == owner

    @staticmethod
    def admin_catalog() -> list:
        """ของทุกชิ้น (รวมที่ซ่อน/หมดเวลา) + ค่าดิบสำหรับฟอร์มแก้ — ส่งให้คนแก้ร้านเท่านั้น"""
        now = datetime.now(timezone.utc)
        out = []
        for i in db.shop_items(active_only=False):
            d = web_item(i, now)
            d["raw"] = {"code": i["code"], "name": i["name"], "description": i["description"], "price": i["price"],
                        "ckx": (i["ckx"] or "").replace(";", " "), "category": i["category"],
                        "limit": i["per_user_limit"], "stock": i["stock"], "start": _local_input(i["start_at"]),
                        "end": _local_input(i["end_at"]), "active": bool(i["active"]), "sort": i["sort"],
                        "image_url": d["image_url"]}
            out.append(d)
        return out

    @staticmethod
    def catalog() -> list:
        return web_page_data()[0]

    @staticmethod
    def page_meta() -> dict:
        return web_page_data()[1]

    @staticmethod
    def item_map() -> dict:
        now = datetime.now(timezone.utc)
        return {i["code"]: {"name": i["name"], "price": i["price"], "ckx": bool(i["ckx"])}
                for i in db.shop_items() if item_state(i, now) in ("open", "hot")}

    async def oauth_user(self, code: str) -> dict:
        data = {"client_id": self.client_id(), "client_secret": cfg.discord_client_secret,
                "grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri()}
        timeout = aiohttp.ClientTimeout(total=15)
        async with bot.session.post("https://discord.com/api/v10/oauth2/token", data=data, timeout=timeout) as r:
            if r.status != 200:
                raise RuntimeError(f"แลก code ไม่ผ่าน ({r.status}): {(await r.text())[:200]}")
            token = (await r.json())["access_token"]
        async with bot.session.get("https://discord.com/api/v10/users/@me", timeout=timeout,
                                   headers={"Authorization": f"Bearer {token}"}) as r:
            if r.status != 200:
                raise RuntimeError(f"อ่านบัญชี Discord ไม่ได้ ({r.status})")
            return await r.json()

    @staticmethod
    async def member(uid: int):
        """คนนี้อยู่ในเซิฟไหม — None = ไม่อยู่ · Discord ล่มชั่วคราวจะโยน HTTPException"""
        guild = bot.get_guild(cfg.guild_id)
        if guild is None:
            raise RuntimeError("บอทยังไม่พร้อม")
        member = guild.get_member(uid)
        if member is None:
            try:
                member = await guild.fetch_member(uid)
            except discord.NotFound:
                return None
        return None if member.bot else member

    async def me(self, uid: int) -> dict:
        member = await self.member(uid)
        if member is None:
            return {"member": False}
        w = db.wallet_ensure(uid)
        ok, why_not = can_redeem(member)
        now = datetime.now(timezone.utc)
        caps, why = {}, {}
        for item in db.shop_items():
            state = item_state(item, now)
            if state not in ("open", "hot"):
                continue
            n = redeem_cap(item, uid)
            caps[item["code"]] = n
            if n < 1:
                why[item["code"]] = ("ครบสิทธิ์แล้ว" if item["per_user_limit"] and
                                     db.redeemed_qty(uid, item["code"]) >= item["per_user_limit"] else "หมดแล้ว")
        wallet_url = (f"https://discord.com/channels/{cfg.guild_id}/{w['thread_id']}" if w["thread_id"]
                      else channel_link(cfg.spin_channel) or "")
        spin = db.spin_today(uid, today_key())
        return {"member": True, "id": str(uid), "name": member.display_name, "editor": self.is_editor(member),
                "stats": db.redeem_stats(uid), "spin_today": spin["cookies"] if spin else None,
                "spin_url": channel_link(cfg.spin_channel) or "",
                "avatar": str(member.display_avatar.url) if getattr(member, "display_avatar", None) else "",
                "balance": w["balance"], "ingame": w["ingame"] or "", "can_redeem": ok, "reason": why_not,
                "caps": caps, "why": why, "wallet_url": wallet_url,
                "recent": [redemption_brief(r) for r in db.redemptions_of(uid, 8)]}

    async def checkout(self, uid: int, data) -> tuple:
        """แลกทั้งตะกร้า — คืน (HTTP status, JSON)"""
        def fail(status, msg, code="bad", **extra):
            return status, {"ok": False, "error": msg, "code": code, **extra}

        if not isinstance(data, dict):
            return fail(400, "ข้อมูลไม่ถูกต้อง")
        nonce = str(data.get("nonce") or "")
        if not NONCE_RE.fullmatch(nonce):
            return fail(400, "ข้อมูลไม่ถูกต้อง รีเฟรชหน้าแล้วลองใหม่")
        raw = data.get("items")
        if not isinstance(raw, list) or not raw:
            return fail(400, "ตะกร้าว่าง")
        wanted: list = []
        for line in raw:
            if not isinstance(line, dict):
                return fail(400, "ข้อมูลไม่ถูกต้อง")
            code, qty = str(line.get("code") or "").strip(), line.get("qty")
            if not code or isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= MAX_REDEEM_QTY:
                return fail(400, "จำนวนไม่ถูกต้อง")
            wanted.append((code, qty))
        if len(wanted) > WEB_CART_LINES:
            return fail(400, f"ตะกร้าใส่ได้สูงสุด {WEB_CART_LINES} รายการ")
        ingame = str(data.get("ingame") or "").strip()
        expected = data.get("expected_total")

        async with cart_lock(uid):
            old = db.cart_by_nonce(uid, nonce)
            if old is not None:  # กดซ้ำ / เน็ตหลุดแล้วส่งใหม่ → คืนผลเดิม ไม่หักซ้ำ
                return await self._done(uid, old["id"], replay=True)
            member = await self.member(uid)
            if member is None:
                return fail(401, "บัญชีนี้ไม่ได้อยู่ในเซิฟ Discord แล้ว", "login")
            ok, why_not = can_redeem(member)
            if not ok:
                return fail(403, why_not, "role")
            items, merged, gone = {}, {}, []
            for code, qty in wanted:  # รวมตามรหัสจริงในร้าน (ตัวพิมพ์เล็ก/ใหญ่ไม่มีผล)
                item = db.shop_get(code)
                if item is None:
                    gone.append(code)
                    continue
                items[item["code"]] = item
                merged[item["code"]] = merged.get(item["code"], 0) + qty
            if gone:
                return fail(409, f"ไม่มีของ {', '.join(gone)} ในร้านแล้ว", "changed",
                            state=await self.me(uid), items=self.item_map())
            total = sum(items[c]["price"] * q for c, q in merged.items())
            if isinstance(expected, int) and not isinstance(expected, bool) and expected != total:
                return fail(409, "ราคาในร้านเพิ่งเปลี่ยน ดูยอดใหม่แล้วกดยืนยันอีกครั้ง", "changed",
                            state=await self.me(uid), items=self.item_map())
            now = datetime.now(timezone.utc)
            for code, qty in merged.items():
                problem = shop_problem(items[code], now)
                cap = redeem_cap(items[code], uid)
                if problem or qty > cap:
                    msg = problem or ("แลกไม่ได้แล้ว" if cap < 1 else f"แลกได้อีกแค่ {cap} ชิ้น")
                    return fail(409, f"{items[code]['name']}: {msg}", "rejected",
                                state=await self.me(uid), items=self.item_map())
            needs_name = any(items[c]["ckx"] for c in merged)
            if needs_name and not ckx_link.valid_ingame(ingame):
                return fail(400, "ใส่ชื่อในเกมที่จะรับของ (ห้ามมี \" | ` และยาวไม่เกิน 40 ตัว)", "ingame")
            if not ckx_link.valid_ingame(ingame):
                ingame = ""
            ckx_items = {}
            for code, qty in merged.items():
                if not items[code]["ckx"]:
                    continue
                try:
                    ckx_items[code] = ckx_link.normalize_items(items[code]["ckx"], multiply=qty)
                except ValueError as e:  # จำนวนผ่าน redeem_cap แล้ว → เหลือแค่รหัสในร้านตั้งผิดจริง
                    guild = bot.get_guild(cfg.guild_id)
                    await mod_log(guild, f"❌ ร้านคุกกี้: รหัสของ `{code}` ผิด ({e})", COLOR_BAD)
                    return fail(409, f"{items[code]['name']} ตั้งค่าผิด แจ้งแอดมินแล้ว เอาออกจากตะกร้าก่อนนะ",
                                "broken")
            cart_id, rids, err = db.redeem_cart(uid, list(merged.items()), ingame, now, nonce, ckx_items)
            if err == "dup":
                old = db.cart_by_nonce(uid, nonce)
                if old is not None:
                    return await self._done(uid, old["id"], replay=True)
                return fail(409, "แลกซ้ำ ลองใหม่อีกครั้ง", "rejected")
            if err:
                return fail(409, err, "rejected", state=await self.me(uid), items=self.item_map())
            log.info("เว็บ: %s แลกตะกร้า C-%04d (%d รายการ, %d คุกกี้)", uid, cart_id, len(rids), total)
            spawn(cart_after_checkout(cart_id), f"ตะกร้า C-{cart_id:04d}")
        return await self._done(uid, cart_id)

    async def _done(self, uid: int, cart_id: int, replay: bool = False) -> tuple:
        """ตอบว่าแลกสำเร็จ — ถ้าดึงข้อมูล Discord ไม่ได้ตอนนี้ก็ยังตอบสำเร็จ (ของถูกหักไปแล้ว)"""
        try:
            state = await self.me(uid)
        except Exception as e:  # noqa: BLE001
            log.warning("เว็บ: ดึงยอดหลังแลกไม่ได้: %s", e)
            state = None
        body = {"ok": True, "cart": cart_summary(cart_id), "state": state, "items": self.item_map()}
        if replay:
            body["replay"] = True
        return 200, body


    # ---------------- แก้ร้านบนเว็บ (เฉพาะคนแก้ร้าน) ----------------
    async def _editor(self, uid: int):
        member = await self.member(uid)
        return member if self.is_editor(member) else None

    async def is_editor_uid(self, uid: int) -> bool:
        """เช็คก่อนรับไฟล์อัปโหลด (ไม่ให้คนอื่นส่งไฟล์ใหญ่มาให้เซิฟอ่าน)"""
        try:
            return await self._editor(uid) is not None
        except discord.HTTPException:
            return False

    async def admin_save(self, uid: int, data: dict, image: Optional[bytes], remove_image: bool) -> tuple:
        def fail(status, msg):
            return status, {"ok": False, "error": msg}

        member = await self._editor(uid)
        if member is None:
            return fail(403, "บัญชีนี้แก้ร้านไม่ได้")
        original = str(data.get("original") or "").strip()
        item = db.shop_get(original) if original else None
        if original and item is None:
            return fail(404, f"ไม่พบ {original} แล้ว (อาจถูกลบไป) รีเฟรชหน้า")
        code = str(data.get("code") or "").strip()
        if not ITEM_CODE_RE.fullmatch(code):
            return fail(400, "รหัสของใช้ได้แค่อังกฤษ ตัวเลข _ - ยาวไม่เกิน 20 ตัว")
        clash = db.shop_get(code)
        if clash and (item is None or clash["code"].casefold() != item["code"].casefold()):
            return fail(409, f"รหัส {code} มีของอื่นใช้อยู่แล้ว")
        name = str(data.get("name") or "").strip()
        if not name:
            return fail(400, "ใส่ชื่อของ")

        def num(key, lo, hi, default):
            raw = str(data.get(key, "")).strip()
            if raw == "":
                return default
            try:
                v = int(raw)
            except ValueError:
                raise ValueError(key)
            if not lo <= v <= hi:
                raise ValueError(key)
            return v

        labels = {"price": "ราคา (1–100,000,000)", "limit": "จำกัดต่อคน (0–999)", "stock": "สต็อก (-1–1,000,000)",
                  "sort": "ลำดับ"}
        try:
            price = num("price", 1, 100_000_000, None)
            limit = num("limit", 0, 999, 0)
            stock = num("stock", -1, 1_000_000, -1)
            sort = num("sort", -100_000, 100_000, 0)
        except ValueError as e:
            return fail(400, f"ช่อง {labels.get(str(e), str(e))} ไม่ถูกต้อง")
        if price is None:
            return fail(400, "ใส่ราคา (คุกกี้)")
        ckx_text = str(data.get("ckx") or "").strip()
        try:
            ckx = ckx_link.normalize_items(ckx_text) if ckx_text else ""
        except ValueError as e:
            return fail(400, str(e))
        try:
            start_at = parse_when(str(data.get("start") or "").replace("T", " "))
            end_at = parse_when(str(data.get("end") or "").replace("T", " "), end=True)
        except app_commands.AppCommandError as e:
            return fail(400, str(e))
        if start_at and end_at and end_at <= start_at:
            return fail(400, "เวลาจบต้องหลังเวลาเริ่ม")
        active = str(data.get("active", "1")).lower() in ("1", "true", "on", "yes")
        image_name = None
        if image:
            if len(image) > 8 * 1024 * 1024:
                return fail(413, "รูปใหญ่เกิน 8 MB")
            ext = sniff_image(image)
            if ext is None:
                return fail(400, "รูปต้องเป็น png / jpg / webp / gif")
            image_name = write_item_image(code, ext, image)
        elif remove_image and item is not None and item["image"]:
            image_name = ""
        # รูปเก่าของของชิ้นนี้ ลบหลังบันทึกสำเร็จ (บันทึกพัง = ของไม่ชี้ไปไฟล์ที่หายไปแล้ว)
        old_image = item["image"] if image_name is not None and item is not None else ""
        fields = dict(name=trunc(name, 80), description=trunc(str(data.get("description") or "").strip(), 500),
                      price=price, ckx=ckx, category=trunc(str(data.get("category") or "").strip(), 40),
                      per_user_limit=limit, stock=stock, start_at=start_at.isoformat() if start_at else "",
                      end_at=end_at.isoformat() if end_at else "", active=int(active), sort=sort)
        loaded = str(data.get("stock_loaded", "")).strip()
        if item is not None and loaded and str(data.get("stock", "")).strip() == loaded:
            fields.pop("stock")  # ไม่ได้แก้ช่องสต็อก → ใช้ค่าจริงตอนนี้ (กันเขียนทับของที่เพิ่งมีคนแลกไป)
        if item is None:
            db.shop_add(code=code, image=image_name or "", **fields)
            verb = "เพิ่ม"
        else:  # เปลี่ยนรหัสแต่ไม่เปลี่ยนรูป → ใช้ไฟล์รูปเดิมต่อ (image=None = ไม่แตะ)
            db.shop_update(item["code"], code=code, image=image_name, **fields)
            verb = "แก้"
        if old_image:
            drop_item_image(old_image)
        guild = bot.get_guild(cfg.guild_id)
        await mod_log(guild, f"🛍️ {member.mention} {verb}ของในร้านผ่านเว็บ `{code}` {trunc(name, 80)} "
                             f"{fmt_cookies(price)}" + ("" if active else " (ซ่อน)"))
        log.info("เว็บ: %s %sของ %s", uid, verb, code)
        return 200, {"ok": True, "code": code}

    async def admin_delete(self, uid: int, data: dict) -> tuple:
        member = await self._editor(uid)
        if member is None:
            return 403, {"ok": False, "error": "บัญชีนี้แก้ร้านไม่ได้"}
        item = db.shop_get(str(data.get("code") or "").strip())
        if item is None or not db.shop_delete(item["code"]):
            return 404, {"ok": False, "error": "ไม่พบของนี้แล้ว"}
        drop_item_image(item["image"])
        await mod_log(bot.get_guild(cfg.guild_id),
                      f"🗑️ {member.mention} ลบของในร้านผ่านเว็บ `{item['code']}` {item['name']}")
        return 200, {"ok": True}

    async def admin_category(self, uid: int, data: dict) -> tuple:
        """คำอธิบายหมวด: บรรทัดขึ้นต้น ! = กล่องเตือนสีชมพู · * = กล่องข้อมูลสีเขียว"""
        member = await self._editor(uid)
        if member is None:
            return 403, {"ok": False, "error": "บัญชีนี้แก้ร้านไม่ได้"}
        name = str(data.get("name") or "").strip()
        if not name or name not in {i["category"] for i in db.shop_items(active_only=False) if i["category"]}:
            return 404, {"ok": False, "error": "ไม่มีหมวดนี้แล้ว"}
        info = web_cat_info()
        desc = trunc(str(data.get("desc") or "").strip(), 1500)
        if desc:
            info[name] = desc
        else:
            info.pop(name, None)
        db.set_setting("web:catinfo", json.dumps(info, ensure_ascii=False))
        await mod_log(bot.get_guild(cfg.guild_id), f"📝 {member.mention} แก้คำอธิบายหมวด {trunc(name, 40)} บนเว็บ")
        return 200, {"ok": True}

    async def admin_page(self, uid: int, data: dict) -> tuple:
        member = await self._editor(uid)
        if member is None:
            return 403, {"ok": False, "error": "บัญชีนี้แก้ร้านไม่ได้"}
        for key, n in (("title", 60), ("subtitle", 200), ("notice", 300)):
            value = trunc(str(data.get(key) or "").strip(), n)
            db.set_setting(f"web:{key}", value or None)
        await mod_log(bot.get_guild(cfg.guild_id), f"📝 {member.mention} แก้ข้อความหน้าเว็บร้าน")
        return 200, {"ok": True}

    @staticmethod
    def site() -> dict:
        return web_site.load(db.setting("web:site"))

    async def admin_site(self, uid: int, data: dict, files: dict, removes: set) -> tuple:
        """แก้หน้าเว็บ 1 ช่อง (โลโก้/ปุ่มลัด/แบนเนอร์/โปรโมต/รูปหมวด/ของตกแต่ง/ธีม/หัวหน้า Donate)
        files = {ช่องรูป: bytes} · removes = ช่องรูปที่จะลบ"""
        def fail(status, msg):
            return status, {"ok": False, "error": msg}

        member = await self._editor(uid)
        if member is None:
            return fail(403, "บัญชีนี้แก้หน้าเว็บไม่ได้")
        address, action = str(data.get("slot") or ""), str(data.get("action") or "save")
        try:
            slot, key = web_site.parse_address(address)
        except web_site.SiteError as e:
            return fail(400, str(e))
        if slot == "cats" and action == "save":
            names = {i["category"] for i in db.shop_items(active_only=False) if i["category"]}
            if key not in names:
                return fail(404, "ไม่มีหมวดนี้แล้ว")
        allowed = web_site.SLOTS[slot]["images"]
        rate = None
        raw_rate, loaded_rate = str(data.get("rate", "")).strip(), str(data.get("rate_loaded", "")).strip()
        if slot == "donate" and action == "save" and raw_rate != "" and raw_rate != loaded_rate:
            try:
                rate = int(str(data["rate"]).strip())
            except ValueError:
                rate = -1
            if not 0 <= rate <= 1_000_000:
                return fail(400, "เรตเติมคุกกี้ต้องเป็น 0–1,000,000 (0 = ปิด)")
        written, images = [], {}
        try:
            for name, blob in files.items():
                if name not in allowed or not blob:
                    continue
                if len(blob) > 8 * 1024 * 1024:
                    return fail(413, "รูปใหญ่เกิน 8 MB")
                ext = sniff_image(blob)
                if ext is None:
                    return fail(400, "รูปต้องเป็น png / jpg / webp / gif")
                images[name] = write_item_image(f"s-{slot}-{name}", ext, blob)
                written.append(images[name])
            for name in removes:
                if name in allowed and name not in images:
                    images[name] = ""
            fields = {k: v for k, v in data.items() if k not in ("slot", "action", "rate", "rate_loaded", "rev")}
            async with _site_lock:
                rev = str(data.get("rev") or "")
                if rev and rev != site_rev():  # อีกแท็บ/อีกคนเพิ่งแก้ → ลำดับแบนเนอร์อาจเลื่อนไปแล้ว
                    return fail(409, "หน้าเว็บเพิ่งถูกแก้จากอีกหน้าต่าง รีเฟรชก่อนแล้วแก้ใหม่")
                current, stale = self.site(), set()
                names = {i["category"] for i in db.shop_items(active_only=False) if i["category"]}
                for name in [k for k in current["cats"] if k not in names]:  # หมวดที่ไม่มีแล้ว → ล้างทิ้ง
                    stale.add(current["cats"].pop(name).get("img") or "")
                try:
                    new, dropped = web_site.update(current, address, action, fields, images)
                except web_site.SiteError as e:
                    return fail(400, str(e))
                dropped = set(dropped) | {x for x in stale if x}
                db.set_setting("web:site", web_site.dump(new))
                written = []  # บันทึกแล้ว ไม่ต้องลบทิ้ง
            if rate is not None:
                db.set_setting("cookie_rate", rate)
        finally:
            for name in written:  # บันทึกไม่ผ่าน → ไม่ทิ้งไฟล์ขยะไว้
                drop_item_image(name)
        for name in dropped:
            drop_item_image(name)
        what = {"logo": "โลโก้", "tiles": "ปุ่มลัด", "hero": "แบนเนอร์", "promos": "การ์ดโปรโมต", "cats": "รูปหมวด",
                "deco": "ของตกแต่ง", "theme": "สีธีม", "donate": "หัวหน้า Donate"}[slot]
        verb = {"delete": "ลบ/รีเซ็ต", "up": "เลื่อน", "down": "เลื่อน"}.get(action, "แก้")
        await mod_log(bot.get_guild(cfg.guild_id), f"🎨 {member.mention} {verb}{what}บนเว็บ"
                                                   + (f" · เรตเติมคุกกี้ 1 บาท = {rate:,}" if rate is not None else ""))
        return 200, {"ok": True}

    @staticmethod
    def donate_admin_catalog() -> list:
        """รายการ Donate ทั้งหมด (รวมที่ปิด) + ค่าดิบสำหรับฟอร์ม — ส่งให้คนแก้ร้านเท่านั้น"""
        out = []
        for i in db.items(active_only=False):
            d = donate_item_web(i)
            d["raw"] = {"code": i["code"], "name": i["name"], "description": i["description"],
                        "price": f"{i['price'] / 100:.2f}".rstrip("0").rstrip("."), "cookies": i["cookies"],
                        "ckx": (i["ckx"] or "").replace(";", " "), "active": bool(i["active"]), "sort": i["sort"],
                        "image_url": d["image_url"]}
            out.append(d)
        return out

    async def admin_donate_item(self, uid: int, data: dict, image: Optional[bytes], remove_image: bool) -> tuple:
        """เพิ่ม/แก้รายการ Donate บนเว็บ (แทน /item add · /item edit)"""
        def fail(status, msg):
            return status, {"ok": False, "error": msg}

        member = await self._editor(uid)
        if member is None:
            return fail(403, "บัญชีนี้แก้ร้านไม่ได้")
        original = str(data.get("original") or "").strip()
        item = db.item_get(original) if original else None
        if original and item is None:
            return fail(404, f"ไม่พบ {original} แล้ว (อาจถูกลบไป) รีเฟรชหน้า")
        code = str(data.get("code") or "").strip()
        if not ITEM_CODE_RE.fullmatch(code) or code.upper() == TOPUP_CODE:
            return fail(400, "รหัสใช้ได้แค่อังกฤษ ตัวเลข _ - ยาวไม่เกิน 20 ตัว (ห้ามใช้ TOPUP)")
        clash = db.item_get(code)
        if clash and (item is None or clash["code"].casefold() != item["code"].casefold()):
            return fail(409, f"รหัส {code} มีรายการอื่นใช้อยู่แล้ว")
        name = str(data.get("name") or "").strip()
        if not name:
            return fail(400, "ใส่ชื่อรายการ")
        try:
            price = parse_baht(str(data.get("price") or ""))
        except ValueError:
            return fail(400, "ราคาไม่ถูกต้อง — ใส่ตัวเลขบาท เช่น 50 หรือ 49.50")
        if price > 10_000_000:
            return fail(400, "ราคาสูงเกินไป")
        try:
            cookies = int(str(data.get("cookies") or "0").strip() or 0)
            sort = int(str(data.get("sort") or "0").strip() or 0)
        except ValueError:
            return fail(400, "ช่องคุกกี้/ลำดับต้องเป็นตัวเลข")
        if not 0 <= cookies <= 10_000_000 or not -100_000 <= sort <= 100_000:
            return fail(400, "ช่องคุกกี้ (0–10,000,000) หรือลำดับไม่ถูกต้อง")
        ckx_text = str(data.get("ckx") or "").strip()
        try:
            ckx = ckx_link.normalize_items(ckx_text) if ckx_text else ""
        except ValueError as e:
            return fail(400, str(e))
        if ckx and ckx_link.max_count(ckx) * cfg.donate_max_qty > ckx_link.MAX_COUNT:
            return fail(400, f"จำนวนในรหัส × จำนวนสูงสุดต่อรายการ ({cfg.donate_max_qty}) ต้องไม่เกิน {ckx_link.MAX_COUNT}")
        active = str(data.get("active", "1")).lower() in ("1", "true", "on", "yes")
        image_name = None
        if image:
            if len(image) > 8 * 1024 * 1024:
                return fail(413, "รูปใหญ่เกิน 8 MB")
            ext = sniff_image(image)
            if ext is None:
                return fail(400, "รูปต้องเป็น png / jpg / webp / gif")
            image_name = write_item_image(f"d-{code}", ext, image)
        elif remove_image and item is not None and item["image"]:
            image_name = ""
        old_image = item["image"] if image_name is not None and item is not None else ""
        fields = dict(name=trunc(name, 80), price=price, description=trunc(str(data.get("description") or "").strip(), 200),
                      sort=sort, cookies=cookies, ckx=ckx, active=int(active))
        if item is None:
            db.item_add(code, image=image_name or "", **fields)
            verb = "เพิ่ม"
        else:
            db.item_update(item["code"], code=code, image=image_name, **fields)
            verb = "แก้"
        if old_image:
            drop_item_image(old_image)
        await mod_log(bot.get_guild(cfg.guild_id), f"🧾 {member.mention} {verb}รายการ Donate ผ่านเว็บ `{code}` "
                                                   f"{trunc(name, 80)} {fmt_baht(price)}" + ("" if active else " (ปิด)"))
        return 200, {"ok": True, "code": code}

    async def admin_donate_delete(self, uid: int, data: dict) -> tuple:
        member = await self._editor(uid)
        if member is None:
            return 403, {"ok": False, "error": "บัญชีนี้แก้ร้านไม่ได้"}
        item = db.item_get(str(data.get("code") or "").strip())
        if item is None or not db.item_delete(item["code"]):
            return 404, {"ok": False, "error": "ไม่พบรายการนี้แล้ว"}
        drop_item_image(item["image"])
        await mod_log(bot.get_guild(cfg.guild_id),
                      f"🧾 {member.mention} ลบรายการ Donate ผ่านเว็บ `{item['code']}` {item['name']}")
        return 200, {"ok": True}

    # ---------------- Donate (จ่ายบนเว็บ · บอทโพสต์ในห้อง Donate ให้) ----------------
    @staticmethod
    def donate_enabled() -> bool:
        return bool(cfg.donate_enabled and stripe is not None)

    @staticmethod
    def donate_catalog() -> dict:
        return {"items": [donate_item_web(i) for i in db.items()], "rate": donate_rate(), "min": cfg.donate_min,
                "max_qty": cfg.donate_max_qty, "max_lines": MAX_CART_LINES, "topup_max": DONATE_TOPUP_MAX}

    @staticmethod
    def donate_meta() -> dict:
        items, meta = web_page_data()
        meta = dict(meta, intro=DONATE_INTRO, minutes=cfg.stripe_session_minutes, shop_items=items,
                    cookie_rate=donate_rate())
        return meta

    @staticmethod
    def donate_orders(uid: int) -> list:
        return [donate_brief(o) for o in db.orders_of(uid, 8)]

    @staticmethod
    def _own_order(uid: int, data):
        oid = data.get("id") if isinstance(data, dict) else None
        if isinstance(oid, bool) or not isinstance(oid, int):
            return None
        order = db.order_get(oid)
        return order if order is not None and order["owner_id"] == uid else None

    async def _donate_room(self, guild, member):
        """ห้อง Donate ของคนนี้ — ใช้ห้องที่เปิดอยู่ หรือเปิดห้องใหม่ให้ (เหมือนกดปุ่ม Donate ในดิส)"""
        for t in db.open_tickets(member.id, "donate"):
            thread = guild.get_thread(t["channel_id"])
            if thread is None:
                try:
                    thread = await guild.fetch_channel(t["channel_id"])
                except discord.NotFound:  # ห้องถูกลบไปแล้ว → ปิดในระบบ แล้วเปิดใหม่
                    db.set_status(t["id"], "closed")
                    continue
            if getattr(thread, "archived", False):
                try:
                    await thread.edit(archived=False)
                except discord.HTTPException as e:
                    log.warning("unarchive ห้อง Donate %s ไม่ได้: %s", thread.id, e)
            try:  # ออกจากเซิฟแล้วกลับมา = หลุดจากห้องส่วนตัว → ดึงกลับเข้าห้อง ให้เห็นการ์ดจ่ายเงิน/สถานะ
                await thread.add_user(member)
            except discord.HTTPException as e:
                log.warning("ดึง %s เข้าห้อง Donate ไม่ได้: %s", member.id, e)
            return thread, t, None
        thread, err = await open_ticket_thread(guild, member, TICKET_TYPES["donate"], {}, via="web")
        if thread is None:
            return None, None, err
        return thread, db.by_channel(thread.id), None

    async def donate_checkout(self, uid: int, data) -> tuple:
        """สั่ง Donate จากเว็บ → ออเดอร์ในห้อง Donate ของคนนี้ + บิล Stripe — คืน (HTTP status, JSON)"""
        def fail(status, msg, code="bad", **extra):
            return status, {"ok": False, "error": msg, "code": code, **extra}

        if not self.donate_enabled():
            return fail(503, "ระบบ Donate ยังไม่เปิด", "off")
        if not isinstance(data, dict):
            return fail(400, "ข้อมูลไม่ถูกต้อง")
        nonce = str(data.get("nonce") or "")
        if not NONCE_RE.fullmatch(nonce):
            return fail(400, "ข้อมูลไม่ถูกต้อง รีเฟรชหน้าแล้วลองใหม่")
        raw = data.get("items") or []
        if not isinstance(raw, list):
            return fail(400, "ข้อมูลไม่ถูกต้อง")
        wanted = []
        for line in raw:
            if not isinstance(line, dict):
                return fail(400, "ข้อมูลไม่ถูกต้อง")
            code, qty = str(line.get("code") or "").strip(), line.get("qty")
            if not code or isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= cfg.donate_max_qty:
                return fail(400, f"จำนวนต่อรายการต้องอยู่ระหว่าง 1–{cfg.donate_max_qty}")
            wanted.append((code, qty))
        topup = data.get("topup") or 0
        if isinstance(topup, bool) or not isinstance(topup, int) or not 0 <= topup <= DONATE_TOPUP_MAX:
            return fail(400, "ยอดเติมคุกกี้ไม่ถูกต้อง")
        if not wanted and not topup:
            return fail(400, "ยังไม่ได้เลือกรายการ")
        if len(wanted) + (1 if topup else 0) > MAX_CART_LINES:
            return fail(400, f"ใส่ได้สูงสุด {MAX_CART_LINES} รายการต่อรอบ")
        ingame = str(data.get("ingame") or "").strip()
        expected = data.get("expected_total")

        superseded = []
        async with user_lock(uid):
            old = db.order_by_nonce(uid, nonce)
            if old is not None:  # กดซ้ำ / เน็ตหลุดแล้วส่งใหม่ → ใช้ออเดอร์เดิม ไม่สร้างบิลซ้ำ
                return await self._donate_resume(uid, old)
            member = await self.member(uid)
            if member is None:
                return fail(401, "บัญชีนี้ไม่ได้อยู่ในเซิฟ Discord แล้ว", "login")
            lines = []
            try:
                for code, qty in wanted:
                    lines = cart_add(lines, db.item_get(code), qty, cfg.donate_max_qty)
            except CartError as e:
                return fail(409, str(e), "changed", catalog=self.donate_catalog())
            if topup:
                rate = donate_rate()
                if rate <= 0:
                    return fail(409, "ตอนนี้ปิดเติมคุกกี้ตามยอดอยู่", "changed", catalog=self.donate_catalog())
                satang = topup * 100
                if satang < cfg.donate_min:
                    return fail(400, f"เติมคุกกี้ขั้นต่ำ {fmt_baht(cfg.donate_min)}")
                cookies = satang * rate // 100
                lines.append({"code": TOPUP_CODE, "name": f"เติมคุกกี้ {cookies:,} 🍪", "unit": satang, "qty": 1,
                              "cookies": cookies, "ckx": ""})
            total = cart_total(lines)
            if isinstance(expected, int) and not isinstance(expected, bool) and expected != total:
                return fail(409, "ราคาเพิ่งเปลี่ยน ดูยอดใหม่แล้วกดอีกครั้ง", "changed", catalog=self.donate_catalog())
            if total < cfg.donate_min:
                return fail(400, f"ยอดขั้นต่ำต่อรอบคือ {fmt_baht(cfg.donate_min)}")
            guild = bot.get_guild(cfg.guild_id)
            if order_ckx_lines(lines):
                if not ckx_link.valid_ingame(ingame):
                    return fail(400, "ใส่ชื่อในเกมที่จะรับของ (ห้ามมี \" | ` และยาวไม่เกิน 40 ตัว)", "ingame")
                for line in order_ckx_lines(lines):
                    try:
                        ckx_link.normalize_items(line["ckx"], multiply=line["qty"])
                    except ValueError as e:  # รหัสของในรายการตั้งผิด/จำนวนเกิน → ไม่ให้จ่ายก่อนแล้วส่งไม่ได้
                        await mod_log(guild, f"❌ Donate บนเว็บ: รหัสของ `{line['code']}` ใช้ไม่ได้ ({e})", COLOR_BAD)
                        return fail(409, f"{line['name']} × {line['qty']} ส่งเข้าเกมไม่ได้ — ลดจำนวน หรือแจ้งแอดมิน",
                                    "broken")
            else:
                ingame = ""
            thread, ticket, err = await self._donate_room(guild, member)
            if thread is None:
                return fail(503, err or "เปิดห้อง Donate ไม่ได้ ลองใหม่อีกครั้ง", "room")
            bills = [o for o in db.orders_in_thread(thread.id, ("pending",)) if o["owner_id"] == uid]
            if bills:
                return fail(409, f"มีบิล #{bills[0]['id']:04d} รอจ่ายอยู่ — จ่ายบิลเดิม หรือยกเลิกก่อนแล้วสั่งใหม่",
                            "open_bill", order=donate_brief(bills[0]))
            for o in db.orders_in_thread(thread.id, ("cart", "review", "expired")):  # ตะกร้า/บิลเก่าที่ค้าง → แทนด้วยอันใหม่
                if o["owner_id"] != uid:
                    continue
                async with order_lock(o["id"]):
                    now_o = db.order_get(o["id"])
                    if now_o["status"] == "pending":  # เพิ่งได้บิล (กดในดิสพร้อมกัน) → ไม่สร้างใบที่สอง
                        return fail(409, f"มีบิล #{o['id']:04d} รอจ่ายอยู่ — จ่ายบิลเดิม หรือยกเลิกก่อนแล้วสั่งใหม่",
                                    "open_bill", order=donate_brief(now_o))
                    if now_o["status"] in ("cart", "review", "expired"):
                        db.order_update(o["id"], status="cancelled")
                        superseded.append(o["id"])
            for oid in superseded:
                spawn(post_order_card(oid, title="ยกเลิกแล้ว — สั่งใหม่จากหน้าเว็บ"), f"Donate #{oid:04d}")
            if ingame:
                db.wallet_update(uid, ingame=ingame)
            order_id = db.order_create_web(ticket["id"], thread.id, uid, nonce, lines, total, ingame)
            if order_id is None:
                return await self._donate_resume(uid, db.order_by_nonce(uid, nonce))
            log.info("เว็บ: %s สั่ง Donate #%04d %s", uid, order_id, fmt_baht(total))
            return await self._donate_bill(order_id, note=f"🌐 <@{uid}> สั่ง Donate จากหน้าเว็บ — "
                                                          "จ่ายต่อได้ที่หน้าเว็บ หรือกดปุ่มด้านล่าง")

    async def _donate_bill(self, order_id: int, note: str = "") -> tuple:
        """สร้างบิล (ถ้ายังไม่มี) แล้วตอบลิงก์จ่าย — ผู้เรียกต้องถือ user_lock(เจ้าของ) อยู่ (บิลทีละใบต่อคน)"""
        guild = bot.get_guild(cfg.guild_id)
        err = None
        async with order_lock(order_id):
            if db.order_get(order_id)["status"] in ("review", "expired"):
                _, err = await _bill_locked(order_id, guild, via="web")
        spawn(post_order_card(order_id, note=note), f"การ์ด Donate #{order_id:04d}")
        brief = donate_brief(db.order_get(order_id))
        if err:  # ออเดอร์ยังอยู่ (รอยืนยัน) — กดจ่ายใหม่ได้ทั้งบนเว็บและในดิส
            return 502, {"ok": False, "error": err, "code": "bill", "order": brief}
        if brief["status"] in ("paid", "delivered"):
            return 200, {"ok": True, "order": brief, "paid": True}
        if not brief["pay_url"]:
            return 502, {"ok": False, "error": "บิลนี้ใช้ไม่ได้แล้ว กดสร้างบิลใหม่", "code": "bill", "order": brief}
        return 200, {"ok": True, "order": brief, "pay_url": brief["pay_url"]}

    async def _donate_resume(self, uid: int, order) -> tuple:
        """ออเดอร์เดิม (nonce ซ้ำ / กดจ่ายต่อ) — ผู้เรียกต้องถือ user_lock(uid) อยู่"""
        if order["status"] == "pending" and not donate_brief(order)["pay_url"]:
            await sync_payment(order["id"])  # เลยเวลาบิลแล้ว → ให้ Stripe ยืนยันก่อน
            order = db.order_get(order["id"])
        if order["status"] == "cancelled":
            return 409, {"ok": False, "error": "รายการนี้ถูกยกเลิกแล้ว", "code": "cancelled",
                         "order": donate_brief(order)}
        if order["status"] == "expired":
            return 409, {"ok": False, "error": "บิลนี้หมดอายุแล้ว — กดสร้างบิลใหม่ที่รายการ", "code": "expired",
                         "order": donate_brief(order)}
        return await self._donate_bill(order["id"])

    async def donate_pay(self, uid: int, data) -> tuple:
        """ยืนยัน/จ่ายต่อ/สร้างบิลใหม่ ของออเดอร์ตัวเอง (รวมออเดอร์ที่สั่งในห้อง Donate บน Discord)"""
        if not self.donate_enabled():
            return 503, {"ok": False, "error": "ระบบ Donate ยังไม่เปิด", "code": "off"}
        order = self._own_order(uid, data)
        if order is None:
            return 404, {"ok": False, "error": "ไม่พบรายการนี้"}
        if await self.member(uid) is None:
            return 401, {"ok": False, "error": "บัญชีนี้ไม่ได้อยู่ในเซิฟ Discord แล้ว", "code": "login"}
        async with user_lock(uid):  # บิลทีละใบต่อคน (เหมือนตอนสั่ง และปุ่มในดิส)
            order = db.order_get(order["id"])
            if order["status"] in ("review", "expired"):
                lines = lines_of(order)
                if order_ckx_lines(lines):
                    name = order_ingame(order)
                    if not ckx_link.valid_ingame(name):
                        name = str(data.get("ingame") or "").strip()
                        if not ckx_link.valid_ingame(name):
                            return 400, {"ok": False, "code": "ingame",
                                         "error": "ใส่ชื่อในเกมที่จะรับของ (ห้ามมี \" | ` และยาวไม่เกิน 40 ตัว)"}
                        db.wallet_update(uid, ingame=name)
                    if order["ingame"] != name:
                        db.order_update(order["id"], ingame=name)
                return await self._donate_bill(order["id"])
            return await self._donate_resume(uid, order)

    async def donate_check(self, uid: int, data) -> tuple:
        order = self._own_order(uid, data)
        if order is None:
            return 404, {"ok": False, "error": "ไม่พบรายการนี้"}
        now = time.monotonic()
        if order["status"] == "pending" and now - _donate_checked.get(order["id"], 0) >= 3:
            _donate_checked[order["id"]] = now
            await sync_payment(order["id"])
        return 200, {"ok": True, "order": donate_brief(db.order_get(order["id"]))}

    async def donate_cancel(self, uid: int, data) -> tuple:
        order = self._own_order(uid, data)
        if order is None:
            return 404, {"ok": False, "error": "ไม่พบรายการนี้"}
        async with order_lock(order["id"]):
            result, text = await _cancel_locked(order["id"])
        if result == "paid":
            await sync_payment(order["id"])
            return 409, {"ok": False, "error": "บิลนี้จ่ายแล้ว ยกเลิกไม่ได้", "code": "paid",
                         "order": donate_brief(db.order_get(order["id"]))}
        if result != "cancelled":
            return (409 if result == "closed" else 502), {"ok": False, "error": text,
                                                          "order": donate_brief(db.order_get(order["id"]))}
        spawn(post_order_card(order["id"], title="ยกเลิกแล้ว (จากหน้าเว็บ)"), f"Donate #{order['id']:04d}")
        await mod_log(bot.get_guild(cfg.guild_id), f"❌ <@{uid}> ยกเลิก Donate #{order['id']:04d} บนเว็บ")
        return 200, {"ok": True, "order": donate_brief(db.order_get(order["id"]))}


web_shop = WebShop()


async def cart_after_checkout(cart_id: int):
    """หลังแลกจากเว็บ: ส่งคำสั่งเข้าเกม + ใบแลกรวมในกระเป๋า + log แอดมิน (ทำเบื้องหลัง ไม่ให้หน้าเว็บรอ)"""
    guild = bot.get_guild(cfg.guild_id)
    cart = db.cart_get(cart_id)
    if guild is None or cart is None:
        return
    pinged = False
    for r in db.cart_lines(cart_id):
        try:
            if r["job_id"]:
                if not await ckx_post(r["job_id"]) or not db.redemption_get(r["id"])["log_id"]:
                    await redemption_changed(guild, r["id"], cart_receipt=False)
            else:
                first = not pinged and not r["log_id"]  # แท็กแอดมินครั้งเดียวต่อตะกร้า
                await redemption_changed(guild, r["id"], notify_staff=first, cart_receipt=False)
                pinged = pinged or first
        except Exception:  # noqa: BLE001
            log.exception("ตะกร้า C-%04d: RD-%s", cart_id, r["id"])
    await cart_receipt_update(guild, cart_id)
    await refresh_wallet(guild, cart["discord_id"])


async def cart_sweep():
    """เปิดบอทใหม่: ตะกร้าที่ทำค้างไว้ (ยังไม่มีใบรวม/log) → ทำต่อให้ครบ"""
    for cart in db.carts_unfinished():
        await cart_after_checkout(cart["id"])


def cart_receipt_embed(cart, lines) -> discord.Embed:
    statuses = {r["status"] for r in lines}
    if statuses <= {"claimed", "done", "refunded", "cancelled"}:
        color = COLOR_OK if statuses & {"claimed", "done"} else COLOR_MUTED
    elif statuses & {"failed", "problem"}:
        color = COLOR_BAD
    else:
        color = COLOR_COOKIE
    rows = []
    for r in lines:
        icon, text = REDEEM_STATUS.get(r["status"], ("•", r["status"]))
        rows.append(f"{icon} `RD-{r['id']:04d}` **{discord.utils.escape_markdown(r['name'])}** × {r['qty']} "
                    f"· {fmt_cookies(r['price'] * r['qty'])} — {text}"
                    + (f"\n-# {trunc(r['note'], 150)}" if r["note"] else ""))
    embed = discord.Embed(title=f"🧾 ตะกร้า C-{cart['id']:04d} · แลกจากเว็บ", color=color,
                          description=trunc("\n".join(rows), 4000),
                          timestamp=datetime.fromisoformat(cart["created_at"]))
    embed.add_field(name="ใช้คุกกี้", value=fmt_cookies(cart["total"]))
    refunded = sum(r["price"] * r["qty"] for r in lines if r["status"] == "refunded")
    if refunded:
        embed.add_field(name="คืนแล้ว", value=fmt_cookies(refunded))
    if cart["ingame"]:
        embed.add_field(name="ชื่อในเกม", value=discord.utils.escape_markdown(cart["ingame"]))
    if any(r["ckx"] for r in lines):
        embed.set_footer(text="ของที่ส่งเข้าเกมเอง: เข้าเกมแล้วกดรับที่ปุ่มบ้านคุกกี้")
    return embed


async def cart_receipt_update(guild, cart_id: int):
    """ใบแลกรวมของตะกร้าในกระเป๋าคุกกี้ (ข้อความเดียว แก้ตามสถานะ)"""
    async with _cart_receipt_locks.setdefault(cart_id, asyncio.Lock()):
        cart = db.cart_get(cart_id)
        if guild is None or cart is None:
            return
        uid = cart["discord_id"]
        member = guild.get_member(uid)
        try:
            thread = await ensure_wallet(guild, member or discord.Object(id=uid), create=member is not None)
        except discord.HTTPException as e:
            log.warning("กระเป๋าของ %s: %s", uid, e)
            return
        if thread is None:
            return
        embed = cart_receipt_embed(cart, db.cart_lines(cart_id))
        try:
            if cart["receipt_id"]:
                try:
                    await thread.get_partial_message(cart["receipt_id"]).edit(embed=embed)
                    return
                except discord.NotFound:
                    pass
            msg = await thread.send(content=f"<@{uid}>" if not cart["receipt_id"] else None, embed=embed,
                                    allowed_mentions=discord.AllowedMentions(users=True))
            db.cart_set_receipt(cart_id, msg.id)
        except discord.HTTPException as e:
            log.warning("ใบแลกตะกร้า C-%s: %s", cart_id, e)


async def save_item_image(code: str, attachment: discord.Attachment) -> str:
    ext = Path(attachment.filename or "").suffix.lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ("png", "jpg", "webp", "gif"):
        raise app_commands.AppCommandError("รูปต้องเป็น png / jpg / webp / gif")
    if attachment.size > 8 * 1024 * 1024:
        raise app_commands.AppCommandError("รูปใหญ่เกิน 8 MB")
    data = await attachment.read()
    return write_item_image(code, ext, data)


async def start_web():
    if not cfg.web_enabled:
        return
    try:
        runner = web.AppRunner(web_catalog.create_app(web_shop, IMAGES_DIR), access_log=None)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", cfg.web_port).start()
        log.info("เว็บแคตตาล็อกเปิดที่พอร์ต %s%s", cfg.web_port,
                 f" → {cfg.public_url}" if cfg.public_url else " (ยังไม่มีโดเมน: Railway → Settings → Networking → Generate Domain)")
        bot.web_runner = runner
    except OSError as e:
        log.warning("เปิดเว็บแคตตาล็อกไม่ได้ (พอร์ต %s): %s", cfg.web_port, e)


# ---------------------------------------------------------------- Donate → คุกกี้ / ส่งเข้าเกมเอง

def order_ckx_lines(lines: list) -> list:
    return [line for line in lines if line.get("ckx")]


def order_manual_lines(lines: list) -> list:
    return [line for line in lines if not line.get("ckx") and not line.get("cookies")]


def order_ingame(order) -> str:
    if order["ingame"]:
        return order["ingame"]
    w = db.wallet_get(order["owner_id"])
    return w["ingame"] if w else ""


async def auto_fulfil(guild, order_id: int):
    """จ่ายแล้ว: เติมคุกกี้ + ส่งของที่มีรหัส Cookie Express เข้าเกม · ถ้าไม่มีของต้องส่งมือ → ส่งของแล้วอัตโนมัติ"""
    if guild is None:
        return
    async with order_lock(order_id):
        order = db.order_get(order_id)
        if order is None or order["status"] not in ("paid", "delivered"):
            return
        lines = lines_of(order)
        cookies = sum(int(line.get("cookies") or 0) * int(line["qty"]) for line in lines)
        if cookies and not order["cookies_given"]:
            ok, _ = db.cookies_add(order["owner_id"], cookies, "topup", ref=f"order-{order_id}",
                                   note=f"Donate #{order_id:04d}")
            db.order_update(order_id, cookies_given=1)
        ckx_lines = order_ckx_lines(lines)
        if ckx_lines and not order["job_id"]:
            ingame = order_ingame(order)
            try:
                items = ";".join(ckx_link.normalize_items(line["ckx"], multiply=line["qty"]) for line in ckx_lines)
            except ValueError as e:
                items = None
                await log_to(guild, cfg.donate_log or cfg.mod_logs, discord.Embed(
                    color=COLOR_BAD, description=f"⚠️ Donate #{order_id:04d} ส่งเข้าเกมเองไม่ได้ ({e}) — "
                                                 f"ส่งเองแล้วกด 📦 ที่ <#{order['thread_id']}>"),
                             content=staff_ping(guild) or None, allowed_mentions=discord.AllowedMentions(users=True))
            if items is None:
                pass
            elif ckx_link.valid_ingame(ingame):
                job_id = db.job_create("donate", order_id, order["owner_id"], ingame, items,
                                       ckx_link.count_lines(items))
                db.order_update(order_id, job_id=job_id, ingame=ingame)
                await ckx_post(job_id)
            else:
                thread = await get_thread(guild, order["thread_id"], unarchive=True)
                if thread is not None:
                    view = ui.View(timeout=None)
                    view.add_item(OrderNameButton(order_id))
                    await thread.send(f"<@{order['owner_id']}> ใส่ชื่อในเกมเพื่อรับของได้เลย 🎮", view=view,
                                      allowed_mentions=discord.AllowedMentions(users=True))
        order = db.order_get(order_id)
        if order["status"] == "paid" and auto_done(order):
            db.order_update(order_id, status="delivered", delivered_by=guild.me.id,
                            delivered_at=datetime.now(timezone.utc).isoformat())
    if cookies:
        await refresh_wallet(guild, order["owner_id"])
        try:
            await ensure_wallet(guild, guild.get_member(order["owner_id"]) or discord.Object(id=order["owner_id"]),
                                create=guild.get_member(order["owner_id"]) is not None)
        except discord.HTTPException:
            pass
    await update_paid_card(guild, order_id)
    board_dirty()


def delivery_text(order, lines: list) -> str:
    out = []
    cookies = sum(int(line.get("cookies") or 0) * int(line["qty"]) for line in lines)
    if cookies:
        out.append(f"🍪 เติม **{fmt_cookies(cookies)}** เข้ากระเป๋าแล้ว" if order["cookies_given"] else
                   f"⏳ รอเติม {fmt_cookies(cookies)}")
    if order_ckx_lines(lines):
        job = db.job_get(order["job_id"]) if order["job_id"] else None
        if job is None:
            out.append("⏳ รอใส่ชื่อในเกมเพื่อส่งของ")
        else:
            icon, text = REDEEM_STATUS.get(job["status"], ("•", job["status"]))
            out.append(f"{icon} ของในเกม: {text} (ชื่อ **{discord.utils.escape_markdown(job['ingame'])}**)")
    manual = order_manual_lines(lines)
    if manual:
        names = ", ".join(f"`{line['code']}` × {line['qty']}" for line in manual)
        if order["status"] == "delivered":
            out.append(f"✅ แอดมินส่งแล้ว: {names}" + (f" โดย <@{order['delivered_by']}>" if order["delivered_by"] else ""))
        else:
            out.append(f"⏳ รอแอดมินส่งในเกม: {names}")
    return "\n".join(out) or "⏳ รอแอดมินส่งของในเกม"


def auto_done(order) -> bool:
    """ทุกอย่างในออเดอร์ส่งถึงแล้วโดยไม่ต้องมีคนทำ: คุกกี้เข้าแล้ว + ของในเกมผู้เล่นรับแล้ว + ไม่มีรายการส่งมือ"""
    lines = lines_of(order)
    if order_manual_lines(lines):
        return False
    if any(line.get("cookies") for line in lines) and not order["cookies_given"]:
        return False
    if order_ckx_lines(lines):
        job = db.job_get(order["job_id"]) if order["job_id"] else None
        return job is not None and job["status"] == "claimed"
    return True


def needs_manual_button(order) -> bool:
    lines = lines_of(order)
    if order["status"] != "paid":
        return False
    job = db.job_get(order["job_id"]) if order["job_id"] else None
    return (bool(order_manual_lines(lines)) or (bool(order_ckx_lines(lines)) and job is None)
            or (job is not None and job["status"] in ("failed", "problem", "cancelled")))


async def update_paid_card(guild, order_id: int):
    order = db.order_get(order_id)
    if guild is None or order is None or not order["paid_message_id"]:
        return
    thread = await get_thread(guild, order["thread_id"])
    if thread is None:
        return
    try:
        await thread.get_partial_message(order["paid_message_id"]).edit(
            embed=paid_embed(order, lines_of(order)), view=DeliverView() if needs_manual_button(order) else None)
    except discord.HTTPException as e:
        log.warning("แก้การ์ด Donate #%s ไม่ได้: %s", order_id, e)


class OrderNameButton(ui.DynamicItem[ui.Button], template=r"cc:ordername:(?P<oid>\d+)"):
    def __init__(self, oid: int):
        super().__init__(ui.Button(label="ใส่ชื่อในเกม", emoji="🎮", style=discord.ButtonStyle.primary,
                                   custom_id=f"cc:ordername:{oid}"))
        self.oid = oid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["oid"]))

    async def callback(self, interaction: discord.Interaction):
        order = db.order_get(self.oid)
        if order is None:
            return await reply(interaction, "ไม่พบรายการนี้")
        if interaction.user.id != order["owner_id"] and not is_staff(interaction.user):
            return await reply(interaction, "ปุ่มนี้สำหรับเจ้าของรายการ")
        oid = self.oid

        async def after(i: discord.Interaction, name: str):
            db.order_update(oid, ingame=name)
            await i.response.send_message(f"ส่งของเข้าเกมให้ **{discord.utils.escape_markdown(name)}** แล้ว 📦",
                                          ephemeral=True)
            await auto_fulfil(i.guild, oid)

        await interaction.response.send_modal(IngameNameModal(order_ingame(order), after=after,
                                                              target=order["owner_id"]))


class TopupModal(BaseModal):
    def __init__(self, order_id: int, rate: int):
        super().__init__(title="เติมคุกกี้ 🍪", timeout=600)
        self.order_id, self.rate = order_id, rate
        self.amount = ui.TextInput(label=f"ยอด Donate (บาท) · 1 บาท = {rate:,} คุกกี้", placeholder="เช่น 100",
                                   max_length=7)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            satang = parse_baht(self.amount.value)
        except ValueError:
            return await reply(interaction, "ใส่ยอดเป็นตัวเลขบาท เช่น 100")
        if satang < cfg.donate_min:
            return await reply(interaction, f"ขั้นต่ำ {fmt_baht(cfg.donate_min)}")
        if satang > 100_000 * 100:
            return await reply(interaction, "ยอดสูงเกินไป")
        cookies = satang * self.rate // 100
        async with order_lock(self.order_id):
            order = db.order_get(self.order_id)
            if order is None or order["status"] != "cart":
                return await reply(interaction, "ตะกร้านี้ส่งไปแล้ว — กด 📝 แก้ไข ที่การ์ดสรุปถ้าจะเปลี่ยน")
            lines = [line for line in lines_of(order) if line["code"] != TOPUP_CODE]
            if len(lines) >= MAX_CART_LINES:
                return await reply(interaction, f"ตะกร้าเต็ม {MAX_CART_LINES} รายการแล้ว")
            lines.append({"code": TOPUP_CODE, "name": f"เติมคุกกี้ {cookies:,} 🍪", "unit": satang, "qty": 1,
                          "cookies": cookies, "ckx": ""})
            db.order_update(order["id"], lines=lines, total=cart_total(lines))
            order = db.order_get(order["id"])
            await show_cart(interaction, order, lines)
        await reply(interaction, f"ใส่ **เติมคุกกี้ {fmt_cookies(cookies)}** ({fmt_baht(satang)}) ในตะกร้าแล้ว")


TOPUP_CODE = "TOPUP"


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


def web_editor_check(guild) -> list:
    """ใครแก้หน้าเว็บได้ (ล็อกไว้ที่ WEB_EDITOR_IDS · ไม่ตั้ง = เจ้าของเซิฟ Discord คนเดียว)"""
    if cfg.web_editor_ids:
        out = [("🔒", "แก้หน้าเว็บได้เฉพาะ (WEB_EDITOR_IDS): " + ", ".join(f"<@{i}>" for i in cfg.web_editor_ids))]
        gone = [i for i in cfg.web_editor_ids if guild.get_member(i) is None]
        if gone:
            out.append(("⚠️", "WEB_EDITOR_IDS มี ID ที่ไม่อยู่ในดิสนี้: " + ", ".join(str(i) for i in gone)))
        return out
    owner = getattr(guild, "owner_id", None)
    return [("🔒", f"แก้หน้าเว็บได้เฉพาะเจ้าของเซิฟ: <@{owner}> · อยากล็อกเป็นคนอื่น ใส่ WEB_EDITOR_IDS"
                  if owner else "แก้หน้าเว็บได้เฉพาะเจ้าของเซิฟ Discord")]


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
    player_roles = {guild.id: "@everyone", cfg.survivor_role: "Survivor", cfg.member_role: "Member"}
    for rid in dict.fromkeys(cfg.staff_roles + cfg.admin_roles):
        role = guild.get_role(rid)
        if role is None:
            out.append(("❌", f"role ทีมแอดมิน: ไม่เจอ ID `{rid}`"))
        elif rid in player_roles:
            out.append(("❌", f"ROLE_STAFF / ROLE_ADMIN ตั้งเป็น role ผู้เล่น ({player_roles[rid]}) — "
                              "ผู้เล่นทุกคนจะกดปุ่มแอดมินได้ ต้องใช้ role ของทีมแอดมินเท่านั้น"))
        else:
            n = len([m for m in getattr(role, "members", []) if not m.bot])
            out.append(("✅", f"role ทีม {role.mention}: {n} คน (จะถูกดึงเข้าทุก ticket)") if n else
                       ("⚠️", f"role ทีม {role.mention} ยังไม่มีใครมี — ใส่ role นี้ให้ตัวเองด้วย ไม่งั้นจะไม่เห็น ticket"))
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
    basic = ["view_channel", "send_messages", "embed_links", "read_message_history"]
    if guild.member_count and len(guild.members) < min(guild.member_count, 2):
        out.append(("❌", "บอทมองไม่เห็นสมาชิก — เปิด SERVER MEMBERS INTENT ใน Developer Portal"))
    out += check_channel(guild, cfg.board_channel, "ห้องสรุป ticket (TICKET_BOARD_CHANNEL_ID)", basic)
    if cfg.admin_alert_channel:
        out += check_channel(guild, cfg.admin_alert_channel, "ห้องสรุปรายวัน (ADMIN_ALERT_CHANNEL_ID)", basic)
    out += check_channel(guild, cfg.newbie_channel, "ห้อง newbie (NEWBIE_CHANNEL_ID)", basic)
    if cfg.join_channel and guild.get_channel(cfg.join_channel) is None:
        out.append(("❌", f"JOIN_CHANNEL_ID `{cfg.join_channel}` ไม่เจอ"))
    if cfg.connect_info_channel and guild.get_channel(cfg.connect_info_channel) is None:
        out.append(("❌", f"CONNECT_INFO_CHANNEL_ID `{cfg.connect_info_channel}` ไม่เจอ — ปุ่มไปห้อง server-info จะพัง"))
    out += check_channel(guild, cfg.spin_channel, "ห้องวงล้อ (SPIN_CHANNEL_ID)", basic)
    if cfg.wallet_channel:
        out += check_channel(guild, cfg.wallet_channel, "ห้องกระเป๋าคุกกี้ (private thread)",
                             basic + ["create_private_threads", "manage_threads", "send_messages_in_threads"])
        wch = guild.get_channel(cfg.wallet_channel)
        if isinstance(wch, discord.TextChannel):
            ev = wch.permissions_for(guild.default_role)
            if not (ev.view_channel and ev.read_message_history):
                out.append(("❌", f"{wch.mention}: @everyone ต้องมี View Channel + Read Message History "
                                  "(ไม่งั้นผู้เล่นเปิดกระเป๋าตัวเองไม่ได้)"))
    out += check_channel(guild, cfg.redeem_channel, "ห้องร้านคุกกี้ (REDEEM_CHANNEL_ID)", basic)
    if cfg.redeem_log:
        out += check_channel(guild, cfg.redeem_log, "ห้อง log แลกของ", basic)
    out += check_channel(guild, cfg.ckx_channel, "ห้อง Cookie Express relay (CKX_CHANNEL_ID)", basic)
    if cfg.ckx_channel and not cfg.ckx_relay_bot:
        out.append(("⚠️", "ไม่ได้ตั้ง CKX_RELAY_BOT_ID — ตอนนี้เชื่อทุกบอทในห้อง relay (แนะนำใส่ ID บอท relay)"))
    out.append(("✅", f"faq.json {len(FAQ.nodes)} ข้อ") if FAQ else ("❌", f"faq.json: {FAQ_ERROR}"))
    if cfg.web_enabled:
        out.append(("✅", f"หน้าเว็บร้าน: {cfg.public_url}") if cfg.public_url else
                   ("⚠️", "หน้าเว็บร้านยังไม่มีโดเมน — Railway → Settings → Networking → Generate Domain "
                          "(รูปของในร้านดิสคอร์ดก็ใช้โดเมนนี้)"))
        if web_shop_on():
            out.append(("✅", f"แลกของบนเว็บ: เปิดแล้ว · Developer Portal → OAuth2 → Redirects ต้องมี "
                              f"`{cfg.public_url}/auth/callback`"))
        elif cfg.public_url:
            out.append(("➖", "แลกของบนเว็บ: ยังไม่ได้ตั้ง DISCORD_CLIENT_SECRET — หน้าเว็บเป็นแคตตาล็อกดูอย่างเดียว "
                              "(แลกในดิสแทน)"))
        out += web_editor_check(guild)
    pool = db.spin_pool()
    out.append(("✅", f"วงล้อมีรางวัล {len(pool)} แบบ") if pool else ("➖", "วงล้อยังไม่มีรางวัล (/spin add)"))

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
    app_commands.Choice(name="spin — วงล้อคุกกี้รายวัน", value="spin"),
    app_commands.Choice(name="shop — ร้านแลกของด้วยคุกกี้", value="shop"),
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
    elif kind.value == "spin":
        kwargs["view"] = SpinPanelView()
    elif kind.value == "shop":
        kwargs["view"] = ShopPanelView()
    else:
        if not cfg.donate_enabled:
            return await reply(interaction, "ยังไม่ได้ตั้ง STRIPE_SECRET_KEY")
        kwargs.update(embed=catalog_embed(in_thread=False), view=DonatePanelView())
    try:
        msg = await target.send(**kwargs)
    except discord.HTTPException as e:
        return await reply(interaction, f"ส่งไม่สำเร็จ: `{e.text or e}`")
    if kind.value in ("spin", "shop"):
        db.set_setting(f"panel:{kind.value}", f"{target.id}:{msg.id}")
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
        if not valid_username(name):
            notes.append(f"`{trunc(name, 40)}`: ชื่อมีตัวอักษรพิเศษ — ลบเองในคอนโซลเซิฟ")
            db.wl_deactivate(name)
            continue
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


def _parse_ckx(text: Optional[str]) -> Optional[str]:
    """None = ไม่แก้ · '-' = ลบ · อื่นๆ = รหัส Cookie Express"""
    if text is None:
        return None
    if text.strip() in ("", "-"):
        return ""
    try:
        return ckx_link.normalize_items(text)
    except ValueError as e:
        raise app_commands.AppCommandError(str(e))


@item_group.command(name="add", description="เพิ่มรายการ Donate ใหม่")
@app_commands.describe(code="รหัส (อังกฤษ/ตัวเลข/_ -) เช่น A01", name="ชื่อที่ผู้เล่นเห็น",
                       price="ยอดต่อชิ้น (บาท) เช่น 50", description="คำอธิบายสั้นๆ (ไม่ใส่ก็ได้)",
                       sort="ลำดับในรายการ (เลขน้อยขึ้นก่อน)",
                       cookies="แพ็กคุกกี้: จ่ายแล้วได้คุกกี้กี่ชิ้น (ไม่ใช่แพ็กเว้นไว้)",
                       ckx="รหัส Cookie Express ของในเกม เช่น CX-BKSP-KTPN*2 CV-AMMF-Z6LF (จ่ายแล้วส่งเข้าเกมเอง)")
async def cmd_item_add(interaction: discord.Interaction, code: str, name: str, price: str,
                       description: Optional[str] = None, sort: Optional[int] = 0,
                       cookies: Optional[app_commands.Range[int, 0, 10_000_000]] = 0, ckx: Optional[str] = None):
    if not await require(interaction, is_admin):
        return
    code = code.strip()
    if not ITEM_CODE_RE.fullmatch(code) or code.upper() == TOPUP_CODE:
        return await reply(interaction, "รหัสใช้ได้แค่อังกฤษ ตัวเลข _ - ยาวไม่เกิน 20 ตัว (ห้ามใช้ TOPUP)")
    if db.item_get(code):
        return await reply(interaction, f"รหัส `{code}` มีอยู่แล้ว — ใช้ /item edit แทน")
    satang = _parse_price(price)
    ckx_items = _parse_ckx(ckx) or ""
    if ckx_items and ckx_link.max_count(ckx_items) * cfg.donate_max_qty > ckx_link.MAX_COUNT:
        return await reply(interaction, f"จำนวนในรหัส × จำนวนสูงสุดต่อรายการ ({cfg.donate_max_qty}) ต้องไม่เกิน "
                                        f"{ckx_link.MAX_COUNT} — ลดจำนวนในรหัส หรือตั้ง DONATE_MAX_QTY ให้น้อยลง")
    db.item_add(code, trunc(name.strip(), 80), satang, trunc((description or "").strip(), 200), sort or 0,
                cookies=cookies or 0, ckx=ckx_items)
    extra = (f" · ได้ {fmt_cookies(cookies)}" if cookies else "") + (f" · ส่งเข้าเกม `{ckx_items}`" if ckx_items else "")
    await reply(interaction, f"เพิ่ม `{code}` **{name}** — {fmt_baht(satang)}{extra} แล้ว")
    await mod_log(interaction.guild, f"🧾 {interaction.user.mention} เพิ่มรายการ `{code}` {name} {fmt_baht(satang)}")


async def item_code_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=trunc(f"{i['code']} · {i['name']} · {fmt_baht(i['price'])}"
                                           + ("" if i["active"] else " (ปิด)"), 100), value=i["code"])
            for i in db.items(active_only=False) if current.casefold() in (i["code"] + i["name"]).casefold()][:25]


@item_group.command(name="edit", description="แก้รายการ Donate (ใส่เฉพาะช่องที่จะแก้)")
@app_commands.describe(code="รหัสเดิม", new_code="เปลี่ยนรหัสเป็น", name="ชื่อใหม่", price="ยอดต่อชิ้นใหม่ (บาท)",
                       description="คำอธิบายใหม่ (ใส่ - เพื่อลบ)", active="เปิดให้ Donate ไหม", sort="ลำดับ",
                       cookies="แพ็กคุกกี้: ได้กี่ชิ้น (0 = ไม่ใช่แพ็ก)", ckx="รหัส Cookie Express (ใส่ - เพื่อลบ)")
@app_commands.autocomplete(code=item_code_autocomplete)
async def cmd_item_edit(interaction: discord.Interaction, code: str, new_code: Optional[str] = None,
                        name: Optional[str] = None, price: Optional[str] = None,
                        description: Optional[str] = None, active: Optional[bool] = None,
                        sort: Optional[int] = None, cookies: Optional[app_commands.Range[int, 0, 10_000_000]] = None,
                        ckx: Optional[str] = None):
    if not await require(interaction, is_admin):
        return
    item = db.item_get(code)
    if item is None:
        return await reply(interaction, f"ไม่พบรหัส `{code}`")
    new_ckx = _parse_ckx(ckx)
    if new_ckx and ckx_link.max_count(new_ckx) * cfg.donate_max_qty > ckx_link.MAX_COUNT:
        return await reply(interaction, f"จำนวนในรหัส × {cfg.donate_max_qty} ต้องไม่เกิน {ckx_link.MAX_COUNT}")
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
                   active=int(active) if active is not None else None, sort=sort, cookies=cookies,
                   ckx=new_ckx)
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
    drop_item_image(item["image"])
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
            + (f" · 🍪 {i['cookies']:,}" if i["cookies"] else "") + (f" · 📦 `{i['ckx']}`" if i["ckx"] else "")
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


# ---------- /setting (ข้อความที่แก้ได้ใน Discord) ----------

setting_group = app_commands.Group(name="setting", description="ตั้งค่าที่แก้ได้ใน Discord (แอดมิน)", guild_only=True,
                               default_permissions=ADMIN_PERMS)


@setting_group.command(name="joininfo", description="แก้ข้อความวิธีเข้าเซิฟ (บอทแปะตอนอนุมัติ White List)")
async def cmd_setting_joininfo(interaction: discord.Interaction):
    if not await require(interaction, is_admin):
        return
    await interaction.response.send_modal(TextSettingModal(
        "joininfo", "วิธีเข้าเซิฟ", DEFAULT_JOININFO, hint="{server_info} {collection}"))


@setting_group.command(name="remind_text", description="แก้ข้อความเตือนคนที่ยังไม่ขอ White List")
async def cmd_setting_remind(interaction: discord.Interaction):
    if not await require(interaction, is_admin):
        return
    await interaction.response.send_modal(TextSettingModal(
        "remind_text", "ข้อความเตือนขอ White List", DEFAULT_REMIND_TEXT, hint="{join}"))


@setting_group.command(name="cookie_rate", description="เติมคุกกี้ผ่าน Donate: 1 บาท ได้กี่คุกกี้ (0 = ปิด)")
async def cmd_setting_rate(interaction: discord.Interaction, cookies_per_baht: app_commands.Range[int, 0, 100_000]):
    if not await require(interaction, is_admin):
        return
    db.set_setting("cookie_rate", cookies_per_baht)
    await update_panel("shop", ShopPanelView)
    await reply(interaction, f"ตั้งแล้ว: 1 บาท = {fmt_cookies(cookies_per_baht)}" if cookies_per_baht else
                "ปิดการเติมคุกกี้ตามยอดแล้ว (แพ็กคุกกี้ใน /item ยังใช้ได้)")


@setting_group.command(name="show", description="ดูค่าที่ตั้งไว้")
async def cmd_setting_show(interaction: discord.Interaction):
    if not await require(interaction, is_admin):
        return
    rate = int(db.setting("cookie_rate", "0") or 0)
    embed = discord.Embed(title="ค่าที่ตั้งไว้", color=COLOR_INFO)
    embed.add_field(name="เติมคุกกี้", value=f"1 บาท = {fmt_cookies(rate)}" if rate else "ปิด", inline=False)
    embed.add_field(name="วิธีเข้าเซิฟ", value=trunc(db.setting("joininfo") or "(ค่าเริ่มต้น)", 1000), inline=False)
    embed.add_field(name="ข้อความเตือน WL", value=trunc(db.setting("remind_text") or "(ค่าเริ่มต้น)", 1000), inline=False)
    embed.add_field(name="หน้าเว็บ", value=cfg.public_url or "ยังไม่มีโดเมน (Railway → Networking → Generate Domain)",
                    inline=False)
    await reply(interaction, embed=embed)


async def update_panel(kind: str, view_cls):
    ref = db.setting(f"panel:{kind}")
    guild = bot.get_guild(cfg.guild_id)
    if not ref or guild is None:
        return
    channel_id, msg_id = (int(x) for x in ref.split(":"))
    channel = guild.get_channel(channel_id)
    if channel is None:
        return
    try:
        await channel.get_partial_message(msg_id).edit(view=view_cls())
    except discord.HTTPException as e:
        log.warning("อัปเดตป้าย %s ไม่ได้: %s", kind, e)


# ---------- /spin (วงล้อรายวัน) ----------

spin_group = app_commands.Group(name="spin", description="วงล้อคุกกี้รายวัน (แอดมิน)", guild_only=True,
                            default_permissions=ADMIN_PERMS)


def pool_list_text() -> str:
    pool = db.spin_pool(active_only=False)
    total = sum(p["weight"] for p in pool if p["active"] and p["weight"] > 0) or 1
    if not pool:
        return "ยังไม่มีรางวัล — เพิ่มด้วย /spin add"
    rows = []
    for p in pool:
        pct = p["weight"] / total * 100 if p["active"] else 0
        rows.append(f"{'🟢' if p['active'] else '⚫'} `#{p['id']}` {discord.utils.escape_markdown(p['label'])} · "
                    f"**{fmt_cookies(p['cookies'])}** · น้ำหนัก {p['weight']} ({pct:.1f}%)")
    expected = sum(p["cookies"] * p["weight"] for p in pool if p["active"] and p["weight"] > 0) / total
    return "\n".join(rows) + f"\n\nเฉลี่ยต่อการหมุน ≈ **{expected:,.1f} 🍪** · ต่อเดือน ≈ {expected * 30:,.0f} 🍪/คน"


async def pool_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=trunc(f"#{p['id']} {p['label']} · {p['cookies']} คุกกี้ · น้ำหนัก {p['weight']}", 100),
                                value=p["id"]) for p in db.spin_pool(active_only=False)
            if current.casefold() in f"{p['id']} {p['label']}".casefold()][:25]


@spin_group.command(name="add", description="เพิ่มรางวัลในวงล้อ (น้ำหนักมาก = ออกบ่อย)")
@app_commands.describe(label="ชื่อรางวัล เช่น คุกกี้ชิ้นเล็ก", cookies="ได้กี่คุกกี้", weight="น้ำหนัก เช่น 60")
async def cmd_spin_add(interaction: discord.Interaction, label: str, cookies: app_commands.Range[int, 0, 1_000_000],
                       weight: app_commands.Range[int, 0, 1_000_000]):
    if not await require(interaction, is_admin):
        return
    db.spin_pool_add(trunc(label.strip(), 60), cookies, weight)
    await update_panel("spin", SpinPanelView)
    await reply(interaction, embed=discord.Embed(title="วงล้อคุกกี้", description=pool_list_text(), color=COLOR_COOKIE))


@spin_group.command(name="edit", description="แก้รางวัลในวงล้อ (ใส่เฉพาะช่องที่จะแก้)")
@app_commands.autocomplete(prize=pool_autocomplete)
@app_commands.describe(prize="รางวัล", label="ชื่อใหม่", cookies="คุกกี้", weight="น้ำหนัก", active="เปิดใช้ไหม")
async def cmd_spin_edit(interaction: discord.Interaction, prize: int, label: Optional[str] = None,
                        cookies: Optional[app_commands.Range[int, 0, 1_000_000]] = None,
                        weight: Optional[app_commands.Range[int, 0, 1_000_000]] = None, active: Optional[bool] = None):
    if not await require(interaction, is_admin):
        return
    if db.spin_pool_get(prize) is None:
        return await reply(interaction, "ไม่พบรางวัลนี้")
    db.spin_pool_update(prize, label=trunc(label.strip(), 60) if label else None, cookies=cookies, weight=weight,
                        active=int(active) if active is not None else None)
    await update_panel("spin", SpinPanelView)
    await reply(interaction, embed=discord.Embed(title="วงล้อคุกกี้", description=pool_list_text(), color=COLOR_COOKIE))


@spin_group.command(name="remove", description="ลบรางวัลออกจากวงล้อ")
@app_commands.autocomplete(prize=pool_autocomplete)
async def cmd_spin_remove(interaction: discord.Interaction, prize: int):
    if not await require(interaction, is_admin):
        return
    if not db.spin_pool_delete(prize):
        return await reply(interaction, "ไม่พบรางวัลนี้")
    await update_panel("spin", SpinPanelView)
    await reply(interaction, embed=discord.Embed(title="วงล้อคุกกี้", description=pool_list_text(), color=COLOR_COOKIE))


@spin_group.command(name="list", description="ดูรางวัลทั้งหมดพร้อมโอกาสออก")
async def cmd_spin_list(interaction: discord.Interaction):
    if not await require(interaction, is_admin):
        return
    await reply(interaction, embed=discord.Embed(title="วงล้อคุกกี้", description=pool_list_text(), color=COLOR_COOKIE))


@spin_group.command(name="reset", description="ให้คนนี้หมุนวันนี้ได้อีกครั้ง (คุกกี้ที่ได้ไปแล้วไม่หาย)")
async def cmd_spin_reset(interaction: discord.Interaction, member: discord.Member):
    if not await require(interaction, is_admin):
        return
    day = today_key()
    with db.conn:
        db.conn.execute("UPDATE ledger SET ref = ref || '-r' || id WHERE discord_id=? AND kind='spin' AND ref=?",
                        (member.id, day))
    ok = db.spin_reset(member.id, day)
    await reply(interaction, f"{member.mention} หมุนวันนี้ได้อีกครั้งแล้ว" if ok else f"{member.mention} วันนี้ยังไม่ได้หมุน")


# ---------- /shop (ร้านแลกของด้วยคุกกี้) ----------

shop_group = app_commands.Group(name="shop", description="ร้านแลกของด้วยคุกกี้ (แอดมิน)", guild_only=True,
                            default_permissions=ADMIN_PERMS)


async def shop_code_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=trunc(f"{i['code']} · {i['name']} · {i['price']:,} คุกกี้"
                                           + ("" if i["active"] else " (ปิด)"), 100), value=i["code"])
            for i in db.shop_items(active_only=False) if current.casefold() in (i["code"] + i["name"]).casefold()][:25]


def shop_item_text(i) -> str:
    when = []
    if i["start_at"]:
        when.append(f"เริ่ม {fmt_time(i['start_at'])}")
    if i["end_at"]:
        when.append(f"ถึง {fmt_time(i['end_at'])}")
    return (f"{'🟢' if i['active'] else '⚫'} `{i['code']}` **{discord.utils.escape_markdown(i['name'])}** — "
            f"{fmt_cookies(i['price'])}"
            + (f" · หมวด {i['category']}" if i["category"] else "")
            + (f" · จำกัด {i['per_user_limit']}/คน" if i["per_user_limit"] else "")
            + (f" · สต็อก {i['stock']}" if i["stock"] >= 0 else "")
            + (" · " + " ".join(when) if when else "")
            + (f"\n　📦 `{i['ckx']}`" if i["ckx"] else "\n　🙋 ไม่มีรหัส Cookie Express (แอดมินส่งเอง)")
            + (" · 🖼️" if i["image"] else ""))


@shop_group.command(name="add", description="เพิ่มของในร้านคุกกี้")
@app_commands.describe(code="รหัสของ (อังกฤษ/ตัวเลข/_ -)", name="ชื่อที่ผู้เล่นเห็น", price="ใช้กี่คุกกี้",
                       ckx="รหัส Cookie Express เช่น CX-BKSP-KTPN หรือ CV-AMMF-Z6LF*1 (ไม่ใส่ = แอดมินส่งเอง)",
                       description="คำอธิบาย", category="หมวด เช่น สกิน / อาวุธ / รถ",
                       limit="คนหนึ่งแลกได้กี่ชิ้น (0 = ไม่จำกัด)", stock="มีทั้งหมดกี่ชิ้น (-1 = ไม่จำกัด)",
                       start="เริ่มแลกได้ เช่น 2026-10-25 หรือ 25/10/2026 18:00", end="แลกได้ถึง เช่น 31/10/2026",
                       image="รูปของ (png/jpg/webp/gif)", sort="ลำดับ (เลขน้อยขึ้นก่อน)")
async def cmd_shop_add(interaction: discord.Interaction, code: str, name: str,
                       price: app_commands.Range[int, 1, 100_000_000], ckx: Optional[str] = None,
                       description: Optional[str] = None, category: Optional[str] = None,
                       limit: Optional[app_commands.Range[int, 0, 999]] = 0,
                       stock: Optional[app_commands.Range[int, -1, 1_000_000]] = -1,
                       start: Optional[str] = None, end: Optional[str] = None,
                       image: Optional[discord.Attachment] = None, sort: Optional[int] = 0):
    if not await require(interaction, is_admin):
        return
    code = code.strip()
    if not ITEM_CODE_RE.fullmatch(code):
        return await reply(interaction, "รหัสใช้ได้แค่อังกฤษ ตัวเลข _ - ยาวไม่เกิน 20 ตัว")
    if db.shop_get(code):
        return await reply(interaction, f"รหัส `{code}` มีอยู่แล้ว — ใช้ /shop edit")
    await interaction.response.defer(ephemeral=True, thinking=True)
    start_at, end_at = parse_when(start), parse_when(end, end=True)
    if start_at and end_at and end_at <= start_at:
        return await interaction.followup.send("วันจบต้องหลังวันเริ่ม", ephemeral=True)
    image_name = await save_item_image(code, image) if image else ""
    db.shop_add(code=code, name=trunc(name.strip(), 80), description=trunc((description or "").strip(), 500),
                price=price, ckx=_parse_ckx(ckx) or "", category=trunc((category or "").strip(), 40),
                image=image_name, per_user_limit=limit or 0, stock=-1 if stock is None else stock,
                start_at=start_at.isoformat() if start_at else "", end_at=end_at.isoformat() if end_at else "",
                sort=sort or 0)
    await interaction.followup.send("เพิ่มแล้ว\n" + shop_item_text(db.shop_get(code)), ephemeral=True)
    await mod_log(interaction.guild, f"🛍️ {interaction.user.mention} เพิ่มของในร้าน `{code}` {name} {fmt_cookies(price)}")


@shop_group.command(name="edit", description="แก้ของในร้าน (ใส่เฉพาะช่องที่จะแก้ · ข้อความใส่ - เพื่อลบ)")
@app_commands.autocomplete(code=shop_code_autocomplete)
@app_commands.describe(code="ของที่จะแก้", new_code="เปลี่ยนรหัสเป็น", name="ชื่อ", price="คุกกี้",
                       ckx="รหัส Cookie Express (- = ลบ)", description="คำอธิบาย (- = ลบ)", category="หมวด (- = ลบ)",
                       limit="ต่อคน (0 = ไม่จำกัด)", stock="สต็อก (-1 = ไม่จำกัด)", start="เริ่ม (- = ลบ)",
                       end="ถึง (- = ลบ)", image="รูปใหม่", active="เปิดในร้านไหม", sort="ลำดับ")
async def cmd_shop_edit(interaction: discord.Interaction, code: str, new_code: Optional[str] = None,
                        name: Optional[str] = None, price: Optional[app_commands.Range[int, 1, 100_000_000]] = None,
                        ckx: Optional[str] = None, description: Optional[str] = None, category: Optional[str] = None,
                        limit: Optional[app_commands.Range[int, 0, 999]] = None,
                        stock: Optional[app_commands.Range[int, -1, 1_000_000]] = None,
                        start: Optional[str] = None, end: Optional[str] = None,
                        image: Optional[discord.Attachment] = None, active: Optional[bool] = None,
                        sort: Optional[int] = None):
    if not await require(interaction, is_admin):
        return
    item = db.shop_get(code)
    if item is None:
        return await reply(interaction, f"ไม่พบ `{code}`")
    if new_code is not None:
        new_code = new_code.strip()
        clash = db.shop_get(new_code)
        if not ITEM_CODE_RE.fullmatch(new_code) or (clash and clash["code"].casefold() != item["code"].casefold()):
            return await reply(interaction, "รหัสใหม่ใช้ไม่ได้ หรือซ้ำกับของอื่น")
    await interaction.response.defer(ephemeral=True, thinking=True)

    def text(v, n):
        return None if v is None else ("" if v.strip() == "-" else trunc(v.strip(), n))

    start_at = None if start is None else (parse_when(start) or "")
    end_at = None if end is None else (parse_when(end, end=True) or "")
    image_name = await save_item_image(new_code or item["code"], image) if image else None
    if image_name and item["image"] and item["image"] != image_name:
        drop_item_image(item["image"])
    db.shop_update(item["code"], code=new_code, name=text(name, 80), price=price, ckx=_parse_ckx(ckx),
                   description=text(description, 500), category=text(category, 40), per_user_limit=limit, stock=stock,
                   start_at=start_at.isoformat() if start_at else start_at,
                   end_at=end_at.isoformat() if end_at else end_at, image=image_name,
                   active=int(active) if active is not None else None, sort=sort)
    await interaction.followup.send("แก้แล้ว\n" + shop_item_text(db.shop_get(new_code or item["code"])), ephemeral=True)


@shop_group.command(name="remove", description="ลบของออกจากร้าน (ใบแลกเก่ายังอยู่)")
@app_commands.autocomplete(code=shop_code_autocomplete)
async def cmd_shop_remove(interaction: discord.Interaction, code: str):
    if not await require(interaction, is_admin):
        return
    item = db.shop_get(code)
    if item is None or not db.shop_delete(item["code"]):
        return await reply(interaction, f"ไม่พบ `{code}`")
    drop_item_image(item["image"])
    await reply(interaction, f"ลบ `{item['code']}` {item['name']} แล้ว")


@shop_group.command(name="list", description="ดูของในร้านทั้งหมด")
async def cmd_shop_list(interaction: discord.Interaction):
    if not await require(interaction, is_admin):
        return
    items = db.shop_items(active_only=False)
    text = "\n".join(shop_item_text(i) for i in items) or "ยังไม่มีของ — เพิ่มด้วย /shop add"
    footer = f"หน้าเว็บ: {cfg.public_url}" if cfg.public_url else "ยังไม่มีหน้าเว็บ (ตั้งโดเมนใน Railway)"
    await reply(interaction, embed=discord.Embed(title=f"ร้านคุกกี้ ({len(items)})", description=trunc(text, 4000),
                                                 color=COLOR_COOKIE).set_footer(text=footer))


# ---------- /cookies ----------

cookies_group = app_commands.Group(name="cookies", description="คุกกี้ของผู้เล่น (แอดมิน)", guild_only=True,
                               default_permissions=ADMIN_PERMS)


@cookies_group.command(name="give", description="ให้คุกกี้ (เช่น รางวัลกิจกรรม)")
async def cmd_cookies_give(interaction: discord.Interaction, member: discord.Member,
                           amount: app_commands.Range[int, 1, 100_000_000], note: Optional[str] = None):
    if not await require(interaction, is_admin):
        return
    _, balance = db.cookies_add(member.id, amount, "admin", note=trunc(note or "", 80), by=interaction.user.id)
    await reply(interaction, f"ให้ {member.mention} {fmt_cookies(amount)} แล้ว · ตอนนี้มี {fmt_cookies(balance)}")
    await mod_log(interaction.guild, f"🎁 {interaction.user.mention} ให้ {member.mention} {fmt_cookies(amount)}"
                                     + (f" — {note}" if note else ""))
    await refresh_wallet(interaction.guild, member.id)


@cookies_group.command(name="take", description="หักคุกกี้")
async def cmd_cookies_take(interaction: discord.Interaction, member: discord.Member,
                           amount: app_commands.Range[int, 1, 100_000_000], note: Optional[str] = None):
    if not await require(interaction, is_admin):
        return
    ok, balance = db.cookies_add(member.id, -amount, "take", note=trunc(note or "", 80), by=interaction.user.id)
    if not ok:
        w = db.wallet_ensure(member.id)
        return await reply(interaction, f"{member.mention} มีแค่ {fmt_cookies(w['balance'])}")
    await reply(interaction, f"หัก {member.mention} {fmt_cookies(amount)} แล้ว · เหลือ {fmt_cookies(balance)}")
    await mod_log(interaction.guild, f"➖ {interaction.user.mention} หักคุกกี้ {member.mention} {fmt_cookies(amount)}"
                                     + (f" — {note}" if note else ""))
    await refresh_wallet(interaction.guild, member.id)


@cookies_group.command(name="balance", description="ดูคุกกี้และประวัติของคนนี้")
async def cmd_cookies_balance(interaction: discord.Interaction, member: discord.Member):
    if not await require(interaction, is_admin):
        return
    w = db.wallet_ensure(member.id)
    hist = "\n".join(f"`{e['delta']:+,}` {LEDGER_TH.get(e['kind'], e['kind'])} {trunc(e['note'], 40)} · "
                     f"{fmt_time(e['created_at'])}" for e in db.ledger_recent(member.id, 12)) or "ยังไม่มี"
    embed = discord.Embed(title=f"🍪 {member.display_name}: {fmt_cookies(w['balance'])}", description=hist,
                          color=COLOR_COOKIE)
    embed.add_field(name="ชื่อในเกม", value=w["ingame"] or "—")
    if w["thread_id"]:
        embed.add_field(name="กระเป๋า", value=f"<#{w['thread_id']}>")
    await reply(interaction, embed=embed)


# ---------- /redeem (ใบแลกของ) ----------

redeem_group = app_commands.Group(name="redeem", description="ใบแลกของด้วยคุกกี้ (ทีมแอดมิน)", guild_only=True,
                              default_permissions=STAFF_PERMS)


@redeem_group.command(name="list", description="ใบแลกล่าสุด")
@app_commands.describe(problem_only="ดูเฉพาะที่ต้องให้แอดมินจัดการ")
async def cmd_redeem_list(interaction: discord.Interaction, problem_only: Optional[bool] = False):
    if not await require(interaction, is_staff):
        return
    rows = db.redemptions_recent(25, ("problem", "failed", "manual", "posting") if problem_only else None)
    text = "\n".join(f"{REDEEM_STATUS.get(r['status'], ('•', ''))[0]} `RD-{r['id']:04d}` <@{r['discord_id']}> "
                     f"{discord.utils.escape_markdown(r['name'])} × {r['qty']} — "
                     f"{REDEEM_STATUS.get(r['status'], ('', r['status']))[1]} · {fmt_time(r['created_at'])}"
                     for r in rows) or "ไม่มี"
    await reply(interaction, embed=discord.Embed(title="ใบแลกของ", description=trunc(text, 4000), color=COLOR_COOKIE))


@redeem_group.command(name="action", description="คืนคุกกี้ / ส่งเข้าเกมอีกครั้ง / บันทึกว่าส่งให้แล้ว")
@app_commands.describe(redeem_id="เลขใบแลก (ตัวเลขหลัง RD-)", action="ทำอะไร")
@app_commands.choices(action=[app_commands.Choice(name="คืนคุกกี้", value="refund"),
                              app_commands.Choice(name="ส่งเข้าเกมอีกครั้ง", value="resend"),
                              app_commands.Choice(name="บันทึกว่าส่งให้แล้ว", value="done")])
async def cmd_redeem_action(interaction: discord.Interaction, redeem_id: int, action: app_commands.Choice[str]):
    if not await require(interaction, is_staff):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    msg = await redeem_admin_action(interaction.guild, action.value, redeem_id, interaction.user)
    await interaction.followup.send(msg, ephemeral=True)


# ---------- /remind /board ----------

@bot.tree.command(name="remind", description="สรุปคนที่ยังไม่ขอ White List ตอนนี้เลย (ปกติบอทสรุปให้ทุกวัน)")
@app_commands.default_permissions(manage_guild=True)
async def cmd_remind(interaction: discord.Interaction):
    if not await require(interaction, is_staff):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    msg = await post_remind_card(interaction.guild, manual_by=interaction.user)
    await interaction.followup.send(f"สรุปแล้ว: {msg.jump_url}" if msg else
                                    f"ไม่มีใครค้าง (นับคนไม่มี role เข้ามาเกิน {cfg.wl_remind_after_days} วัน "
                                    f"และไม่ได้เตือนใน {cfg.wl_remind_repeat_days} วันที่ผ่านมา)", ephemeral=True)


@bot.tree.command(name="board", description="อัปเดตห้องสรุป ticket ทันที (สร้างการ์ดใหม่ถ้าถูกลบ)")
@app_commands.default_permissions(manage_guild=True)
async def cmd_board(interaction: discord.Interaction):
    if not await require(interaction, is_staff):
        return
    if not cfg.board_channel:
        return await reply(interaction, "ยังไม่ได้ตั้ง TICKET_BOARD_CHANNEL_ID")
    await interaction.response.defer(ephemeral=True, thinking=True)
    await refresh_board(force=True)
    await interaction.followup.send(f"อัปเดต <#{cfg.board_channel}> แล้ว", ephemeral=True)


for _group in (ticket_group, wl_group, steam_group, item_group, order_group, setting_group, spin_group, shop_group,
               cookies_group, redeem_group):
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
    global cfg, db, rcon, TZ, IMAGES_DIR
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
    IMAGES_DIR = cfg.data_dir / "images"
    load_faq()
    if cfg.rcon_enabled:
        rcon = Rcon(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password)
    try:
        bot.run(cfg.token, log_handler=None)
    except discord.LoginFailure:
        log.error("DISCORD_TOKEN ผิด — Developer Portal → Bot → Reset Token แล้วใส่ใหม่ใน Variables")
        sys.exit(EXIT_CONFIG)
    except discord.PrivilegedIntentsRequired:
        log.error("ต้องเปิด SERVER MEMBERS INTENT และ MESSAGE CONTENT INTENT: "
                  "Developer Portal → Bot → Privileged Gateway Intents")
        sys.exit(EXIT_CONFIG)


if __name__ == "__main__":
    main()
