# weekly-report-bot

매주 월요일, 지난 한 주간의 GitHub 커밋 로그를 모아 Confluence 주간 회의록 페이지를 자동으로 생성/갱신하는 봇.

## 왜 만들었나

기존엔 회의 전에 사람이 직접 지난주 커밋 내역을 돌아보며 "작업 공유" 섹션을 채워야 했음. 이 스크립트는 그 부분을 자동화해서, 회의 시작 전에 이미 기본 골격(날짜/참여자/작업 공유)이 채워진 상태로 만들어두는 게 목적. "이후 작업 공유"·"이슈"·"전체 공유 사안"처럼 커밋 로그로 알 수 없는 항목은 빈 템플릿으로 남겨두고 회의 중 직접 채우도록 함.

## 기술 스택

- **Python 3.12** + `requests`, `python-dotenv` (의존성 최소화, 별도 SDK 없이 REST API 직접 호출)
- **GitHub REST API** — 저장소별 커밋 로그 조회 (경로 기준으로 카테고리 분류)
- **OpenAI Responses API** (`finditem/QnA-Bot`와 동일한 방식) — 커밋 메시지를 한 줄 요약
- **Confluence REST API v1** — 페이지/폴더 조회·생성·갱신 (storage format으로 본문 작성)
- **GitHub Actions** (`cron`) — 매주 월요일 09:00 KST 자동 실행

## 동작 흐름

1. **GitHub Actions**가 매주 월요일 09:00(KST)에 트리거됨 (`workflow_dispatch`로 수동 실행도 가능)
2. **커밋 수집**: `PEOPLE`에 등록된 인원별로, `REPO_RULES`에 정의된 저장소·경로 규칙에 따라 지난 7일간의 커밋을 GitHub API로 조회
   - `finditem/infra-support`의 `apps/monitor-server`, `apps/monitor-web` 경로 → 모니터링
   - `finditem/infra-support`의 `apps/schedule` 경로 → 일정관리
   - `finditem/FI-FE` 전체 → 운영
3. **요약**: 사람별·카테고리별 커밋 메시지 목록을 OpenAI에 보내 한 줄 요약으로 압축
4. **렌더링**: 팀 회의록 템플릿 구조(날짜, 참여자 멘션, 작업 공유 a./b./c., 이후 작업 공유, 공유·이슈·질문 공유, 전체 회의 공유 사안)에 맞춰 Confluence storage format(XHTML) 생성
5. **월별 폴더 확인/생성**: `회의록 통합` 폴더 아래 이번 달 폴더(예: `통합 26년 7월`)가 있는지 확인, 없으면 새로 생성 (페이지·폴더 타입 구분 없이 정확한 제목으로 검색해서 중복 생성 방지)
6. **업서트**: 그 폴더 아래에 `M월 DD일 미팅` 제목으로 페이지가 이미 있으면 갱신, 없으면 새로 생성

```
GitHub 커밋 로그 → 사람×카테고리별 수집 → OpenAI 요약 → Confluence storage format 렌더링
  → 이번 달 폴더 확인/생성 → 페이지 upsert (있으면 갱신, 없으면 생성)
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `weekly_report.py` | 메인 스크립트 (전체 플로우) |
| `test_weekly_report.py` | 렌더링/파싱 로직 self-check (네트워크 호출 없음) |
| `lookup_account_id.py` | 참여자 `@멘션`용 Confluence accountId 조회 헬퍼 |
| `.github/workflows/weekly-report.yml` | 스케줄 실행 워크플로 |

## 로컬에서 실행하기

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python weekly_report.py
```

## 환경변수

프로젝트 루트에 `.env` 파일을 만들고 아래 값을 채워야 함 (커밋하지 말 것, `.gitignore`에 이미 포함됨):

```
CONFLUENCE_BASE_URL=
CONFLUENCE_EMAIL=
CONFLUENCE_API_TOKEN=
CONFLUENCE_SPACE_KEY=
CONFLUENCE_PARENT_PAGE_ID=

GH_PAT=

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
```

Confluence 인증(이메일+API 토큰), GitHub PAT(`infra-support`/`FI-FE` read 권한), OpenAI 키(QnA-Bot과 동일 계정, 별도 키) 세 그룹이 필요함. GitHub Actions에서 돌릴 땐 저장소 Secrets에 동일한 이름으로 등록.

## 참고

- 새 인원 추가/변경 시 `weekly_report.py`의 `PEOPLE`, `PERSON_CATEGORIES` 수정 필요 (accountId는 `lookup_account_id.py`로 조회)
- 저장소 대상이나 경로별 카테고리 규칙이 바뀌면 `REPO_RULES` 수정
- 커밋 메시지가 OpenAI로 전송되므로, 사내 데이터 정책상 문제 없는지 확인 필요
