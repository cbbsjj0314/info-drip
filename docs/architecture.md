# InfoDrip MVP workflow and architecture

## 1. Product identity

InfoDrip은 개인용 local-first iPad PDF reading assistant다.

핵심은 PDF에서 궁금한 부분을 선택하고, 그 selected text를 중심으로 설명, 용어 정리, 질문/답변, 퀴즈, 다시 풀기 흐름을 이어 가는 것이다. InfoDrip은 generic PDF chatbot, public SaaS, full RAG system, OCR system이 아니다.

Primary MVP client는 SwiftUI와 PDFKit 기반 iPad app이다. Backend는 FastAPI와 SQLite를 사용하며, LLM 호출은 OpenAI-compatible provider boundary 뒤에서 처리한다.

## 2. MVP workflow

현재 MVP workflow는 다음 흐름을 중심으로 한다.

1. iPad app에서 PDF를 import한다.
2. PDFKit reader에서 PDF를 읽고 text를 선택한다.
3. 선택한 문장을 backend `highlights`로 저장한다.
4. 저장된 `highlight`를 기준으로 explanation, glossary extraction, question answering, quiz generation을 요청한다.
5. Backend는 selected text와 필요한 bounded context를 사용해 LLM provider를 호출하고, response를 검증한 뒤 SQLite에 저장한다.
6. iPad app은 generated result를 quick action detail sheet에서 보여준다.
7. Quiz study flow에서 사용자는 답안을 저장하고, 정답 확인 후 self-check를 남긴다.
8. `is_correct=false` `quiz_attempts`는 review-again listing/replay 대상이 된다.
9. Review-again 목록에서는 replay와 explicit delete/remove를 지원한다.
10. 저장된 문장, 용어 모음, 관련 detail sheets는 `study-records` API/DTO를 사용해 document-level saved results를 조회한다.

현재 iPad UX에 포함된 동작:

- Last opened document session restore
- Text selection 후 `QuickActionPanel` 기반 문장 저장, 설명, 용어, 퀴즈, 질문 action
- 좁은 폭에서 `QuickActionPanel` action row adaptation
- 문제 수 선택 후 사용자가 명시적으로 quiz generation을 실행하는 흐름
- Blank quiz answer를 `모름`으로 제출
- Review-again replay sheet는 replay 답안을 다시 저장하는 흐름으로 동작하며, 기존 review-again 항목을 중복 추가하는 action을 제공하지 않음
- Review-again listing/detail에서 explicit delete/remove

`study-records`는 backend/API capability이며 current iPad usage는 `저장된 문장`, `용어 모음`, saved sentence detail, replay/detail sheets 같은 saved result lookup flow를 통해 이루어진다. 별도의 `학습 기록` toolbar entry나 `DocumentStudyRecordSheet`를 current primary UI로 설명하지 않는다.

## 3. Architecture boundary

| Layer | Responsibility |
| --- | --- |
| iPad app | PDF import, local app document copy, PDFKit reading, selected text quick actions, quiz study/replay UI |
| FastAPI backend | PDF upload/storage, page text extraction, API validation, SQLite persistence, LLM provider 호출 |
| SQLite | `documents`, `document_pages`, `highlights`, generated results, `quiz_attempts`, `review_cards`, `llm_request_logs` 저장 |
| LLM provider | selected-text study actions에 대한 structured output 생성 |

Security/runtime boundary:

- iPad app은 backend API만 호출한다.
- iPad app에는 LLM API key, provider secret, provider account detail을 저장하지 않는다.
- Backend만 LLM provider를 호출한다.
- LLM provider secrets는 backend environment variables에만 둔다.
- Uploaded PDFs는 backend runtime artifacts이며 commit하지 않는다.
- Local SQLite DB, runtime logs, `.env`, `Local.xcconfig`, private PDF content는 public docs나 Git에 포함하지 않는다.

Selected-text boundary:

- LLM task input은 selected text와 필요한 context를 분리해 구성한다.
- 현재 backend는 same-page text에서 bounded context를 사용한다.
- 매 요청마다 full PDF text를 LLM provider로 보내는 architecture가 아니다.
- LLM output은 trusted data로 취급하지 않고 schema validation 후 저장한다.

