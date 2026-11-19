"""단위 시험: 규칙 · 검사 · 반영. AC 번호를 이름에 적는다."""
from __future__ import annotations

import json
from datetime import date

import pytest

from src import apply as ap
from src import checklist, ledger
from src.common import load_rules
from src.mask import has_phone, mask
from src.parse import check_input, parse_lines
from src.rules import is_delayed, safety_hits, sort_key
from src.validate import validate_issue, validate_meeting

R = load_rules()
SRC = "﻿[0:05] 안녕하세요 시작하겠습니다.\n[1:10] 수진 님이 금요일까지 날짜 형식 고쳐 주세요.\n이어지는 말\n[1:01:02] 제가 내일 농가에 물어볼게요."


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("MA_DATA_DIR", str(tmp_path))
    for s in ("inputs", "drafts", "minutes", "backups"):
        (tmp_path / s).mkdir()
    return tmp_path


def test_ac02_two_time_formats_and_no_line_lost():
    lines = parse_lines(SRC)
    assert [x["time"] for x in lines] == ["[0:05]", "[1:10]", "[1:01:02]"]
    assert "이어지는 말" in lines[1]["text"]


def test_ac22_no_timestamps():
    assert check_input("그냥 글입니다")["reason"] == "no_timestamps"


def test_ac24_too_large():
    assert check_input("[0:01] " + "가" * 50000)["reason"] == "too_large"


def test_ac29_safety_words():
    assert safety_hits("옆에 사람이 있었어요", R) == ["사람"]
    assert safety_hits("날짜가 숫자로 나와요", R) == []


def test_ac36_delay_boundary():
    today = date(2026, 11, 30)
    assert not is_delayed("2026-11-23", today, R)  # 7일
    assert is_delayed("2026-11-22", today, R)  # 8일
    assert not is_delayed("미정", today, R)


def test_ac21_sort_order():
    items = [{"id": "x1", "risk": "C", "due": "2026-11-01"}, {"id": "x2", "risk": "", "due": "2026-10-01"},
             {"id": "x3", "risk": "A", "due": "미정"}, {"id": "x4", "risk": "A", "due": "2026-12-01"},
             {"id": "x5", "risk": "B", "due": "2026-11-20"}]
    assert [i["id"] for i in sorted(items, key=lambda x: sort_key(x, R))] == ["x4", "x3", "x5", "x1", "x2"]


def test_ac38_mask_phone_and_name():
    out, c = mask("안녕하세요 홍길동입니다 010-0000-0000. 대리점 사장님께 전해 주세요.", R)
    assert "홍길동" not in out and "010" not in out
    assert "[이름]" in out and "[전화번호]" in out
    assert "사장님" in out  # 일반 명사는 남김
    assert not has_phone(out)


def _todo(**kw):
    t = {"task": "날짜 형식 수정", "owner": "수진", "due": "2026-11-20", "evidence_times": ["[1:10]"],
         "quote": "날짜 형식 고쳐 주세요", "related_issue": None}
    t.update(kw)
    return t


def test_ac05_06_invented_todo_rejected():
    led = {"todos": [], "issues": []}
    d = {"kind": "meeting", "todos": [_todo(), _todo(evidence_times=["[9:99]"]), _todo(quote="원문에 없는 말")]}
    out = validate_meeting(d, SRC, led, R)
    assert len(out["todos"]) == 1 and len(out["rejected"]) == 2


def test_ac17_invented_owner_rejected():
    out = validate_meeting({"kind": "meeting", "todos": [_todo(owner="박지훈")]}, SRC, {"todos": [], "issues": []}, R)
    assert out["rejected"]


def test_ac31_human_field_rejected():
    out = validate_meeting({"kind": "meeting", "todos": [_todo(status="완료")]}, SRC, {"todos": [], "issues": []}, R)
    assert out["rejected"]


def _issue(**kw):
    it = {"msg_id": "M1", "masked_text": "3번 열에서 또 멈췄어요", "route": "농가",
          "condition": {"value": "미정", "quote": None},
          "symptom": {"value": "멈춤", "quote": "또 멈췄어요"},
          "expected": {"value": "미정", "quote": None},
          "risk_suggestion": {"grade": "B", "quote": "또 멈췄어요"},
          "questions": ["멈춘 시각은?"], "attachments": [], "duplicate_of": []}
    it.update(kw)
    return it


def test_ac32_missing_needs_questions():
    led = {"todos": [], "issues": []}
    assert not validate_issue({"kind": "issue", "items": [_issue()]}, led, R)["rejected"]
    assert validate_issue({"kind": "issue", "items": [_issue(questions=[])]}, led, R)["rejected"]
    assert validate_issue({"kind": "issue", "items": [_issue(questions=["1", "2", "3", "4"])]}, led, R)["rejected"]


