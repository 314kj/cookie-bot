"""ต้นไม้ถามตอบของ ticket แจ้งบั๊ก / ติดต่อแอดมิน (อ่านจาก faq.json) — ไม่แตะ Discord"""
import json
import re
from pathlib import Path

SPECIAL = {"@solved", "@admin", "@menu"}
NODE_RE = re.compile(r"^[a-z0-9_]{1,40}$")


class FaqError(Exception):
    pass


class FaqTree:
    def __init__(self, data: dict):
        self.data = data
        self.nodes = data.get("nodes") or {}
        self.start = data.get("start", "menu")
        self.contact_start = data.get("contact_start", self.start)
        self.validate()

    @classmethod
    def load(cls, path) -> "FaqTree":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise FaqError(f"อ่าน {path} ไม่ได้: {e}")
        return cls(data)

    def validate(self):
        problems = []
        for start in (self.start, self.contact_start):
            if start not in self.nodes:
                problems.append(f"ไม่มีข้อเริ่มต้น {start!r}")
        for key, node in self.nodes.items():
            if not NODE_RE.match(key):
                problems.append(f"ชื่อข้อ {key!r} ใช้ได้แค่ a-z 0-9 _")
            nums = [o.get("n") for o in node.get("options", [])]
            if len(nums) != len(set(nums)):
                problems.append(f"{key}: เลขตัวเลือกซ้ำ")
            if len(node.get("options", [])) > 10:
                problems.append(f"{key}: ตัวเลือกเกิน 10")
            for o in node.get("options", []):
                go = o.get("go", "")
                if go not in SPECIAL and go not in self.nodes:
                    problems.append(f"{key}: ตัวเลือก {o.get('n')} ไปข้อ {go!r} ที่ไม่มี")
                if not isinstance(o.get("n"), int) or not 0 <= o["n"] <= 99:
                    problems.append(f"{key}: เลขตัวเลือกต้องเป็น 0–99")
                if len(f"{o.get('n')}. {o.get('label', '')}") > 80:
                    problems.append(f"{key}: ชื่อปุ่ม {o.get('n')} ยาวเกิน 80 ตัว")
        if problems:
            raise FaqError("faq.json มีปัญหา:\n- " + "\n- ".join(problems))

    def node(self, key):
        return self.nodes.get(key)

    def option_by_number(self, key, number: int):
        node = self.nodes.get(key) or {}
        for o in node.get("options", []):
            if o.get("n") == number:
                return o
        return None

    def title_of(self, key) -> str:
        node = self.nodes.get(key) or {}
        return node.get("title") or key

    def images(self, key) -> list:
        return list((self.nodes.get(key) or {}).get("images", []))[:4]


def fill(text: str, values: dict) -> str:
    """แทน {server_info} {collection} {join} ฯลฯ เฉพาะตัวที่รู้จัก (ปีกกาอื่นปล่อยไว้)"""
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


def typed_number(text: str):
    """ผู้เล่นพิมพ์ '1', '1.', ' 0 ', 'ข้อ 3' → เลข / None"""
    m = re.fullmatch(r"\s*(?:ข้อ\s*)?(\d{1,2})\s*[.)]?\s*", text or "")
    return int(m.group(1)) if m else None
