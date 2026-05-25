# InfoDrip Backend

InfoDrip MVP 백엔드는 개인용 local-first iPad PDF 학습 흐름을 위한 FastAPI + SQLite 서비스다.

백엔드는 다음을 담당한다.
- PDF 업로드
- page text 추출
- selected-text highlight 저장
- LLM 기반 explanation/glossary/question/quiz 생성
- quiz attempt 저장
- review-again 조회 및 quiz attempt 제거
- document 단위 study record 조회

iPad/client는 backend API만 호출한다.

LLM API key는 client에 두지 않고 backend 환경 변수에만 둔다.

## 현재 구현 상태

- FastAPI entrypoint: `app.main:app`
- 상태 확인: `GET /health`
- SQLite database/session 구성
- PDF 업로드와 backend local file 저장
- 업로드한 PDF의 page text 추출
- selected-text highlight 저장
- `LLMProvider` interface
- 결정적 응답을 반환하는 `fake` provider
- `openai-compatible` provider
- LLM JSON response 저장 전 검증
- local DB table `llm_request_logs`에 LLM request log 저장
- primary review flow: `quiz_attempts` 기반 review-again listing/replay/delete-remove

`review_cards`는 backend/API 기능으로 존재하지만, 별도 review card UX는 보류되어 있다.

MVP의 primary review UX는 `quiz_attempts`와 review-again flow 중심이다.

## API

### 상태 확인

- `GET /health`

### 문서

- `POST /api/v1/documents`
  - PDF 파일 업로드
  - page count와 page text 추출
  - backend upload directory에 PDF 저장
- `GET /api/v1/documents/{document_id}/study-records`
  - document, highlights, explanations, glossary_terms, user_questions, quizzes, quiz_attempts를 document 단위로 조회
  - `llm_request_logs`는 public API response에 포함하지 않는다.

### 하이라이트

- `POST /api/v1/highlights`
  - `document_id`, `page_number`, `selected_text`로 highlight 생성
- `GET /api/v1/documents/{document_id}/highlights`
  - document의 highlights 조회

### Selected-Text LLM Workflow

- `POST /api/v1/highlights/{highlight_id}/explanations`
  - selected text 기반 explanation 생성
- `POST /api/v1/highlights/{highlight_id}/glossary-terms`
  - selected text 기반 glossary terms 생성
- `POST /api/v1/highlights/{highlight_id}/questions`
  - selected text에 대한 question answer 생성
- `POST /api/v1/highlights/{highlight_id}/quizzes`
  - selected text 기반 quiz 생성
  - 지원하는 quiz types: `short_answer`, `fill_blank`

LLM request는 highlight의 `selected_text`와 필요한 same-page surrounding context를 사용한다.

매 요청마다 full PDF text를 LLM provider로 보내는 flow가 아니다.

### Quiz Attempts And Review-Again

- `POST /api/v1/quizzes/{quiz_id}/attempts`
  - quiz attempt 저장
  - `is_correct=false` attempt는 review-again 대상이 된다.
- `GET /api/v1/quiz-attempts/review-again`
  - review-again 대상 quiz attempts 조회
  - optional query: `document_id`
- `DELETE /api/v1/quiz-attempts/{attempt_id}`
  - review-again 목록/detail에서 quiz attempt 제거
  - 연결된 `review_cards`가 있으면 제거하지 않는다.

보조 조회 endpoint:

- `GET /api/v1/quizzes/{quiz_id}/attempts`
  - 특정 quiz의 attempt history 조회
  - 핵심 selected-text smoke flow에는 포함하지 않는다.

### Optional/Deferred Review Card Capability

- `POST /api/v1/quiz-attempts/{attempt_id}/review-cards`
  - wrong quiz attempt에서 review card 생성
- `GET /api/v1/review-cards`
  - 생성된 review cards 조회
  - optional query: `document_id`

이 기능은 backend/API 확인용이다.

별도 review card list/detail/edit/delete UX는 MVP primary flow가 아니다.

## 환경 변수

예시:

```bash
INFODRIP_DATABASE_URL=sqlite:///./info_drip.db
INFODRIP_UPLOAD_DIR=uploads/documents
INFODRIP_LLM_PROVIDER=fake
INFODRIP_OPENAI_API_KEY=
INFODRIP_OPENAI_BASE_URL=
INFODRIP_OPENAI_MODEL=
INFODRIP_OPENAI_RESPONSE_FORMAT=json_schema
```

- `INFODRIP_DATABASE_URL`
  - SQLite database URL
  - local 기본 예시: `sqlite:///./info_drip.db`
- `INFODRIP_UPLOAD_DIR`
  - 업로드한 PDF storage directory
  - 기본값: `uploads/documents`
