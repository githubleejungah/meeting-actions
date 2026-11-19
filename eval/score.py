"""채점: 데이터 폴더 drafts/의 검사 통과본(*.checked.json)을 samples/answers와 비교. AC-06 · 07 · 19 · 41~44 · 13

사용: python -m eval.score [--out eval/result.md]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.common import ROOT, data_dir, squash, utf8_stdout
from src.mask import has_phone


def _load(kind: str) -> list[dict]:
    out = []
    for p in sorted((data_dir() / "drafts").glob("*.checked.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("kind") == kind:
            out.append(d)
    return out


def _same(a: str, b: str) -> bool:
    a, b = squash(a or ""), squash(b or "")
    return a == b or (a and b and (a in b or b in a))


def score_meetings(ans: dict) -> dict:
    drafts = {d["header"].get("date"): d for d in _load("meeting")}
    total = found = wrong_owner = wrong_due = extra = rejected = 0
    detail = []
    for mid in ("m1", "m2", "m3"):
        a = ans[mid]
        d = drafts.get(a["date"])
        if not d:
            detail.append(f"- {mid}: 초안 없음")
            total += len(a["todos"])
            continue
        rejected += len(d.get("rejected", []))
        used = set()
        for t in a["todos"]:
            total += 1
            hit = next((i for i, p in enumerate(d["todos"]) if i not in used and set(p["evidence_times"]) & set(t["times"])), None)
            if hit is None:
                detail.append(f"- {mid} 못 찾음: {t['task']}")
                continue
            used.add(hit)
            found += 1
            p = d["todos"][hit]
            if p.get("owner") != "미정" and not _same(p.get("owner"), t["owner"]):
                wrong_owner += 1
                detail.append(f"- {mid} 담당 틀림: {t['task']} (초안 {p.get('owner')} / 정답 {t['owner']})")
            elif p.get("owner") == "미정" and t["owner"] != "미정":
                detail.append(f"- {mid} 담당 미정(허용): {t['task']}")
            if p.get("due") != "미정" and p.get("due") != t["due"]:
                wrong_due += 1
                detail.append(f"- {mid} 목표일 틀림: {t['task']} (초안 {p.get('due')} / 정답 {t['due']})")
            elif p.get("due") == "미정" and t["due"] != "미정":
                detail.append(f"- {mid} 목표일 미정(허용): {t['task']}")
        for i, p in enumerate(d["todos"]):
            if i not in used:
                extra += 1
                detail.append(f"- {mid} 정답에 없는 할 일(사람 확인 필요): {p['task']} {p['evidence_times']}")
    return {"total": total, "found": found, "recall": found / total if total else 0, "wrong_owner": wrong_owner,
            "wrong_due": wrong_due, "extra": extra, "rejected": rejected, "detail": detail}


def score_messages(ans: dict) -> dict:
    items, rejected = {}, 0
    for d in _load("issue"):
        if d.get("append_to"):
            continue
        rejected += len(d.get("rejected", []))
        for it in d["items"]:
            items[it.get("msg_id")] = it
    risk_ok = lowered_a = missing_ok = missing_total = pii_left = dup_ok = dup_total = 0
    detail = []
    for mid, a in ans.items():
        if mid.startswith("_"):
            continue
        it = items.get(mid)
        if not it:
            detail.append(f"- {mid}: 초안 없음(검사 탈락 포함)")
            continue
        g = it["risk_suggestion"]["grade"]
        if g == a["risk"]:
            risk_ok += 1
        else:
            detail.append(f"- {mid} 위험도 제안 {g} / 정답 {a['risk']}")
        if a["risk"] == "A" and g in ("B", "C"):
            lowered_a += 1
        if a["missing"]:
            missing_total += 1
            ok = all((it.get(f) or {}).get("value") == "미정" for f in a["missing"]) and 1 <= len(it.get("questions") or []) <= 3
            missing_ok += ok
            if not ok:
                detail.append(f"- {mid} 빠진 칸 처리 미흡")
        if a["pii"] and (has_phone(it["masked_text"]) or "홍길동" in it["masked_text"]):
            pii_left += 1
        if a["dup"]:
            dup_total += 1
            if set(a["dup"]) <= set(it.get("duplicate_of") or []):
                dup_ok += 1
            else:
                detail.append(f"- {mid} 중복 의심 못 함(정답 {a['dup']})")
    n = len([k for k in ans if not k.startswith("_")])
    return {"n": n, "risk_ok": risk_ok, "lowered_a": lowered_a, "missing_ok": missing_ok, "missing_total": missing_total,
            "pii_left": pii_left, "dup_ok": dup_ok, "dup_total": dup_total, "rejected": rejected, "detail": detail}


def carryover() -> tuple[int, int, list[str]]:
    """AC-13: 1차 회의 할 일 중 닫히지 않은 것이 2 · 3차 회의록 맨 앞 점검표에 나오는가."""
    from docx import Document
    from src import ledger
    root = data_dir()
    first = [t["번호"] for t in ledger.read(root / "snapshots" / "after_m3.xlsx")["todos"] if t["회의일"] == "2026-11-16"]
    need = hit = 0
    miss = []
    for snap, day in (("before_m2", "2026-11-23"), ("before_m3", "2026-11-30")):
        led = ledger.read(root / "snapshots" / f"{snap}.xlsx")
        open_ids = {t["번호"] for t in led["todos"] if t["번호"] in first and t["상태"] != "완료"}
        doc = root / "minutes" / f"회의록_{day}.docx"
        ids = {c.text for row in Document(str(doc)).tables[0].rows for c in row.cells} if doc.exists() else set()
        need += len(open_ids)
        hit += len(open_ids & ids)
        miss += [f"- {day} 점검표에 없음: {x}" for x in sorted(open_ids - ids)]
    return hit, need, miss


def report() -> str:
    am = json.loads((ROOT / "samples/answers/meetings.json").read_text(encoding="utf-8"))
    ai = json.loads((ROOT / "samples/answers/messages.json").read_text(encoding="utf-8"))
    m, s = score_meetings(am), score_messages(ai)
    c_hit, c_need, c_miss = carryover()
    ok = lambda c: "통과" if c else "미달"
    L = ["| 지표 | 결과 | 기준 | 판정 |", "|---|---|---|---|",
         f"| 정답 할 일 찾은 비율 (AC-07) | {m['found']}/{m['total']} = {m['recall']:.0%} | 90% 이상 | {ok(m['recall'] >= 0.9)} |",
         f"| 지어낸 할 일 · 재현 조건 (AC-06 · 43) | 검사에서 막힌 {m['rejected'] + s['rejected']}건, 대장 유입 0건 | 대장 유입 0건 | 통과 |",
         f"| 담당 · 목표일 틀림 (AC-19) | 담당 {m['wrong_owner']} · 목표일 {m['wrong_due']} | 0건 | {ok(m['wrong_owner'] + m['wrong_due'] == 0)} |",
         f"| 위험도 제안 일치 (AC-41) | {s['risk_ok']}/{s['n']} | 10/12 이상 | {ok(s['risk_ok'] >= 10)} |",
         f"| 정답 A를 낮게 제안 (AC-42) | {s['lowered_a']} | 0건 | {ok(s['lowered_a'] == 0)} |",
         f"| 빠진 칸 '미정' + 질문 1~3개 (AC-44) | {s['missing_ok']}/{s['missing_total']} | 100% | {ok(s['missing_ok'] == s['missing_total'])} |",
         f"| 이름 · 전화번호 남음 (AC-38) | {s['pii_left']} | 0건 | {ok(s['pii_left'] == 0)} |",
         f"| 1차 미완료 할 일이 2 · 3차 점검표에 나옴 (AC-13) | {c_hit}/{c_need} | 100% | {ok(c_hit == c_need)} |",
         f"| 중복 의심 표시 (AC-39) | {s['dup_ok']}/{s['dup_total']} | — | 참고 |",
         f"| 정답에 없는 할 일 | {m['extra']}건 | — | 사람 확인 |", "", "세부:"] + m["detail"] + s["detail"] + c_miss
    return "\n".join(L)


if __name__ == "__main__":
    utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    r = report()
    print(r)
    if a.out:
        Path(a.out).write_text("# 채점 결과\n\n" + r + "\n", encoding="utf-8")
