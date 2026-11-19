"""대장 엑셀 읽기 · 쓰기. 쓰기는 apply.py만 부른다(아키텍처 6절)."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

TODO_SHEET = "할 일"
ISSUE_SHEET = "이슈"
TODO_COLS = ["번호", "회의일", "할 일", "담당", "목표일", "상태", "위험도", "지연 사유", "근거 시각", "비고", "관련 이슈 번호"]
ISSUE_COLS = ["번호", "위험도", "재현 조건", "증상", "기대 결과", "상태", "목표일", "판정", "조치", "지연 사유",
              "접수일", "접수 경로", "원문", "위험도 제안", "되물을 질문", "첨부 파일 이름"]
WIDTH = {"할 일": 40, "재현 조건": 34, "증상": 30, "기대 결과": 28, "원문": 50, "위험도 제안": 36, "되물을 질문": 36}


def _style_header(ws, cols):
    for i, name in enumerate(cols, start=1):
        c = ws.cell(row=1, column=i, value=name)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3A5A")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[c.column_letter].width = WIDTH.get(name, 12)
    ws.freeze_panes = "B2"


def create(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = TODO_SHEET
    _style_header(ws, TODO_COLS)
    _style_header(wb.create_sheet(ISSUE_SHEET), ISSUE_COLS)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def read(path: Path) -> dict:
    """{'todos': [dict], 'issues': [dict]} — 칸 이름을 키로."""
    if not path.exists():
        return {"todos": [], "issues": []}
    wb = load_workbook(path, data_only=True)
    out = {}
    for key, sheet, cols in (("todos", TODO_SHEET, TODO_COLS), ("issues", ISSUE_SHEET, ISSUE_COLS)):
        rows = []
        for r in wb[sheet].iter_rows(min_row=2, values_only=True):
            if not any(v not in (None, "") for v in r):
                continue
            rows.append({c: ("" if v is None else v) for c, v in zip(cols, r)})
        out[key] = rows
    return out


def next_id(rows: list[dict], prefix: str) -> int:
    nums = [int(str(r["번호"]).split("-")[1]) for r in rows if str(r.get("번호", "")).startswith(prefix + "-")]
    return (max(nums) if nums else 0) + 1


def is_writable(path: Path) -> bool:
    """엑셀이 파일을 열고 있으면 False. (잠금 파일 ~$ 또는 쓰기 거부)"""
    if (path.parent / ("~$" + path.name)).exists():
        return False
    if not path.exists():
        return True
    try:
        with open(path, "r+b"):
            return True
    except OSError:
        return False
