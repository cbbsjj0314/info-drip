# Agent 작업 workflow

## 목적

이 문서는 InfoDrip에서 spec-driven, PR-native 방식으로 작업하고 backend CI와 human review를 함께 사용하는 agent runbook이다.

기본 흐름은 다음과 같다.

```text
Spec
→ Ticket
→ Agent implementation
→ PR
→ Validation / Checks
→ Review
→ Human Gate
→ Release
```

관련 문서의 책임은 다음과 같이 나눈다.

- `AGENTS.md`: repo-level agent policy
- `.github/PULL_REQUEST_TEMPLATE.md`: PR body format
- `docs/runbook/documentation-style.md`: documentation style, Korean-first 판단, literal 보존, reader 분류, privacy, docs-code consistency policy
- `README.md`, `backend/README.md`, `docs/architecture.md`: 현재 product/backend 동작을 설명하는 reference
- `docs/runbook/agent-workflow.md`: 반복 가능한 작업 절차와 검토 기준

---

## 역할

### ChatGPT

- 제품 기획, spec 정리, ticket 설계, agent execution prompt 작성을 돕는다.
- PR review 보조를 할 수 있지만 최종 merge/release 판단은 하지 않는다.
- risky decision은 Human Gate로 올린다.

### Codex

- approved ticket 단위로 구현한다.
- ticket scope 안에서 branch 생성, commit, push, PR 준비 또는 생성을 할 수 있다.
- 구현 전 repo 상태, 관련 코드, 관련 문서를 확인한다.
- 테스트와 검증 결과를 PR과 완료 보고에 남긴다.
- merge, release, tag 생성은 하지 않는다.

### Human

- spec과 ticket scope를 승인한다.
- risky decision, Human Gate Required ticket, merge, release를 판단한다.
- physical iPad smoke 같은 manual QA를 수행하거나 최종 승인한다.

### Validation / review

- backend 변경은 local backend validation과 backend CI로 확인한다.
- iPad 변경은 가능한 환경에서 local iPad build validation을 수행한다.
- physical iPad smoke는 manual QA로 둔다.
- iOS CI 자동화는 deferred이며, 이 workflow 정리 작업에서 GitHub Actions workflow를 추가하지 않는다.

---

## Ticket 기준

Ticket은 agent가 구현할 수 있을 만큼 scope, acceptance criteria, validation 기대가 정리된 작업 단위다.

- 가능하면 one ticket = one branch/PR로 끝낸다.
- strong dependency가 있으면 ticket order를 명시한다.
- high-risk ticket은 `Human Gate Required: Yes`로 표시한다.
- ticket은 구현 prompt 그 자체가 아니라, agent execution prompt로 쉽게 변환 가능한 source다.
- agent execution prompt는 ticket을 바탕으로 현재 repo 상태, 허용 범위, validation, reporting 요구를 함께 담아 실행 지시로 만든다.

Ticket에는 최소한 다음을 포함한다.

- Goal
- Scope
- Out of Scope
- Requirements
- Acceptance Criteria
- Required Checks
- Manual QA
- Risk Level
- Human Gate Required
- Suggested Branch Name
- Suggested PR Title
- Dependencies / Order

Template은 `docs/runbook/ticket-template.md`를 사용한다.

Ticket의 `Required Checks`는 작업 유형에 맞는 local validation, backend CI 확인, local iPad build validation, manual QA 기대를 뜻한다. GitHub branch protection이나 required status check enforcement를 전제로 하지 않는다.

---

## 작업 전 precheck

작업을 시작하기 전에 agent는 repo의 현재 상태와 작업 경계를 확인한다.

### 먼저 확인할 자료

