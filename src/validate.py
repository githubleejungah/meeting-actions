"""초안 JSON 검사. 고쳐 쓰지 않고 떨어진 항목과 이유만 낸다.
예외 하나: 안전 낱말이 있으면 위험도 '제안'을 A로 올리고 이유를 남긴다(AC-29).

사용: python -m src.validate <drafts/xxx.json>
  → drafts/xxx.checked.json 저장, 초안 표(마크다운) 출력. 떨어진 항목이 있으면 exit 2.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from src import ledger
from src.common import data_dir, load_rules, read_text, squash
from src.mask import has_phone
from src.parse import times_in
from src.rules import higher, safety_hits

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _human_fields(obj: dict, rules: dict) -> list[str]:
    return [k for k in rules["human_fields"] if k in obj and obj[k] not in (None, "", [])]


def _quote_ok(quote, source: str) -> bool:
    """인용은 문자열 하나 또는 여러 조각(list). 모든 조각이 원문에 글자 그대로 있어야 한다."""
    parts = quote if isinstance(quote, list) else [quote]
    return bool(parts) and all(p and squash(p) in squash(source) for p in parts)


def _date_ok(v, unknown: str) -> bool:
    return v == unknown or bool(DATE.match(str(v)))


def validate_meeting(draft: dict, source: str, led: dict, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    U = rules["unknown"]
    times = times_in(source)
    issue_ids = {r["번호"] for r in led["issues"]}
    kept, rejected = [], []
    for t in draft.get("todos", []):
        why = []
        ev = t.get("evidence_times") or []
        if not ev:
            why.append("근거 시각 없음")
        bad = [x for x in ev if x not in times]
        if bad:
            why.append(f"원문에 없는 시각 {bad}")
        if not _quote_ok(t.get("quote"), source):
            why.append("인용이 원문에 없음")
        owner = t.get("owner", U)
        if owner != U and squash(owner) not in squash(source):
            why.append(f"담당 '{owner}'이(가) 원문에 없음")
        if not _date_ok(t.get("due", U), U):
            why.append("목표일 형식(YYYY-MM-DD 또는 미정) 아님")
        hf = _human_fields(t, rules)
        if hf:
            why.append(f"사람 칸에 값이 있음 {hf}")
        rel = t.get("related_issue")
        if rel and rel not in issue_ids:
            why.append(f"대장에 없는 이슈 번호 {rel}")
        (rejected if why else kept).append({**t, "reasons": why} if why else t)
    for sec in ("agenda", "decisions", "open_items"):
        for it in draft.get(sec, []):
            bad = [x for x in it.get("quotes", []) if x not in times]
            if bad:
                rejected.append({"section": sec, "text": it.get("title") or it.get("text"), "reasons": [f"원문에 없는 시각 {bad}"]})
    sections = {s: [it for it in draft.get(s, []) if not [x for x in it.get("quotes", []) if x not in times]]
                for s in ("agenda", "decisions", "open_items")}
    return {**draft, **sections, "todos": kept, "rejected": rejected, "notes": []}


def validate_issue(draft: dict, led: dict, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    U = rules["unknown"]
    closed = rules["issue_closed"]
    issues = {r["번호"]: r for r in led["issues"]}
    open_ids = {k for k, r in issues.items() if r.get("상태") != closed}
    target = draft.get("append_to")
    kept, rejected, notes = [], [], []
    if target and target not in open_ids:
        return {**draft, "items": [], "rejected": [{"reasons": [f"{target}이(가) 대장에 없거나 닫힘"]}], "notes": []}
    for it in draft.get("items", []):
        why = []
        src = it.get("masked_text", "")
        if has_phone(src):
            why.append("가린 원문에 전화번호가 남아 있음")
        if it.get("route", U) not in rules["routes"]:
            why.append(f"접수 경로 '{it.get('route')}'이(가) 목록 밖")
        missing = []
        for f in ("condition", "symptom", "expected"):
            v = it.get(f) or {"value": U, "quote": None}
            if v.get("value") == U:
                missing.append(f)
            elif not _quote_ok(v.get("quote"), src):
                why.append(f"{f} 인용이 원문에 없음")
        rs = it.get("risk_suggestion") or {}
        if target:  # 덧붙이기는 위험도 제안 · 질문을 새로 만들지 않는다
            pass
        elif rs.get("grade") not in ("A", "B", "C"):
            why.append("위험도 제안이 A/B/C 아님")
        elif not _quote_ok(rs.get("quote"), src):
            why.append("위험도 근거 인용이 원문에 없음")
        hits = safety_hits(src, rules)
        if hits and not target and rs.get("grade") in ("B", "C"):
            it = {**it, "risk_suggestion": {**rs, "grade": higher("A", rs["grade"], rules), "safety_word": hits[0],
                                            "raised_from": rs["grade"]}}
            notes.append(f"{it.get('msg_id', '')}: 안전 낱말 '{hits[0]}' → 위험도 제안을 {rs['grade']}에서 A로 올림")
        q = it.get("questions") or []
        if len(q) > rules["max_questions"]:
            why.append(f"되물을 질문 {len(q)}개(최대 {rules['max_questions']})")
        if missing and not target and not q:
            why.append("'미정' 칸이 있는데 되물을 질문이 없음")
        dup = it.get("duplicate_of") or []
        bad = [d for d in dup if d not in open_ids]
        if bad:
            why.append(f"중복 의심 번호가 대장에 없거나 닫힘 {bad}")
        hf = _human_fields(it, rules)
        if hf:
            why.append(f"사람 칸에 값이 있음 {hf}")
        if target:
            row = issues[target]
            col = {"condition": "재현 조건", "symptom": "증상", "expected": "기대 결과"}
            touched = [c for f, c in col.items() if (it.get(f) or {}).get("value", U) != U and row.get(c) != U]
            if touched:
                why.append(f"'미정'이 아닌 칸을 바꾸려 함 {touched}")
        (rejected if why else kept).append({**it, "reasons": why} if why else it)
    return {**draft, "items": kept, "rejected": rejected, "notes": notes}


def table(checked: dict) -> str:
    """사용자에게 보여 줄 초안 표(마크다운)."""
    L = []
    if checked["kind"] == "meeting":
        L.append("| # | 할 일 | 담당 | 목표일 | 근거 시각 | 관련 이슈 |\n|---|---|---|---|---|---|")
        for i, t in enumerate(checked["todos"], 1):
            L.append(f"| {i} | {t['task']} | {t.get('owner')} | {t.get('due')} | {', '.join(t['evidence_times'])} | {t.get('related_issue') or ''} |")
        if not checked["todos"]:
            L.append("| - | 할 일 없음 | | | | |")
    else:
        L.append("| # | 경로 | 재현 조건 | 증상 | 기대 결과 | 위험도 제안(미리 판단 아님) | 되물을 질문 | 중복 의심 |\n|---|---|---|---|---|---|---|---|")
        for i, it in enumerate(checked["items"], 1):
            rs = it.get("risk_suggestion") or {"grade": "-", "quote": "덧붙이기"}
            L.append(f"| {it.get('msg_id', i)} | {it['route']} | {it['condition']['value']} | {it['symptom']['value']} | "
                     f"{it['expected']['value']} | {rs['grade']} — \"{rs['quote'] if isinstance(rs['quote'], str) else ' … '.join(rs['quote'])}\" | {' / '.join(it.get('questions') or [])} | "
                     f"{', '.join(it.get('duplicate_of') or [])} |")
    for n in checked.get("notes", []):
        L.append(f"\n- 규칙: {n}")
    if checked["rejected"]:
        L.append("\n검사 탈락:")
        for r in checked["rejected"]:
            L.append(f"- {r.get('task') or r.get('msg_id') or r.get('text') or ''}: {'; '.join(r['reasons'])}")
    return "\n".join(L)


def run(draft_path: Path, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    led = ledger.read(data_dir() / "ledger.xlsx")
    if draft["kind"] == "meeting":
        src = read_text(Path(draft["source_file"]) if Path(draft["source_file"]).is_absolute()
                        else data_dir() / draft["source_file"])
        checked = validate_meeting(draft, src, led, rules)
    else:
        checked = validate_issue(draft, led, rules)
    out = draft_path.with_name(draft_path.stem + ".checked.json")
    out.write_text(json.dumps(checked, ensure_ascii=False, indent=2), encoding="utf-8")
    checked["_path"] = str(out)
    return checked


if __name__ == "__main__":
    from src.common import utf8_stdout
    utf8_stdout()
    c = run(Path(sys.argv[1]))
    print(table(c))
    print(f"\n검사 통과본: {c['_path']}")
    sys.exit(2 if c["rejected"] else 0)
