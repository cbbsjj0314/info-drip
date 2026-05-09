# Agent 작업 workflow

## 목적

이 문서는 InfoDrip에서 AI coding agent에게 작업을 맡기기 전후에 확인할 수 있는 수동 workflow와 검토 기준을 정리한다.

목표는 자동화 플랫폼을 만드는 것이 아니라, 반복해서 prompt에 넣던 작업 규칙을 repo 안의 durable 문서로 옮겨 짧고 일관된 작업 지시를 가능하게 하는 것이다.

`AGENTS.md`는 repo-level 규칙을 짧게 정의하고, 이 문서는 반복 가능한 작업 절차와 검토 기준을 더 구체적으로 설명한다.

---

## 언제 사용하는가

다음 상황에서 이 runbook을 참조한다.

- repo-level 작업 규칙을 agent에게 짧게 전달해야 할 때
- 변경 전 precheck와 작업 boundary를 맞춰야 할 때
- docs-only 변경과 runtime/code 변경의 validation 기준을 구분해야 할 때
- backend 작업과 iPad 작업의 검증 기준을 구분해야 할 때
- LLM API key, PDF 원문, local-only 자료의 노출 위험을 점검해야 할 때
- 작업 완료 보고 형식을 일관되게 유지해야 할 때
- public docs에 올릴 수 있는 내용과 local-only 자료를 구분해야 할 때

---

## 기본 원칙

InfoDrip은 iPad PDF 학습 보조 앱이다.

MVP의 핵심 흐름은 다음과 같다.

    PDF upload
    → PDF reading
    → text selection
    → highlight persistence
    → LLM explanation
    → glossary extraction
    → question answering
    → quiz generation
    → quiz attempt tracking
    → wrong answer tracking
    → review card generation
    → document-level study record lookup

작업자는 항상 다음 경계를 유지한다.

- iPad 앱에는 LLM API key를 저장하지 않는다.
- LLM API key는 backend environment variable로만 관리한다.
- iPad 앱은 backend API만 호출한다.
- backend가 LLM provider를 호출한다.
- PDF 전체를 매번 LLM에 보내지 않는다.
- LLM 요청에는 선택 텍스트와 필요한 주변 문맥만 보낸다.
- LLM output은 가능한 JSON으로 받고 validation 후 저장한다.
- 학습 기록은 DB에 저장한다.
- LLM 요청별 provider, model, token usage, latency, status, estimated cost를 기록한다.
- OCR, RAG, LLM streaming, 계정 시스템, 결제, 공개 배포는 MVP 범위가 아니다.

---

## 작업 전 precheck

작업을 시작하기 전에 agent는 먼저 repo의 현재 상태와 작업 경계를 확인한다.

### 1. 읽을 파일

가능하면 다음 파일을 먼저 확인한다.

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `docs/runbook/agent-workflow.md`
- `docs/planning/` 아래 관련 문서
- `backend/pyproject.toml` 또는 `pyproject.toml`
- 작업과 관련된 source/test 파일

필요한 경우 local-only 문서도 확인한다.

- `docs/local/NEXT.md`
- `docs/local/WORKING_RULES.md`
- `docs/local/checkpoints/`

단, `docs/local/`은 Git에 commit되지 않는 private working material일 수 있다.  
local docs를 읽을 수 없고 작업 판단에 꼭 필요하면, 어떤 정보가 필요한지 사용자에게 요청한다.

### 2. 작업 유형 구분

작업을 시작하기 전에 다음 중 어디에 해당하는지 구분한다.

- docs-only 변경
- backend runtime/code 변경
- backend API behavior 변경
- database schema/model 변경
- LLM prompt/schema/provider 변경
- iPad UI/client 변경
- repo bootstrap/config 변경
- security 관련 변경

### 3. boundary 확인

다음이 모호하면 수정 전에 질문한다.

- task boundary
- API contract
- DB schema contract
- LLM request/response schema
- PDF 저장 위치
- 선택 텍스트와 주변 문맥의 책임 경계
- iPad client와 backend의 책임 경계
- validation 방법
- security boundary

### 4. 짧은 plan 작성

작업 전 plan에는 다음을 포함한다.

- 읽은 파일
- 선택한 smallest useful slice
- 변경할 파일
- 변경하지 않을 파일
- validation 계획
- out-of-scope 확인
- 관련 assumptions

예:

