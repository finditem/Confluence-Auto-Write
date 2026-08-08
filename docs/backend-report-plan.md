# 백엔드 주간 회의록 자동화

> 상태: 코드·워크플로·스페이스/폴더 전부 완료. 실행 검증만 안 해봄.

## 왜 필요한가

지금 있는 `frontend/weekly_report.py`는 프론트엔드 팀 전용. 같은 방식으로 백엔드 팀 주간 회의록도 자동 생성하고 싶음.

## 확정된 것

- 전체 구조는 프론트엔드 자동화와 동일 (GitHub 커밋 로그 수집 → OpenAI 요약 → Confluence 페이지 upsert)
- 대상 인원: **유세정** (GitHub `Yoosejeong`), **박상혁** (GitHub `sangcci`)
- 대상 저장소: `finditem/FI-BE` 전체 — Java/Spring Boot 단일 서비스 저장소라 프론트처럼 앱별 경로 분리가 없음. 경로별 카테고리 구분 없이 저장소 전체를 하나로 취급
- 템플릿 구조: 프론트와 동일하되, **카테고리 괄호 표시 없음** — `이름: (카테고리) : 요약` 대신 `이름 : 요약` 한 줄로 표시 (저장소를 경로별로 나누지 않고 하나로 취급하므로 세부 분류가 필요 없음)
  - 1. 작업 공유 / 2. 이후 작업 공유 / 3. 공유·이슈·질문 공유 / 4. 프론트 미팅 공유 사항 (프론트 회의록의 "백엔드 미팅 공유 사안"과 대칭)
- 페이지 제목 형식: `MM월 DD일 미팅` (프론트와 동일)
- 실행 요일/시간: **매주 월요일 07:47 KST** (`47 22 * * 0` UTC, 즉 UTC 기준 일요일 22:47) — "개발 미팅"(통합 회의록, 월요일 15:17 KST) 전에 미리 채워져 있어야 하므로 오전 8시 이전으로 이르게 잡음
- 백엔드 회의록에 "프론트 미팅 공유 사항" 섹션을 넣어, 프론트 회의록의 "백엔드 미팅 공유 사안"과 대칭되는 양방향 구조 완성 ([combined-report-plan.md](./combined-report-plan.md) 참고)

## 구현된 것

- `backend/weekly_report.py` — 메인 스크립트
- `backend/test_weekly_report.py` — self-check 테스트
- `.github/workflows/backend-weekly-report.yml` — 스케줄 워크플로 (크론 확정)

## 확정된 스페이스/폴더

`03-백엔드` 스페이스 > `회의록` 폴더 > `통합 YY년 M월` 월별 폴더. 프론트/통합과 동일한 2단계 구조.

## 참고

- [combined-report-plan.md](./combined-report-plan.md) — 프론트+백엔드 통합 회의록 계획. 통합 스크립트가 이 회의록의 "4. 프론트 미팅 공유 사항" 섹션을 파싱해서 가져감
- 참고 구현체는 `../frontend/weekly_report.py`, 공용 헬퍼는 `../common/confluence_client.py`
