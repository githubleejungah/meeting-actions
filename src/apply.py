"""'반영': 백업 → 대장에 새 행 추가 → (회의면) 점검표 + 회의록 워드.
대장을 쓰는 곳은 여기 하나뿐이다. AC-03 · 04 · 12 · 13 · 20 · 25 · 31 · 33 · 34 · 40

사용: python -m src.apply <drafts/xxx.checked.json> [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from openpyxl import load_workbook
from openpyxl.styles import Alignment

from src import checklist, ledger
from src.common import data_dir, load_rules
from src.rules import to_date


class LedgerLocked(Exception):
    pass


def _backup(path: Path, root: Path) -> Path | None:
    if not path.exists():
        return None
    dst = root / "backups" / f"ledger_{datetime.now():%Y%m%d-%H%M%S-%f}.xlsx"
    shutil.copy2(path, dst)
    return dst


def _open(path: Path):
    if not path.exists():
        ledger.create(path)
    return load_workbook(path)


def _wrap(ws, row: int):
    for c in ws[row]:
        c.alignment = Alignment(wrap_text=True, vertical="top")


def apply_meeting(checked: dict, root: Path, today: date, rules: dict) -> dict:
    U = rules["unknown"]
    path = root / "ledger.xlsx"
    before = ledger.read(path)
    check_items = checklist.build(before, today, rules)  # 이번 회의 전 열린 항목 (AC-13)
    backup = _backup(path, root)
    wb = _open(path)
    ws = wb[ledger.TODO_SHEET]
    n = ledger.next_id(before["todos"], "T")
    issue_risk = {r["번호"]: r.get("위험도", "") for r in before["issues"]}
    mdate = checked.get("header", {}).get("date", U)
    added = []
    for t in checked["todos"]:
        tid = f"T-{n:03d}"
        n += 1
        rel = t.get("related_issue") or ""
        ws.append([tid, mdate, t["task"], t.get("owner", U), t.get("due", U), rules["todo_status"][0],
                   issue_risk.get(rel, ""), "", ", ".join(t["evidence_times"]), "", rel])
        _wrap(ws, ws.max_row)
        added.append({**t, "id": tid})
    wb.save(path)
    minutes = _minutes(checked, added, check_items, root, rules)
    return {"added": [a["id"] for a in added], "backup": str(backup) if backup else None, "minutes": str(minutes)}


def apply_issue(checked: dict, root: Path, today: date, rules: dict) -> dict:
    U = rules["unknown"]
    path = root / "ledger.xlsx"
    before = ledger.read(path)
    backup = _backup(path, root)
    wb = _open(path)
    ws = wb[ledger.ISSUE_SHEET]
    target = checked.get("append_to")
    if target:  # 되물은 답: '미정' 칸만 채움 (AC-33)
        col = {"condition": "재현 조건", "symptom": "증상", "expected": "기대 결과"}
        idx = {name: i + 1 for i, name in enumerate(ledger.ISSUE_COLS)}
        filled = []
        for row in ws.iter_rows(min_row=2):
            if row[0].value == target:
                for it in checked["items"]:
                    for f, cname in col.items():
                        v = (it.get(f) or {}).get("value", U)
                        cell = row[idx[cname] - 1]
                        if v != U and cell.value == U:
                            cell.value = v
                            filled.append(cname)
        wb.save(path)
        return {"added": [], "filled": {target: filled}, "backup": str(backup) if backup else None}
    n = ledger.next_id(before["issues"], "I")
    added = []
    recv = checked.get("received_date") or today.isoformat()
    for it in checked["items"]:
        iid = f"I-{n:03d}"
        n += 1
        rs = it["risk_suggestion"]
        q = rs["quote"] if isinstance(rs["quote"], str) else " … ".join(rs["quote"])
        sug = f"{rs['grade']} — 근거: \"{q}\""
        if rs.get("raised_from"):
            sug += f" (안전 낱말 '{rs['safety_word']}'로 {rs['raised_from']}→A)"
        ws.append([iid, "", it["condition"]["value"], it["symptom"]["value"], it["expected"]["value"],
                   rules["issue_status"][0], "", "", "", "", it.get("received_date") or recv, it["route"], it["masked_text"], sug,
                   "\n".join(it.get("questions") or []), ", ".join(it.get("attachments") or [])])
        _wrap(ws, ws.max_row)
        added.append(iid)
    wb.save(path)
    return {"added": added, "backup": str(backup) if backup else None}


def _font(doc: Document):
    st = doc.styles["Normal"]
    st.font.name = "Malgun Gothic"
    st.font.size = Pt(10)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")


def _table(doc, head, rows):
    t = doc.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, head):
        c.text = h
    for r in rows:
        cells = t.add_row().cells
        for c, v in zip(cells, r):
            c.text = str(v)


def _minutes(checked, added, check_items, root: Path, rules) -> Path:
    h = checked.get("header", {})
    U = rules["unknown"]
    doc = Document()
    _font(doc)
    doc.add_heading(f"회의록 — {h.get('name', U)}", level=1)
    doc.add_heading("0. 지난 일 점검", level=2)
    _table(doc, ["위험도", "번호", "내용", "담당", "상태", "목표일", "지연"],
           [[i["risk"] or "-", i["id"], i["text"], i["owner"], i["status"], i["due"], "지연" if i["delayed"] else ""]
            for i in check_items] or [["-", "-", "닫히지 않은 항목 없음", "", "", "", ""]])
    doc.add_heading("1. 머리", level=2)
    for k, label in (("name", "회의명"), ("date", "일시"), ("attendees", "참석자"), ("author", "작성자")):
        doc.add_paragraph(f"{label}: {h.get(k, U)}")
    doc.add_heading("2. 안건별 논의 요약", level=2)
    for a in checked.get("agenda", []):
        doc.add_paragraph(f"{a['title']} — {a['summary']} ({', '.join(a.get('quotes', []))})", style="List Bullet")
    doc.add_heading("3. 결정 사항", level=2)
    for d in checked.get("decisions", []) or [{"text": "없음", "quotes": []}]:
        doc.add_paragraph(f"{d['text']} {('(' + ', '.join(d['quotes']) + ')') if d.get('quotes') else ''}", style="List Bullet")
    doc.add_heading("4. Action Item", level=2)
    _table(doc, ["번호", "할 일", "담당", "목표일", "근거 시각", "관련 이슈"],
           [[a["id"], a["task"], a.get("owner", U), a.get("due", U), ", ".join(a["evidence_times"]), a.get("related_issue") or ""]
            for a in added] or [["-", "할 일 없음", "", "", "", ""]])
    doc.add_heading("5. 미결 사항 · 다음 회의", level=2)
    for o in checked.get("open_items", []):
        doc.add_paragraph(f"{o['text']} ({', '.join(o.get('quotes', []))})", style="List Bullet")
    doc.add_paragraph(f"다음 회의: {checked.get('next_meeting', U)}")
    if checked.get("rejected"):
        doc.add_paragraph(f"(검사에서 빠진 항목 {len(checked['rejected'])}건은 대장에 넣지 않았습니다)")
    d = h.get("date", U)
    stem = f"회의록_{d}" if d != U else f"회의록_{datetime.now():%Y%m%d-%H%M%S}"
    out = root / "minutes" / f"{stem}.docx"
    k = 2
    while out.exists():  # 사용자가 고쳤을 수 있는 회의록은 덮어쓰지 않는다
        out = root / "minutes" / f"{stem}_{k}.docx"
        k += 1
    doc.save(out)
    return out


def run(checked_path: Path, today: date | None = None, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    root = data_dir()
    path = root / "ledger.xlsx"
    if not ledger.is_writable(path):
        raise LedgerLocked("대장 파일이 열려 있습니다. 엑셀에서 닫은 뒤 다시 '반영'이라고 해 주세요.")
    checked = json.loads(checked_path.read_text(encoding="utf-8"))
    today = today or date.today()
    if checked["kind"] == "meeting":
        return apply_meeting(checked, root, today, rules)
    return apply_issue(checked, root, today, rules)


if __name__ == "__main__":
    from src.common import utf8_stdout
    utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("checked")
    ap.add_argument("--today")
    a = ap.parse_args()
    try:
        r = run(Path(a.checked), to_date(a.today) if a.today else None)
    except LedgerLocked as e:  # AC-25: 0행 변경, 안내 1회
        print(e)
        sys.exit(3)
    print(json.dumps(r, ensure_ascii=False, indent=2))
