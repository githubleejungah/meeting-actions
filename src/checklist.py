"""지난 일 점검표: 닫히지 않은 할 일 · 이슈를 위험도 순 정렬, 7일 넘긴 지연 표시. 대장은 바꾸지 않는다.
AC-13 · 14 · 21 · 36

사용: python -m src.checklist [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
from datetime import date

from src import ledger
from src.common import data_dir, load_rules
from src.rules import is_delayed, sort_key, to_date


def build(led: dict, today: date, rules: dict | None = None) -> list[dict]:
    rules = rules or load_rules()
    items = []
    for t in led["todos"]:
        if t.get("상태") == rules["todo_closed"]:
            continue
        items.append({"kind": "할 일", "id": t["번호"], "text": t["할 일"], "owner": t.get("담당", ""),
                      "risk": t.get("위험도", ""), "status": t.get("상태", ""), "due": t.get("목표일", "")})
    for i in led["issues"]:
        if i.get("상태") == rules["issue_closed"]:
            continue
        items.append({"kind": "이슈", "id": i["번호"], "text": i.get("증상", ""), "owner": "",
                      "risk": i.get("위험도", ""), "status": i.get("상태", ""), "due": i.get("목표일", ""),
                      "verdict": i.get("판정", "")})
    for it in items:
        d = to_date(it["due"])
        it["due"] = d.isoformat() if d else (it["due"] or "")
        it["delayed"] = is_delayed(it["due"], today, rules)
    return sorted(items, key=lambda x: sort_key(x, rules))


def table(items: list[dict]) -> str:
    L = ["| 위험도 | 번호 | 내용 | 담당 | 상태 | 목표일 | 지연 |", "|---|---|---|---|---|---|---|"]
    for it in items:
        L.append(f"| {it['risk'] or '-'} | {it['id']} | {it['text']} | {it['owner']} | {it['status']} | {it['due']} | {'지연' if it['delayed'] else ''} |")
    if not items:
        L.append("| - | - | 닫히지 않은 항목 없음 | | | | |")
    return "\n".join(L)


if __name__ == "__main__":
    from src.common import utf8_stdout
    utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--today")
    a = ap.parse_args()
    today = to_date(a.today) if a.today else date.today()
    print(table(build(ledger.read(data_dir() / "ledger.xlsx"), today)))