## 4. Backend data and API shape

Core persistence tables:

| Table | Role |
| --- | --- |
| `documents` | uploaded PDF metadata, original filename, storage path, page count |
| `document_pages` | backend가 추출한 page별 text |
| `highlights` | iPad selected text와 page number |
| `llm_explanations` | highlight 기반 explanation summary/key points |
| `glossary_terms` | highlight 기반 term/definition/source text |
| `user_questions` | highlight 기반 question, answer, evidence text |
| `quizzes` | highlight 기반 generated quiz, `short_answer`, `fill_blank` |
| `quiz_attempts` | user answer, self-check result, optional feedback |
| `review_cards` | wrong quiz attempt에서 review card를 생성하는 backend/API capability |
| `llm_request_logs` | provider, model, token usage, latency, status, estimated cost, sanitized error |

Representative public API flow:

- `POST /api/v1/documents`: PDF upload, backend storage, page text extraction
- `POST /api/v1/highlights`: selected text 저장
- `POST /api/v1/highlights/{highlight_id}/explanations`: explanation 생성
- `POST /api/v1/highlights/{highlight_id}/glossary-terms`: glossary terms 생성
- `POST /api/v1/highlights/{highlight_id}/questions`: selected text 기반 question answering
- `POST /api/v1/highlights/{highlight_id}/quizzes`: quiz generation
- `POST /api/v1/quizzes/{quiz_id}/attempts`: quiz attempt 저장
- `GET /api/v1/quiz-attempts/review-again`: `is_correct=false` attempts 조회
- `DELETE /api/v1/quiz-attempts/{attempt_id}`: review-again/delete-remove flow에서 quiz attempt 제거
- `GET /api/v1/documents/{document_id}/study-records`: document-level saved result lookup

`review_cards`는 backend/API capability로 존재하지만 separate review card list/detail/edit/delete UX는 current primary MVP UX가 아니며 deferred다.

## 5. Runtime and config

Backend:

- FastAPI entrypoint는 `app.main:app`이다.
- 기본 local database는 SQLite URL인 `sqlite:///./info_drip.db` 방향을 사용한다.
- Uploaded PDF storage는 backend runtime directory를 사용한다.
- 기본 LLM provider는 local development에 적합한 `fake` provider다.
- Real provider를 쓰려면 backend environment에서 `INFODRIP_LLM_PROVIDER=openai-compatible`와 provider-specific variables를 설정한다.

iPad:

- `INFODRIP_BACKEND_BASE_URL`은 Info.plist build setting으로 주입된다.
- Simulator 기본값은 `http://127.0.0.1:8000`이다.
- Physical iPad testing에서는 `ios/InfoDrip/Config/Local.xcconfig.example`을 `Local.xcconfig`로 복사하고, iPad에서 접근 가능한 sanitized backend host를 설정한다.
- `Local.xcconfig`는 local-only file이며 commit하지 않는다.

Sanitized examples:

```text
INFODRIP_BACKEND_BASE_URL = http:/$()/<LAN_HOST>:8000
INFODRIP_LLM_PROVIDER=openai-compatible
INFODRIP_OPENAI_API_KEY=<redacted>
```

Actual LAN/Tailscale IP, `.env` values, `Local.xcconfig` values, provider account details, API keys, private PDF filenames/content는 public artifact에 포함하지 않는다.

## 6. Validation and current limits

Current validation:

- Backend CI는 `.github/workflows/backend-ci.yml`에서 `backend/scripts/check.sh`를 실행한다.
- Local backend check는 repo root에서 `backend/scripts/check.sh`를 사용한다.
- iPad 변경은 가능한 환경에서 Xcode build로 확인하고, 주요 user flow는 physical iPad manual QA로 확인한다.
- 현재 docs는 iOS CI, branch protection, production deployment readiness를 주장하지 않는다.

Current MVP out of scope:

- OCR
- RAG
- vector DB
- LLM streaming
- account system
- payment
- public deployment
- Android implementation
- page range quiz
- exam mode
- learning-goal-based quiz generation
- advanced/deep mode
- separate review card list/detail/edit/delete UX
