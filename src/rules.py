"""고정 규칙: 안전 낱말 · 점검표 정렬 · 지연 판단. AC-21 · 29 · 30 · 36"""
from __future__ import annotations

from datetime import date, datetime

from src.common import load_rules


def safety_hits(text: str, rules: dict | None = None) -> list[str]:
    rules = rules or load_rules()
    return [w for w in rules["safety_words"] if w in text]


def higher(a: str, b: str, rules: dict | None = None) -> str:
    """두 등급 중 높은(위험한) 쪽."""
    order = (rules or load_rules())["risk_order"]
    return a if order.index(a or "") <= order.index(b or "") else b


def to_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def is_delayed(due, today: date, rules: dict | None = None) -> bool:
    """목표일에서 delay_days(7)일을 '넘게' 지나면 지연. 7일째는 아님, 8일째부터."""
    d = to_date(due)
    if d is None:
        return False
    return (today - d).days > (rules or load_rules())["delay_days"]


def sort_key(item: dict, rules: dict | None = None):
    """위험도 A → B → C → 빈칸, 같은 등급은 목표일 빠른 순, 목표일 없으면 뒤."""
    rules = rules or load_rules()
    order = rules["risk_order"]
    risk = item.get("risk") or ""
    r = order.index(risk) if risk in order else len(order)
    d = to_date(item.get("due"))
    return (r, d is None, d or date.max, item.get("id", ""))