- `AGENTS.md`, `docs/local/NEXT.md`, 관련 API 파일을 확인했다.
- 이번 slice는 `documents` upload API skeleton까지만 다룬다.
- `LLM provider`, `quiz`, `iPad UI`는 건드리지 않는다.
- validation은 `uv run ruff check .`, `uv run pytest`로 한다.

---

## 작업 중 원칙

작업은 요청된 slice에 맞춰 작게 진행한다.

- 가장 작은 유용한 변경을 우선한다.
- speculative abstraction이나 미래 platform 동작을 추가하지 않는다.
- unrelated formatting, rename, refactor를 하지 않는다.
- 요청된 작업과 무관한 파일을 건드리지 않는다.
- 아직 필요하지 않은 directory, module, interface를 과하게 만들지 않는다.
- Android는 후속 client로 보고 MVP 구현에 섞지 않는다.
- OCR, RAG, LLM streaming, 계정 시스템, 결제, 공개 배포를 임의로 추가하지 않는다.
- branch, commit, PR, issue, label은 사용자가 명시적으로 요청하지 않으면 만들지 않는다.
- remote tool로 파일을 직접 수정하는 것도 사용자가 명시적으로 요청하지 않으면 하지 않는다.

---

## Backend 작업 기준

Backend는 FastAPI 기반이다.

MVP backend는 다음 책임을 가진다.

- PDF upload
- PDF file storage
- page count extraction
- page text extraction
- document metadata persistence
- highlight persistence
- LLM task API
- LLM provider interface
- LLM request logging
- study record lookup

Backend 작업 시 다음을 지킨다.

- API route에 비즈니스 로직을 과하게 넣지 않는다.
- LLM 호출 코드를 route에 직접 박지 않는다.
- service layer와 provider interface를 분리한다.
- LLM provider는 DB를 직접 알지 않게 한다.
- DB 저장은 service/repository layer에서 처리한다.
- request/response schema는 Pydantic으로 명확히 둔다.
- LLM output은 저장 전에 schema validation을 통과해야 한다.
- 실패한 LLM 요청도 가능하면 `llm_request_logs`에 기록한다.
- API key, token, provider account detail은 코드와 docs에 쓰지 않는다.

---

## Database 작업 기준

MVP DB는 SQLite를 기본으로 한다.

주요 persistence 대상은 다음이다.

- `documents`
- `document_pages`
- `highlights`
- `llm_explanations`
- `glossary_terms`
- `user_questions`
- `quizzes`
- `quiz_attempts`
- `review_cards`
- `llm_request_logs`

DB 작업 시 다음을 지킨다.

- MVP에 필요한 table만 추가한다.
- broad analytics, dashboard, recommendation engine, complex review scheduling을 임의로 추가하지 않는다.
- 학습 기록을 나중에 조회할 수 있도록 document 중심 foreign key 흐름을 유지한다.
- LLM 결과는 raw text만 저장하지 말고, 앱에서 쓰기 쉬운 구조화된 field로 저장한다.
- token usage, latency, status, estimated cost를 추적할 수 있게 한다.
- migration 도구를 도입할지 여부가 정해지지 않았다면 과하게 확장하지 않는다.

---

## LLM 작업 기준

LLM은 단일 generic chat layer가 아니라 task-specific workflow로 사용한다.

MVP LLM task:

- explanation generation
- glossary extraction
- question answering
- quiz generation
- review card generation

후순위 task:

- weakness analysis

LLM 작업 시 다음을 지킨다.

