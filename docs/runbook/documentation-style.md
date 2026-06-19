# Documentation Style Guide

## 목적과 책임 경계

이 문서는 InfoDrip 문서의 reader 분류, 한국어 우선 작성 여부, inventory audit, literal 보존, privacy/security 검토를 위한 durable runbook이다.

- `AGENTS.md`의 repo-level 규칙과 `.github/PULL_REQUEST_TEMPLATE.md`의 PR 작성 기준을 대체하지 않는다.
- 문서 작업자는 먼저 현재 repo code와 docs를 확인하고, 이 guide로 작업 범위와 표현 방식을 결정한다.
- 번역은 stale claim이나 잘못된 구현 설명을 숨기는 수단이 아니다.

## 범위

이 guide는 다음에 적용한다.

- `README.md`, `backend/README.md`, `docs/architecture.md`
- `docs/runbook/*.md`, `docs/planning/*.md`
- `AGENTS.md`, `.github/PULL_REQUEST_TEMPLATE.md`
- boundary 확인이 필요한 `docs/local/**`
- UI copy, API/client-visible message, comment/docstring, test/fixture를 문서 inventory에서 발견했을 때의 분류

다음 작업은 보통 각각 별도 PR scope로 분리한다.

- durable public docs Koreanization
- docs style guide 변경
- README rewrite
- architecture docs cleanup
- local checkpoint cleanup
- UI localization
- API/client-visible message 변경
- comments/docstrings rewrite
- tests/fixtures string 변경
- generated file cleanup

## Primary reader classification

문서나 section의 주 독자를 먼저 하나로 분류한다.

| 값 | 의미 | InfoDrip의 일반적인 대상 | 언어 경향 |
| --- | --- | --- | --- |
| `operator_facing` | local 실행, 설정, 운영 절차를 수행하는 사람 대상 | `backend/README.md`, `docs/runbook/*.md`의 실행 절차 | Korean-first, command와 config는 원문 유지 |
| `agent_facing` | coding agent의 판단과 작업 경계를 정의 | `AGENTS.md`, agent용 runbook section | tool compatibility에 유리하면 English 유지 가능 |
| `public_facing` | repo 방문자와 사용자에게 제품과 현재 상태를 설명 | `README.md`, `docs/architecture.md`, approved public planning docs | Korean-first |
| `developer_facing` | 구현 contract와 개발 절차를 설명 | `backend/README.md`, `docs/architecture.md`, `docs/runbook/*.md`, `docs/planning/*.md` | Korean-first prose, technical literal은 원문 유지 |
| `mixed_reader` | 둘 이상의 독자군이 section별로 공존 | `.github/PULL_REQUEST_TEMPLATE.md`, 일부 `docs/runbook/*.md`, `docs/planning/*.md` | section별 reader에 따라 분리 결정 |

`docs/local/**`는 주로 local operator/developer용 working material이다. public durable docs로 간주하지 않는다.

## Translation decision classification

Primary reader를 분류한 다음 translation decision을 정한다. 기존 문서를 English 표현이 있다는 이유만으로 일괄 번역하지 않는다.

| 값 | 사용할 때 | 변경하지 않을 것 |
| --- | --- | --- |
| `translate_korean_first` | durable human-facing prose를 새로 쓰거나 approved scope에서 정리할 때 | identifier, literal, command, 의미가 확정되지 않은 claim |
| `keep_english` | agent/tool compatibility 또는 code-facing reference에서 English가 더 정확할 때 | 정확한 technical term과 tool input 형식 |
| `preserve_literals_only` | 주변 설명은 번역하되 code/API와 결합된 표현을 그대로 유지해야 할 때 | endpoint, schema, enum/string literal 등 literal 전체 |
| `split_by_section` | `mixed_reader` 문서에서 독자와 목적이 section마다 다를 때 | 다른 section의 언어 결정을 일괄 적용하지 않음 |
| `defer_to_separate_scope` | 번역이 UI/API/test/runtime contract나 대규모 rewrite로 이어질 때 | 현재 PR scope 밖 파일과 동작 |

