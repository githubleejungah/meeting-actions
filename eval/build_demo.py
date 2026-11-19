"""시연 페이지 데이터 만들기: 데모 데이터 폴더(가상 시나리오 실행 결과) → site/demo-data.json. AC-46 · 47

사용: MA_DATA_DIR=<데모 폴더> python -m eval.build_demo
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from eval.score import report
from src import ledger
from src.common import ROOT, data_dir, read_text, utf8_stdout
from src.parse import parse_lines

STAGES = [("before_m1", "1차 회의 전 · 2026-11-16", "2026-11-16"), ("before_m2", "2차 회의 전 · 2026-11-23", "2026-11-23"),
          ("before_m3", "3차 회의 전 · 2026-11-30", "2026-11-30"), ("after_m3", "3차 회의 뒤 · 2026-11-30", "2026-11-30")]


def _rows(rows: list[dict]) -> list[dict]:
    return [{k: (v.isoformat()[:10] if hasattr(v, "isoformat") else v) for k, v in r.items()} for r in rows]


def build() -> dict:
    root = data_dir()
    stages = []
    for sid, label, day in STAGES:
        led = ledger.read(root / "snapshots" / f"{sid}.xlsx")
        stages.append({"id": sid, "label": label, "date": day, "todos": _rows(led["todos"]), "issues": _rows(led["issues"])})
    final = stages[-1]
    by_text = {r["원문"]: r["번호"] for r in final["issues"]}

    drafts = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((root / "drafts").glob("*.checked.json"))]
    issue_drafts = [d for d in drafts if d["kind"] == "issue" and not d.get("append_to")]
    messages, guard, week = [], [], 0
    for d in sorted(issue_drafts, key=lambda d: min(it.get("received_date", "") for it in d["items"])):
        week += 1
        for it in d["items"]:
            messages.append({"id": it.get("msg_id"), "week": week, "received": it.get("received_date"), "route": it["route"],
                             "masked": it["masked_text"], "ledger_id": by_text.get(it["masked_text"], ""),
                             "draft": {k: it.get(k) for k in ("condition", "symptom", "expected", "risk_suggestion", "questions", "duplicate_of")}})
        guard += [f"{n}" for n in d.get("notes", [])]
        guard += [f"검사 탈락(대장에 안 넣음): {r.get('msg_id', '')} {'; '.join(r['reasons'])}" for r in d.get("rejected", [])]
    reply = None
    for d in drafts:
        if d.get("append_to"):
            col = {"condition": "재현 조건", "symptom": "증상", "expected": "기대 결과"}
            it = d["items"][0] if d["items"] else {}
            reply = {"target": d["append_to"], "masked": it.get("masked_text", ""),
                     "filled": {c: (it.get(f) or {}).get("value") for f, c in col.items() if (it.get(f) or {}).get("value", "미정") != "미정"}}
    meetings = []
    for d, stage in zip(sorted([d for d in drafts if d["kind"] == "meeting"], key=lambda d: d["header"]["date"]),
                        ("before_m1", "before_m2", "before_m3")):
        src = root / d["source_file"]
        added = [t["번호"] for t in final["todos"] if t["회의일"] == d["header"]["date"]]
        meetings.append({"date": d["header"]["date"], "stage": stage,
                         "lines": [{"time": x["time"], "text": x["text"]} for x in parse_lines(read_text(src))],
                         "draft": {k: d.get(k) for k in ("header", "agenda", "decisions", "todos", "open_items", "next_meeting")},
                         "added": added})
        guard += [f"검사 탈락(대장에 안 넣음): {r.get('task') or r.get('text')} — {'; '.join(r['reasons'])}" for r in d.get("rejected", [])]
    masked_files = list((root / "inputs").glob("*.masked.txt"))
    n_phone = sum(read_text(p).count("[전화번호]") for p in masked_files)
    n_name = sum(read_text(p).count("[이름]") for p in masked_files)
    guard = [f"이름 {n_name}건 · 전화번호 {n_phone}건을 AI가 보기 전에 가림(가린 글만 대장 '원문' 칸에 저장)",
             "모든 AI 값에 원문 인용을 붙이고, 인용이 원문에 글자 그대로 없으면 대장에 넣지 않음",
             "위험도 확정 · 판정 · 상태 · 종결 칸은 비워 두고 사람이 채움(아래 대장의 값은 시나리오에서 사람이 고른 것)",
             "되물은 답은 '미정'이던 칸만 채우고 다른 칸은 그대로 둠",
             "'반영' 전마다 대장 사본을 남김(지우지 않음)"] + guard

    score_rows = []
    for line in report().splitlines():
        if line.startswith("|") and not set(line) <= set("|-: "):
            score_rows.append([c.strip() for c in line.strip("|").split("|")])
        if line.startswith("세부"):
            break
    return {"stages": stages, "messages": messages, "reply": reply, "meetings": meetings, "guard": guard, "score": score_rows}


if __name__ == "__main__":
    utf8_stdout()
    out = ROOT / "site" / "demo-data.json"
    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=1)
    assert not re.search(r"01[016789]-?\d{3,4}-?\d{4}", text), "전화번호가 남아 있음"  # AC-46
    out.write_text(text, encoding="utf-8")
    print(f"저장: {out} · 메시지 {len(data['messages'])} · 회의 {len(data['meetings'])} · 시점 {len(data['stages'])}")
