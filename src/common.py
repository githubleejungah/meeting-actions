"""공통: 경로 · 규칙 · 설정 읽기."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "src" / "rules.json"
DEFAULT_DATA_DIR = Path("C:/dev/meeting-actions-data")


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def data_dir() -> Path:
    """실제 데이터 폴더. 환경변수 MA_DATA_DIR > config.json > 기본값 순."""
    env = os.environ.get("MA_DATA_DIR")
    if env:
        d = Path(env)
    else:
        cfg = ROOT / "config.json"
        d = Path(json.loads(cfg.read_text(encoding="utf-8"))["data_dir"]) if cfg.exists() else DEFAULT_DATA_DIR
    for sub in ("inputs", "drafts", "minutes", "backups"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def read_text(path_or_text: str | Path) -> str:
    """파일이면 읽고(BOM 제거), 아니면 문자열 그대로."""
    p = Path(str(path_or_text))
    try:
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    return str(path_or_text).lstrip("\ufeff")


def squash(s: str) -> str:
    """인용 비교용: 공백을 모두 지운다."""
    return "".join(str(s).split())


def utf8_stdout() -> None:
    """Windows 콘솔에서도 한글이 깨지지 않게 출력을 UTF-8로."""
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