- `README.md`에 English term이 남아 있다는 사실만으로 full rewrite가 필요하다고 판단하지 않는다.
- mixed file은 문서 전체가 아니라 section별로 `split_by_section`할 수 있다.
- translation decision과 구현 사실 수정이 함께 필요하면 scope를 명시하고 관련 docs PR에서 stale claim을 먼저 바로잡는다.

## Inventory classification

다음 값은 audit/classification label이며, 발견한 항목을 현재 PR에 반드시 포함한다는 scope label이 아니다.

| 값 | 의미와 포함/보류 기준 |
| --- | --- |
| `public_docs_candidate` | public durable docs의 작성·번역 후보. approved public docs scope일 때 포함한다. |
| `operator_facing_candidate` | local 실행·설정·운영 안내 후보. 실제 절차와 command 검증이 가능할 때 포함한다. |
| `agent_facing_review_only` | agent instruction 검토 대상. tool compatibility가 중요하므로 자동 번역하지 않는다. |
| `developer_reference_keep_english` | code contract 중심 reference. English 또는 원문 literal 유지가 정확할 때 보류하거나 그대로 둔다. |
| `ui_localization_candidate` | iPad UI copy 후보. docs PR에서 제외하고 UI localization scope로 넘긴다. |
| `api_or_client_message_candidate` | API response나 client-visible message 후보. behavior/test 영향이 있으므로 별도 scope로 넘긴다. |
| `comment_or_docstring_review_only` | comment/docstring 검토 대상. code intent와 유지보수성을 확인하고 별도 code scope에서 다룬다. |
| `test_or_fixture_coupled` | test/fixture와 결합된 string. assertion·contract 영향 검토 없이 변경하지 않는다. |
| `already_sufficiently_korean` | 현재 reader에게 충분히 한국어로 설명되어 추가 번역이 불필요하다. |
| `generated_or_excluded` | generated artifact, ignored dependency, build output 등 유지보수 문서 대상이 아니다. |
| `manual_review_needed` | reader, literal, privacy, runtime contract가 불명확해 사람이 판단해야 한다. |

`docs/local/**`에는 다음 boundary를 적용한다.

- local-only working material이며 public changelog가 아니다.
- 기본적으로 public durable docs나 Koreanization inventory에 포함하지 않는다.
- local planning/checkpoint 내용을 public docs로 옮기기 전에 sanitize하고 현재 repo 상태와 대조한다.
- `docs/local/**` 파일이 tracked 상태라면 boundary-sensitive artifact로 보고 공개 가능성, private data, stale claim을 주의 깊게 검토한다.

## Literal / identifier 보존 규칙

실제 code/API가 바뀌지 않는 한 다음 항목은 번역, rename, paraphrase, 임의 reformat하지 않는다.

- code-facing identifier
- endpoint, route, table, model, schema, view
- API, CLI, command
- module, class, function, config key
- filename, package name, library name, framework name, proper noun
- enum/string literal, environment variable, HTTP method
- path parameter, query parameter, database field
- Swift/Python symbol

예:

- `POST /api/v1/documents`
- `GET /api/v1/quiz-attempts/review-again`
- `documents`, `quiz_attempts`, `review_cards`, `llm_request_logs`
- `INFODRIP_BACKEND_BASE_URL`, `INFODRIP_OPENAI_API_KEY`
- `Local.xcconfig`, `backend/scripts/check.sh`, `QuickActionPanel`

설명 문장은 Korean-first로 쓸 수 있지만 위 literal의 spelling, case, separator, code formatting은 유지한다.

## Markdown formatting 규칙

- 짧은 section과 bullet을 우선한다.
- table은 비교가 명확해질 때만 사용한다.
- code block은 유용한 경우 language label을 붙여 fenced block으로 작성한다.
- 실제 command를 업데이트하는 작업이 아니면 command snippet을 그대로 보존한다.
- repo 내부 참조는 relative path를 사용하고 private local absolute path를 쓰지 않는다.
- heading은 구체적으로 작성한다.
- broad product/production promise와 과도한 emphasis를 피한다.
- runbook을 progress log나 영구 changelog로 만들지 않는다.

