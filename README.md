# meeting-actions — 회의 · 현장 이슈 정리

회의와 현장에서 나온 일을 AI가 정리하고, 사람이 판정한다.

**시연 페이지:** https://githubleejungah.github.io/meeting-actions/ (가상 데이터 · 설치 없이 클릭으로 체험)

- 현장 메시지 → 재현 조건 · 증상 · 기대 결과로 나눈 이슈 초안 + 위험도(A 안전 · B 기능 저하 · C 불편) **제안**. 위험도 확정 · 판정(반영 / 조건부 반영 / 보류) · 종결은 사람만 한다.
- 회의 녹음 텍스트(받아쓰기 앱이 내보낸 `[분:초] 문장`) → 회의록 워드 + 할 일(담당 · 목표일 · 근거 시각). 원문에 없는 담당 · 날짜는 지어내지 않고 '미정'.
- 할 일과 이슈를 엑셀 대장 하나에 쌓고, 다음 회의록 맨 앞 점검표에 닫히지 않은 항목을 위험도 순으로 다시 꺼낸다. 목표일을 7일 넘기면 '지연'.
- Claude Code 안에서 도는 명령(스킬)이라 추가 비용이 없다. 데이터는 모두 가상이다.

## 어떻게 나눴나

| 하는 쪽 | 일 |
|---|---|
| Claude | 할 일 뽑기, 재현 조건 · 증상 · 기대 결과 나누기, 위험도 제안, 되물을 질문, 중복 의심 |
| Python 스크립트 | 이름 · 전화번호 가리기, 원문 인용 검사(지어낸 값 막기), 안전 낱말 → A, 정렬 · 지연 판단, 백업 · 대장 쓰기 |
| 사람 | '반영' 승인, 위험도 확정 · 판정 · 상태 · 종결 |

## 실행법

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp config.example.json config.json   # data_dir: 실제 데이터 폴더(저장소 밖)
.venv/Scripts/python -m pytest -q
```

Claude Code에서 이 폴더를 열고 `/issue`(현장 메시지) · `/meeting`(회의 텍스트) · `/check`(점검표)를 부른다. 가상 시나리오 채점은 `eval/score.py`, 시연 데이터는 `eval/build_demo.py`.

## 문서

| 문서 | 위치 |
|---|---|
| 요구(원문 · 인터뷰 · EARS 수용 기준 50개) | [docs/requirements.md](docs/requirements.md) |
| 아키텍처 | [docs/architecture.md](docs/architecture.md) |
| 데이터 설계(정본 표 · 대장 칸 · 초안 JSON) | [docs/data-model.md](docs/data-model.md) |
| 흐름 설계(순서도 · 끝나는 조건) | [docs/flows.md](docs/flows.md) |
| 설계 결정 기록 | [docs/adr/](docs/adr/) |
| 작업 규칙 | [CLAUDE.md](CLAUDE.md) |

이슈 관리표 · 위험도 기준 · 판정 세 가지는 지원자가 예전 스마트팜 서비스 개발에서 직접 만들어 쓴 양식을 가상 상황에 맞춰 다시 쓴 것이다. 실제 회사 · 제품의 자료는 쓰지 않았다.

## 연락처

이메일: [veryfar@naver.com](mailto:veryfar@naver.com)
