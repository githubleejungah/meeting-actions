# 작업 규칙 — meeting-actions

## 스택 (설계 승인 전, docs/architecture.md 4절)
- Claude Code 스킬 3개(meeting · issue · check). Claude API 키는 쓰지 않는다(추가 0원, ADR 0001).
- Python 3.12 스크립트(`src/`): openpyxl · python-docx · pytest.
- 결과: 회의록 워드(.docx) · 대장 엑셀(.xlsx, 할 일 · 이슈 시트). 실제 데이터는 저장소 밖 폴더.
- 대장을 쓰는 곳은 `apply.py` 하나뿐이다.

## 규칙
- 요구는 `docs/requirements.md`가 정본이다. 코드와 어긋나면 먼저 표로 보이고 묻는다.
- 실제 회의 · 강의 텍스트, 실제 회의록 · 대장은 저장소에 넣지 않는다(AC-10). 저장소에는 가상 회의만 둔다.
- 할 일은 원문 근거 시각 없이 만들지 않는다. 모르는 담당 · 목표일은 '미정'.
- 이슈는 원문에 없는 재현 조건 · 증상을 만들지 않는다. 빠진 칸은 '미정' + 되물을 질문 1~3개.
- 위험도는 A/B/C '제안'만 한다. 확정 · 판정 · 상태 · 종결 칸은 사람만 쓴다.
- 대장은 사용자가 '반영'이라고 해야만 바꾸고, 바꾸기 전에 사본을 남긴다.
- 특정 회사 제품 이름 · 내부 사정처럼 보이는 내용, 현장 메시지 보낸 사람의 이름 · 전화번호는 넣지 않는다.

## 자주 쓰는 명령
- 요구 검사: `python "C:/dev/workspace-igm/self study/ref-project/sdd/99_toolchain/01_automation/doc_lint.py" ears docs/requirements.md --min 20 --all-patterns --strict`