## Privacy / security boundary

Public docs, prompt, log, screenshot, fixture, report에는 다음을 포함하지 않는다.

- raw private PDF content, selected passage, extracted full page text
- generated LLM output 전문, LLM request logs
- private/local paths, provider account details, API keys, tokens, private runtime data
- local DB content, uploaded PDF artifacts
- real `.env` values, real `Local.xcconfig` values
- 의도적으로 sanitize하지 않은 real private network host details

필요한 예시는 다음과 같은 sanitized placeholder를 사용한다.

- `<BACKEND_HOST>`
- `<set in local env only>`
- `<redacted>`
- `<LOCAL_REPO_PATH>`

## Docs-code consistency 확인

다음 claim은 checked-in code, config, workflow, test 또는 current docs source of truth로 검증하거나 아직 미확인임을 표시한다.

- implemented API endpoints
- database tables/models
- iPad UI flow
- validation commands
- GitHub Actions behavior
- LLM provider behavior
- config behavior
- security/runtime boundaries
- out-of-scope features

문서는 current implemented behavior, MVP boundary, future/deferred scope를 섞지 않는다. 특히 backend behavior, iPad behavior, LLM provider behavior, `review_cards`, Android, OCR, RAG, LLM streaming, public deployment, iOS CI, physical iPad manual QA를 설명할 때 상태를 명시한다.

Stale claim은 번역으로 모호하게 만들지 말고 approved relevant docs PR에서 수정한다. 확인되지 않은 future behavior를 current behavior처럼 서술하지 않는다.

## Validation

Docs-only change는 다음을 수행한다.

- `git diff --check`
- 변경 문서 reread
- stale claim 확인
- duplicated guidance 확인
- overbroad scope promise 확인
- private data exposure 확인
- MVP boundary mismatch 확인
- `AGENTS.md`와의 conflict 확인
- `.github/PULL_REQUEST_TEMPLATE.md`와의 conflict 확인

Runtime/backend/iPad validation은 docs-only change에서 생략할 수 있다. PR body에 실행하지 않은 validation을 실행했다고 쓰지 않는다.

## PR body / commit / title 기준

- Commit subject는 `AGENTS.md`의 Git conventions를 따른다.
- PR title과 body는 `.github/PULL_REQUEST_TEMPLATE.md`를 따른다.
- PR body는 한국어로 짧고 구체적으로 작성하며 identifier는 원문 그대로 보존한다.
- Docs-only PR은 `Not run (docs-only change)`와 changed docs reread 결과를 validation으로 기록할 수 있다.

PR template 전체를 이 문서에 복제하지 않는다.

## Agent checklist

- [ ] `AGENTS.md`를 읽었다.
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`를 읽었다.
- [ ] 이 guide를 읽었다.
- [ ] Primary reader를 먼저 분류했다.
- [ ] Translation decision을 두 번째로 정했다.
- [ ] Inventory classification을 지정했다.
- [ ] Literal과 identifier를 보존했다.
- [ ] UI/API/comments/tests 변경을 별도 scope로 분리했다.
- [ ] Privacy/security boundary를 확인했다.
- [ ] Docs-code consistency를 확인했다.
- [ ] PR scope를 작게 유지했다.
- [ ] 보고 전에 변경 문서를 다시 읽었다.

## 완료 기준

Documentation style 또는 Koreanization task는 다음을 만족해야 완료다.

- primary reader가 식별되어 있다.
- translation decision이 명시되어 있다.
- literal과 identifier가 보존되어 있다.
- private data가 노출되지 않는다.
- current behavior, MVP boundary, future/deferred scope가 섞이지 않는다.
- validation 결과가 정직하게 보고되어 있다.
- 명시적으로 승인되지 않은 deferred category는 PR scope에서 제외되어 있다.