def test_ac43_invented_condition_rejected():
    it = _issue(condition={"value": "경사 구간", "quote": "경사 구간에서"})
    assert validate_issue({"kind": "issue", "items": [it]}, {"todos": [], "issues": []}, R)["rejected"]


def test_ac29_safety_raises_suggestion():
    it = _issue(masked_text="옆에 사람이 있는데 안 멈췄어요", symptom={"value": "안 멈춤", "quote": "안 멈췄어요"},
                risk_suggestion={"grade": "C", "quote": "안 멈췄어요"})
    out = validate_issue({"kind": "issue", "items": [it]}, {"todos": [], "issues": []}, R)
    assert out["items"][0]["risk_suggestion"]["grade"] == "A" and out["notes"]


def _checked_issue(root, items, **kw):
    d = {"kind": "issue", "received_date": "2026-11-16", "items": items, "rejected": [], "append_to": None}
    d.update(kw)
    p = root / "drafts" / f"i{len(list((root / 'drafts').iterdir()))}.checked.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return p


def test_ac12_20_31_33_40_apply_issue_and_append(root):
    p = _checked_issue(root, [_issue()])
    r = ap.run(p, date(2026, 11, 16), R)
    assert r["added"] == ["I-001"] and r["backup"] is None
    led = ledger.read(root / "ledger.xlsx")
    row = led["issues"][0]
    assert row["위험도"] == "" and row["판정"] == "" and row["상태"] == "접수"  # AC-31
    # 사람이 위험도 확정 → 덧붙이기가 그 칸을 건드리지 않아야 함
    from openpyxl import load_workbook
    wb = load_workbook(root / "ledger.xlsx"); wb["이슈"]["B2"] = "B"; wb.save(root / "ledger.xlsx")
    ans = _issue(masked_text="아침 9시쯤 신호 표시가 한 칸이었어요",
                 condition={"value": "아침 9시, 신호 표시 한 칸", "quote": "아침 9시쯤 신호 표시가 한 칸"},
                 symptom={"value": "미정", "quote": None}, risk_suggestion={"grade": "B", "quote": "아침 9시쯤"}, questions=[])
    p2 = _checked_issue(root, [ans], append_to="I-001")
    r2 = ap.run(p2, date(2026, 11, 20), R)
    assert r2["filled"]["I-001"] == ["재현 조건"] and r2["backup"]  # AC-40
    row = ledger.read(root / "ledger.xlsx")["issues"][0]
    assert row["재현 조건"].startswith("아침 9시") and row["증상"] == "멈춤" and row["위험도"] == "B"
    assert len(list((root / "backups").iterdir())) == 1


def test_ac13_meeting_minutes_and_checklist(root):
    src = root / "inputs" / "m.txt"
    src.write_text(SRC, encoding="utf-8")
    d = {"kind": "meeting", "source_file": "inputs/m.txt",
         "header": {"name": "주간 회의", "date": "2026-11-16", "attendees": "미정", "author": "미정"},
         "agenda": [{"title": "날짜", "summary": "형식 수정", "quotes": ["[1:10]"]}], "decisions": [],
         "todos": [_todo()], "open_items": [], "next_meeting": "미정", "rejected": []}
    p = root / "drafts" / "m.checked.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    r1 = ap.run(p, date(2026, 11, 16), R)
    assert r1["added"] == ["T-001"]
    d["header"]["date"] = "2026-11-23"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    ap.run(p, date(2026, 11, 30), R)
    items = checklist.build(ledger.read(root / "ledger.xlsx"), date(2026, 11, 30), R)
    t1 = [i for i in items if i["id"] == "T-001"][0]
    assert t1["delayed"]  # 11-20 목표, 11-30 → 10일
    from docx import Document
    doc2 = Document(str(root / "minutes" / "회의록_2026-11-23.docx"))
    text = "\n".join(c.text for t in doc2.tables for row in t.rows for c in row.cells)
    assert "T-001" in text  # 2차 회의록 점검표에 1차 할 일


def test_ac25_locked_ledger(root):
    ledger.create(root / "ledger.xlsx")
    (root / "~$ledger.xlsx").write_text("lock")
    with pytest.raises(ap.LedgerLocked):
        ap.run(_checked_issue(root, [_issue()]), date(2026, 11, 16), R)
    assert ledger.read(root / "ledger.xlsx")["issues"] == []


def test_ac10_gitignore_blocks_data():
    from pathlib import Path
    gi = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
    assert "config.json" in gi and "*.xlsx" in gi and "*.docx" in gi