- `AGENTS.md`
- `docs/runbook/agent-workflow.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- 작업과 관련된 source/test/docs 파일
- 필요한 경우 `docs/architecture.md`
- 참고가 필요한 경우 `docs/local/NEXT.md`, `docs/local/PROJECT_BRIEF.md`, `docs/local/checkpoints/`

`docs/local/`은 source of truth가 아니라 planning board다. 작업 전에는 repo code, recent PR, relevant docs와 대조한다.

### 작업 유형 구분

작업 시작 전에 다음 중 어디에 해당하는지 구분한다.

- docs-only 변경
- backend runtime/code 변경
- backend API behavior 변경
- database schema/model 변경
- LLM prompt/schema/provider 변경
- iPad UI/client 변경
- repo bootstrap/config 변경
- security 관련 변경

### 수정 전 확인할 boundary

다음이 모호하면 구현 전에 질문하거나 Human Gate로 올린다.

- task boundary
- API contract
- DB schema contract
- LLM request/response schema
- PDF 저장 방식
- selected text와 surrounding context의 책임 경계
- iPad client와 backend의 책임 경계
- validation 방법
- security boundary

---

## Branch / Commit / PR 규칙

Approved ticket이면 Codex는 작업 branch를 만들고, commit, push, PR 준비 또는 생성을 할 수 있다.

- 현재 branch가 `main`이면 새 working branch를 만든다.
- branch name은 작업 성격 중심으로 짓는다.
- 권장 prefix: `feat/`, `fix/`, `docs/`, `chore/`, `test/`, `refactor/`
- `codex/`, `agent/`는 기본 branch naming convention으로 사용하지 않는다.
- AI 작업 여부를 branch prefix나 PR body에 기본으로 명시할 필요는 없다.
- commit subject는 `type(scope): summary` 형식을 선호한다.
- PR title은 commit보다 한 단계 위에서 PR 전체 변경을 요약한다.

금지:

- `main`에 직접 push
- PR merge
- release/tag 생성
- 명시 지시 없는 force-push
- ticket scope 밖 파일 수정
- secret/private data/build artifact commit
- unrelated formatting, rename, refactor
- remote file edit, 단 사용자가 명시적으로 요청한 경우 제외

---

## Human Gate 기준

다음 변경은 ticket에 `Human Gate Required: Yes`를 표시하고, 구현 또는 merge 전에 human 판단을 받는다.

- DB schema 변경
- API contract 변경
- LLM prompt/schema/provider 변경
- LLM 비용 증가 가능성이 있는 UX
- deletion/cascade policy
- private PDF/user data 저장 방식 변경
- release/tag/deploy
- public architecture 방향 변경
- security boundary 변경

Human Gate가 필요한 변경은 PR 본문에도 이유와 남은 판단 지점을 남긴다.

---

## InfoDrip MVP Boundary

InfoDrip은 개인용 local-first iPad PDF reading assistant이며, selected text를 중심으로 읽기와 학습을 이어 가는 workflow다. 상세한 현재 동작과 deferred scope는 `AGENTS.md`, `README.md`, `backend/README.md`, `docs/architecture.md`를 기준으로 확인한다.

작업자는 다음 핵심 경계를 유지한다.

- iPad 앱에는 LLM API key를 저장하지 않는다.
- backend가 LLM provider를 호출한다.
- LLM 요청에는 selected text와 bounded same-page context만 사용하며, full private PDF text를 요청마다 보내지 않는다.
- LLM output은 persistence 전에 validation한다.
- Public artifact에는 secret이나 private data를 넣지 않는다.
- `review_cards`는 backend/API capability지만 separate review card list/detail/edit/delete UX는 deferred다.

---

## 작업 중 원칙

- 가장 작은 유용한 변경을 우선한다.
- speculative abstraction이나 미래 platform 동작을 추가하지 않는다.
- 요청된 작업과 무관한 파일을 건드리지 않는다.
- 아직 필요하지 않은 directory, module, interface를 과하게 만들지 않는다.
- API route에 비즈니스 로직을 과하게 넣지 않는다.
- LLM 호출 코드를 route에 직접 박지 않는다.
- provider-specific code를 전체 codebase에 퍼뜨리지 않는다.
- LLM output을 trusted data로 취급하지 않는다.
- private PDF 내용, local path, token, API key, provider account detail을 docs, comments, logs, fixtures, screenshots에 남기지 않는다.

---

## Documentation boundary

Documentation style, Korean-first 판단, code-facing literal 보존, primary reader 분류, UI/API/comments/tests scope 분리, privacy/security 예시, docs-code consistency 확인은 `docs/runbook/documentation-style.md`를 source of truth로 따른다.

Workflow에서는 다음 최소 경계를 유지한다.

- Durable human-facing docs는 Korean-first로 작성한다.
- Code-facing identifier와 literal은 원문 그대로 보존한다.
- Public artifact에는 secret, private data, private/local path를 넣지 않고 sanitized example만 사용한다.
- `docs/local/**`는 local/planning-only material이며 current behavior의 source of truth가 아니다.
- README와 `docs/architecture.md`는 approved ticket scope에 포함될 때만 수정한다.

---

## Validation / Checks

변경 유형에 따라 validation을 다르게 적용한다.

### Docs-only 변경

Runtime validation은 생략할 수 있다.

대신 변경한 문서를 다시 읽고 다음을 확인한다.

- outdated claim 없음
- 중복 guidance가 과하지 않음
- MVP 범위를 넘는 약속 없음
- public docs에 secret, private data, private/local path 없음
- `AGENTS.md`는 짧고 상세 절차는 runbook에 있음
- approved ticket의 branch/commit/push/PR 허용 규칙과 금지 규칙이 충돌하지 않음

완료 보고에는 다음처럼 적는다.

- `Not run (docs-only change)`

### Backend runtime/code 변경

Backend 변경 기본 validation:

- `backend/scripts/check.sh`

이 script는 `backend/` directory에서 다음을 실행한다.

- `uv run ruff check .`
- `uv run pytest`

Backend API behavior를 바꿨다면 가능한 경우 relevant narrow smoke check도 수행한다.

### Database 변경

DB model 또는 schema를 바꿨다면 다음을 확인한다.

- table/field 이름이 ticket과 맞는지
- foreign key 관계가 document 중심 학습 흐름과 맞는지
- migration 또는 init path가 현재 repo 정책과 맞는지
- sample data나 local DB 파일이 commit되지 않는지

가능하면 backend validation을 함께 실행한다.

### LLM prompt/schema/provider 변경

다음을 확인한다.

- API key가 코드나 docs에 노출되지 않았는지
- prompt가 selected text와 context를 분리하는지
- full PDF를 보내는 구조가 아닌지
- output schema가 명확한지
- validation 실패 처리 경로가 있는지
- `llm_request_logs`에 필요한 정보가 남는지
- fake/mock provider로 테스트 가능한지

Real provider smoke는 사용자가 명시적으로 요청하거나 local 환경이 준비된 경우에만 수행한다.

### iPad 변경

가능한 환경에서 iPad build는 local iPad build validation으로 수행한다.

기본 command:

```sh
xcodebuild -project ios/InfoDrip/InfoDrip.xcodeproj -scheme InfoDrip -destination 'generic/platform=iOS' build
```

Physical iPad smoke는 manual QA로 둔다.

예:

- PDF import
- PDFKit reader 표시
- selected text quick action
- backend base URL 설정
- quiz study/review-again flow

iOS CI 자동화는 deferred이며, 별도 approved ticket 없이 GitHub Actions workflow를 추가하지 않는다.

---

## PR 작성 기준

- PR body 구조는 `.github/PULL_REQUEST_TEMPLATE.md`를 따른다.
- PR body는 Korean-first로 작성하고 code-facing identifier와 literal은 원문 그대로 보존한다.
- Validation / Checks에는 실제로 수행한 command, backend CI 확인, local iPad build validation, manual QA 결과를 정직하게 기록한다.
- Docs-only PR은 `Not run (docs-only change)`와 changed docs reread 결과를 기록할 수 있다.

---

## Reporting format

작업 완료 보고는 다음 형식을 기본으로 한다.

1. 변경 파일
2. 변경 요약
3. Validation 결과
4. 명시적으로 제외한 것
5. 남은 리스크 / 다음 작업 판단
6. PR을 생성했다면 PR title과 link
7. PR을 생성하지 못했다면 이유와 사용자가 해야 할 git/PR 작업

보고는 짧고 구체적으로 작성한다.