- prompt에는 selected text와 surrounding context를 명확히 구분한다.
- PDF 전체 원문을 매번 보내지 않는다.
- 문서에 없는 내용을 확정적으로 말하지 않게 한다.
- 가능한 JSON output을 사용한다.
- output schema를 명시한다.
- Pydantic 또는 equivalent schema로 validation한다.
- provider-specific code를 전체 codebase에 퍼뜨리지 않는다.
- OpenAI-compatible provider interface를 우선한다.
- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` 같은 값은 environment variable로 관리한다.
- real API key를 fixture, docs, logs, screenshots에 남기지 않는다.

---

## iPad 작업 기준

첫 client는 iPad native app이다.

기본 stack:

- Swift
- SwiftUI
- PDFKit
- URLSession
- local file handling

iPad 작업 시 다음을 지킨다.

- LLM API key를 앱에 넣지 않는다.
- iPad app은 backend API만 호출한다.
- PDFKit 기반 PDF reading과 text selection을 우선한다.
- PDF text selection이 가능한 PDF를 MVP 대상으로 둔다.
- OCR이나 Apple Pencil handwriting recognition을 임의로 추가하지 않는다.
- API response DTO와 UI model의 책임을 구분한다.
- backend API contract가 불명확하면 먼저 확인한다.
- Android 확장 가능성은 고려하되, iPad MVP 구현을 복잡하게 만들지 않는다.

---

## Documentation guide

Durable public docs와 local working docs는 한국어로 작성한다.

다만 code-facing identifier는 번역하지 않는다.

번역하지 않을 예:

- `endpoint`
- `route`
- `table`
- `model`
- `schema`
- `view`
- `API`
- `CLI`
- command name
- module name
- class name
- function name
- config key
- filename

Public docs에는 안정된 정보만 남긴다.

예:

- problem statement
- architecture
- setup
- usage
- design decisions
- data model
- API contract
- testing strategy
- security principles

Public docs에 넣지 않을 것:

- real API key
- token
- credential
- private PDF content
- raw private document text
- private/local path
- provider account detail
- private endpoint detail
- temporary execution log 전문
- local debugging dump
- private runtime data

---

## Local docs guide

`docs/local/`은 local-only working material이다.

예:

- `docs/local/NEXT.md`
- `docs/local/WORKING_RULES.md`
- `docs/local/checkpoints/`
- handoff notes
- local debugging notes
- temporary runbooks

`docs/local/NEXT.md`는 live execution board다.

권장 section:

- Now
- Next
- Later
- Blockers
- Decisions
- Done

운영 원칙:

- 짧게 유지한다.
- 상세 changelog로 만들지 않는다.
- 현재 slice 중심으로 유지한다.
- `Done`이 길어지면 `docs/local/checkpoints/`로 옮긴다.
- checkpoint는 slice 단위로 저장한다.
- checkpoint 이름은 정렬 가능하게 작성한다.

예:

    docs/local/checkpoints/0001-repository-bootstrap.md
    docs/local/checkpoints/0002-backend-skeleton.md
    docs/local/checkpoints/0003-document-upload-api.md

---

## Validation guide

변경 유형에 따라 validation을 다르게 적용한다.

### Docs-only 변경

Runtime validation은 생략할 수 있다.

대신 변경한 문서를 직접 다시 읽고 다음을 확인한다.

- 오래된 주장 없음
- 중복된 guidance 없음
- MVP 범위를 넘는 과한 약속 없음
- InfoDrip와 맞지 않는 이전 프로젝트 이름 없음
- public docs에 secret, private data, private path 없음
- `AGENTS.md`와 runbook의 역할 중복이 과하지 않음

완료 보고에는 다음처럼 적는다.

- `Not run (docs-only change)`

### Backend runtime/code 변경

기본 validation:

- `uv run ruff check .`
- `uv run pytest`

API behavior를 바꿨다면 가능한 경우 narrow smoke check도 수행한다.

예:

- `GET /health`
- document upload API smoke
- highlight creation API smoke

아직 smoke command가 정리되지 않았다면, 어떤 검증이 가능한지 보고한다.

### Database 변경

DB model 또는 schema를 바꿨다면 다음을 확인한다.

- table/field 이름이 기획과 맞는지
- foreign key 관계가 문서 중심 흐름과 맞는지
- 기존 test가 깨지지 않는지
- migration 또는 init path가 현재 repo 정책과 맞는지
- sample data나 local DB 파일이 commit되지 않는지

가능하면 backend validation을 함께 실행한다.

- `uv run ruff check .`
- `uv run pytest`

### LLM prompt/schema/provider 변경

다음을 확인한다.

- API key가 코드나 docs에 노출되지 않았는지
- prompt가 selected text와 context를 분리하는지
- full PDF를 보내는 구조가 아닌지
- output schema가 명확한지
- validation 실패 시 처리 경로가 있는지
- `llm_request_logs`에 필요한 정보가 남는지
- fake/mock provider로 테스트 가능한지

Real provider smoke는 사용자가 명시적으로 요청하거나 local 환경이 준비된 경우에만 수행한다.

### iPad 변경

가능한 경우 Xcode build/test를 수행한다.

현재 환경에서 Xcode validation이 불가능하면 다음을 보고한다.

- Xcode validation을 실행하지 못한 이유
- 대신 확인한 내용
- 사용자가 로컬에서 실행해야 할 command 또는 action

예:

- Xcode에서 project 열기
- target build
- simulator 또는 iPad에서 PDF import 확인
- backend base URL 설정 확인

---

## Validation 실패 또는 미실행 시 보고

Validation을 실행할 수 없으면 완료 보고에 다음을 남긴다.

- 시도한 command
- 실패 이유
- 대신 확인한 내용
- 남은 risk
- 사용자가 로컬에서 확인해야 할 것

예:

    Validation:
    - `uv run pytest`: not run, backend skeleton not initialized yet
    - Docs reread: passed
    - Risk: API smoke는 backend app 생성 후 가능

---

## Reporting format

작업 완료 보고는 다음 형식을 기본으로 한다.

1. 변경 파일
2. 변경 요약
3. 검증 결과
4. 명시적으로 제외한 것
5. 위험/메모/사용자 확인 필요 사항

보고는 짧고 구체적으로 작성한다.

좋은 보고 예:

    변경 파일
    - `backend/app/main.py`
    - `backend/tests/test_health.py`

    변경 요약
    - FastAPI app skeleton을 추가했다.
    - `GET /health` endpoint를 추가했다.

    검증
    - `uv run ruff check .`: passed
    - `uv run pytest`: passed

    제외
    - document upload API는 다음 slice로 남겼다.

Security 관련 변경이라면 다음도 포함한다.

- 노출됐거나 노출 가능성이 있었던 것
- rotate 또는 revoke한 것
- 남은 deferred 항목

---

## Git and PR guide

사용자가 명시적으로 요청하지 않으면 다음을 하지 않는다.

- branch 생성
- commit 생성
- push
- pull request 생성
- issue 생성
- label 수정
- merge
- remote file edit

사용자가 git 작업을 요청한 경우:

- 한 작업 item당 하나의 branch를 선호한다.
- commit subject는 `type(scope): summary` 형식을 선호한다.
- suggested types:
  - `feat`
  - `fix`
  - `test`
  - `docs`
  - `chore`
  - `refactor`

예:

- `chore(repo): bootstrap project structure`
- `docs(planning): add MVP project brief`
- `feat(api): add document upload endpoint`
- `test(api): cover highlight creation`

PR 본문은 `.github/PULL_REQUEST_TEMPLATE.md`가 있으면 그 형식을 따른다.

---

## Slice 운영 방식

작업은 slice 단위로 진행한다.

좋은 slice 예:

- repository bootstrap
- backend FastAPI skeleton
- document upload API
- document_pages extraction
- highlight creation API
- fake LLM provider
- explanation API
- iPad PDF import
- PDFKit reader
- selected text save flow

나쁜 slice 예:

- backend 전체 구현
- iPad 앱 전체 구현
- LLM 기능 전부 구현
- RAG까지 같이 구현
- Android까지 같이 구현

각 slice는 다음 기준으로 마무리한다.

- smallest useful result가 있다.
- 관련 validation을 수행했거나 못 한 이유를 보고했다.
- 의도적으로 제외한 범위를 남겼다.
- 필요하면 `docs/local/NEXT.md`의 Done에 기록했다.
- slice가 끝나면 필요한 내용만 checkpoint로 정리했다.

---

## Public/private data governance

InfoDrip은 PDF와 LLM API를 다루므로 data governance를 명확히 지킨다.

Public docs, prompt, log, screenshot, fixture, report에 넣지 않는다.

- LLM API key
- backend access token
- provider account detail
- private PDF file
- raw PDF text
- private/local path
- private endpoint detail
- local DB content
- temporary execution log 전문
- user-specific runtime data

Public docs에는 sanitized example만 사용한다.

예:

    selected_text: "Schema drift occurs when incoming data changes unexpectedly."

실제 개인 PDF 원문, 유료 자료 원문, private 문서의 긴 발췌는 public docs에 넣지 않는다.

---

## Out-of-scope reminder

다음은 MVP에서 제외한다.

- OCR
- RAG
- vector DB
- LLM streaming
- user account system
- payment
- public deployment
- complex spaced repetition
- real-time collaboration
- Apple Pencil handwriting recognition
- Android implementation
- full PDF annotation editor

이 항목이 필요해 보이더라도, 사용자가 명시적으로 요청하지 않으면 backlog 또는 deferred로 남긴다.
