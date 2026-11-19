"""시연 시나리오: 회의 사이에 '사람'이 엑셀에서 하는 일(위험도 확정 · 판정 · 상태 변경)을 흉내 낸다.
AI가 아니라 사용자의 손을 대신하는 것이며, 시연 페이지에도 '사람이 한 일'로 표시한다.

사용: python -m eval.human_edits <단계>   단계: after_week1 | after_m1 | after_week2 | after_m2
"""
from __future__ import annotations

import sys

from openpyxl import load_workbook

from src import ledger
from src.common import data_dir, utf8_stdout

EDITS = {
    "after_week1": {"이슈": {
        "I-001": {"위험도": "A", "상태": "확인 중"}, "I-002": {"위험도": "A", "상태": "확인 중"},
        "I-003": {"위험도": "B"}, "I-004": {"위험도": "B"}, "I-005": {"위험도": "B"}, "I-006": {"위험도": "C"}}},
    "after_m1": {
        "할 일": {"T-001": {"상태": "진행"}, "T-003": {"상태": "완료"}, "T-005": {"상태": "완료"}},
        "이슈": {"I-006": {"상태": "종결", "판정": "반영", "조치": "엑셀 날짜 칸 형식 수정"},
                "I-005": {"판정": "보류", "지연 사유": "기온별 데이터 부족"}}},
    "after_week2": {"이슈": {
        "I-007": {"위험도": "A", "상태": "확인 중"}, "I-008": {"위험도": "B"}, "I-009": {"위험도": "B"},
        "I-010": {"위험도": "C"}, "I-011": {"위험도": "C"}, "I-012": {"위험도": "C"}}},
    "after_m2": {
        "할 일": {"T-007": {"상태": "완료"}, "T-001": {"지연 사유": "비로 현장 재현 못 함"}},
        "이슈": {"I-007": {"상태": "종결", "판정": "반영", "조치": "배터리 커넥터 조임"},
                "I-009": {"상태": "종결", "조치": "I-003과 같은 건으로 합침(사람 판단)"},
                "I-012": {"상태": "추후 수정", "판정": "조건부 반영", "조치": "다음 출시에서 수정"}}},
}


def run(step: str) -> list[str]:
    path = data_dir() / "ledger.xlsx"
    wb = load_workbook(path)
    done = []
    for sheet, rows in EDITS[step].items():
        ws = wb[sheet]
        cols = ledger.TODO_COLS if sheet == ledger.TODO_SHEET else ledger.ISSUE_COLS
        idx = {c: i for i, c in enumerate(cols)}
        for row in ws.iter_rows(min_row=2):
            rid = row[0].value
            for k, v in rows.get(rid, {}).items():
                row[idx[k]].value = v
                done.append(f"{rid} {k}={v}")
    wb.save(path)
    return done


if __name__ == "__main__":
    utf8_stdout()
    for d in run(sys.argv[1]):
        print("사람:", d)