- `INFODRIP_LLM_PROVIDER`
  - 기본값: `fake`
  - 지원 값: `fake`, `openai-compatible`
- `INFODRIP_OPENAI_API_KEY`
  - `INFODRIP_LLM_PROVIDER=openai-compatible`일 때만 필요
  - backend 환경 변수에만 저장
- `INFODRIP_OPENAI_BASE_URL`
  - custom OpenAI-compatible endpoint base URL
  - 별도 endpoint를 쓰지 않으면 비워 둔다.
- `INFODRIP_OPENAI_MODEL`
  - `INFODRIP_LLM_PROVIDER=openai-compatible`일 때만 필요
- `INFODRIP_OPENAI_RESPONSE_FORMAT`
  - 기본값: `json_schema`
  - 지원 값: `json_schema`, `json_object`
  - strict JSON schema를 지원하지 않고 JSON object mode를 요구하는 OpenAI-compatible provider에서는 `json_object`를 사용할 수 있다.
  - `json_object` mode에서도 backend는 LLM output을 저장하기 전에 Pydantic schema로 검증한다.

API key, provider account detail, token, private runtime value는 iPad app, 공개 문서, fixture, screenshot, API payload example에 저장하지 않는다.

## 실행

`backend/`에서 실행한다.

```bash
uv run uvicorn app.main:app --reload
```

기본 local provider는 `fake`다.

외부 LLM API를 호출하지 않고, backend가 정해진 가짜 응답을 반환하므로 API key 없이 backend 흐름을 확인할 수 있다.

## 검증

`backend/`에서 실행한다.

```bash
uv run ruff check .
uv run pytest
```

Docs-only 변경에서는 runtime validation을 생략할 수 있다.

이 경우 README를 다시 읽고 오래된 설명, 중복 안내, 과도한 범위 약속, secret/private data 노출이 없는지 확인한다.

## Local LLM Smoke Checklist

실제 LLM provider로 selected-text workflow를 local에서 확인할 때 사용하는 checklist다.

실제 API key 값, provider account detail, private PDF 원문, 긴 원문 발췌는 command, 문서, screenshot, report에 남기지 않는다.

1. Sanitized PDF fixture 또는 개인 테스트 PDF를 준비한다.
2. Backend 환경에 실제 provider 값을 설정한다.

   ```bash
   INFODRIP_LLM_PROVIDER=openai-compatible
   INFODRIP_OPENAI_API_KEY=<set in local env only>
   INFODRIP_OPENAI_MODEL=<model name>
   INFODRIP_OPENAI_BASE_URL=<optional custom base URL>
   INFODRIP_OPENAI_RESPONSE_FORMAT=json_schema
   ```

3. Backend를 실행한다.

   ```bash
   uv run uvicorn app.main:app --reload
   ```

4. iPad app 또는 HTTP client로 PDF를 업로드한다.
   - `POST /api/v1/documents`
5. 업로드한 document의 page에서 selected text highlight를 생성한다.
   - `POST /api/v1/highlights`
6. Highlight 기반 explanation을 생성한다.
   - `POST /api/v1/highlights/{highlight_id}/explanations`
7. Highlight 기반 glossary terms를 생성한다.
   - `POST /api/v1/highlights/{highlight_id}/glossary-terms`
8. Highlight 기반 question answer를 생성한다.
   - `POST /api/v1/highlights/{highlight_id}/questions`
9. Highlight 기반 quiz를 생성한다.
   - `POST /api/v1/highlights/{highlight_id}/quizzes`
10. Quiz attempt를 저장한다.
    - `POST /api/v1/quizzes/{quiz_id}/attempts`
    - review-again 확인을 위해 `is_correct=false` attempt를 하나 포함한다.
11. Review-again 대상 attempt를 조회한다.
    - `GET /api/v1/quiz-attempts/review-again`
12. Document-level study records를 조회한다.
    - `GET /api/v1/documents/{document_id}/study-records`
13. Local DB에서 `llm_request_logs`를 확인한다.
    - 이 table은 public API endpoint가 아니다.
    - 확인 항목: `provider`, `model`, token fields, `latency_ms`, `status`, `estimated_cost`
14. Provider 실패 상황에서는 public API response가 sanitized error만 노출하는지 확인한다.
    - API key, provider account detail, raw provider error, private PDF content가 response에 노출되면 안 된다.

Optional/deferred capability 확인:

- Wrong quiz attempt에서 review card 생성
  - `POST /api/v1/quiz-attempts/{attempt_id}/review-cards`
- Review cards 조회
  - `GET /api/v1/review-cards`
