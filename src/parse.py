"""회의 텍스트(유니브 형식) 읽기 · 형식 검사. AC-02 · 09 · 22 · 24

사용: python -m src.parse <회의.txt>
"""
from __future__ import annotations

import json
import re
import sys

from src.common import load_rules, read_text

TIME_LINE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s?(.*)$")


def parse_lines(text: str) -> list[dict]:
    """시각 표시 줄만 [{time, text, line}]로. 시각이 없는 줄은 앞 줄에 붙인다(버리지 않음)."""
    out: list[dict] = []
    for i, raw in enumerate(text.lstrip("﻿").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        m = TIME_LINE.match(line)
        if m:
            out.append({"time": f"[{m.group(1)}]", "text": m.group(2).strip(), "line": i})
        elif out:
            out[-1]["text"] = (out[-1]["text"] + " " + line).strip()
    return out


def check_input(text: str, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    size = len(text.encode("utf-8"))
    lines = parse_lines(text)
    if size > rules["max_input_bytes"]:
        return {"ok": False, "reason": "too_large", "bytes": size, "lines": len(lines),
                "message": "회의 텍스트가 너무 깁니다(약 4시간 넘음). 나눠 넣어 주세요."}
    if not lines:
        return {"ok": False, "reason": "no_timestamps", "bytes": size, "lines": 0,
                "message": "시각 표시가 있는 텍스트를 넣어 주세요."}
    return {"ok": True, "reason": None, "bytes": size, "lines": len(lines),
            "first": lines[0]["time"], "last": lines[-1]["time"]}


def times_in(text: str) -> set[str]:
    return {x["time"] for x in parse_lines(text)}


if __name__ == "__main__":
    from src.common import utf8_stdout
    utf8_stdout()
    t = read_text(sys.argv[1])
    print(json.dumps(check_input(t), ensure_ascii=False))
    sys.exit(0 if check_input(t)["ok"] else 1)
