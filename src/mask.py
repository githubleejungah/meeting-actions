"""현장 메시지의 이름 · 전화번호 가리기. AC-38

규칙으로 다 잡지 못할 수 있어(지나치게 가리는 쪽을 택함), 스킬에서도 이름을 쓰지 않게 한다.
사용: python -m src.mask <메시지.txt> [-o 저장할.txt]  → 가린 글을 출력 · 저장
"""
from __future__ import annotations

import re
import sys

from src.common import load_rules, read_text

PHONE = re.compile(r"(?<!\d)(?:01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}|0\d{1,2}[-.\s]\d{3,4}[-.\s]\d{4})(?!\d)")
NAME_PATTERNS = [
    # "홍길동 씨/님/사장님/대표님"
    re.compile(r"([가-힣]{2,4})(?=\s?(?:씨|님|사장님|대표님)(?:[^가-힣]|$|[이가은는을를께도의요]))"),
    # "저 홍길동인데요", "저는 홍길동입니다", "안녕하세요 홍길동입니다"
    re.compile(r"(?:저는?|제가|안녕하세요[,.!\s]*)\s*([가-힣]{2,4})(?=(?:인데요|입니다|이에요|예요|이고요))"),
]


def mask(text: str, rules: dict | None = None) -> tuple[str, dict]:
    rules = rules or load_rules()
    stop = tuple(rules["name_stopwords"])
    counts = {"phone": 0, "name": 0}

    def _phone(m: re.Match) -> str:
        counts["phone"] += 1
        return "[전화번호]"

    out = PHONE.sub(_phone, text)
    for pat in NAME_PATTERNS:
        def _name(m: re.Match) -> str:
            name = m.group(1)
            if name.startswith(stop) or name in stop:
                return m.group(0)
            counts["name"] += 1
            return m.group(0).replace(name, "[이름]")
        out = pat.sub(_name, out)
    return out, counts


def has_phone(text: str) -> bool:
    return bool(PHONE.search(text))


if __name__ == "__main__":
    from src.common import utf8_stdout
    utf8_stdout()
    masked, c = mask(read_text(sys.argv[1]))
    if len(sys.argv) > 3 and sys.argv[2] == "-o":
        from pathlib import Path
        Path(sys.argv[3]).write_text(masked, encoding="utf-8")
    else:
        print(masked)
    print(f"# 가림: 전화번호 {c['phone']}건 · 이름 {c['name']}건", file=sys.stderr)
