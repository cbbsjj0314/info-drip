# InfoDrip

InfoDrip은 개인용 local-first iPad PDF reading assistant다.

사용자는 iPad에서 PDF를 읽다가 궁금한 부분을 선택하고, 선택한 문장을 바탕으로 설명, 용어 정리, 질문/답변, 퀴즈, 다시 풀기까지 이어지는 흐름을 사용할 수 있다.

InfoDrip은 범용 PDF chatbot이 아니다.

전체 PDF를 대상으로 대화하는 흐름보다 selected text 기반 reading/study workflow와 그 결과 저장에 초점을 둔다.

## MVP workflow

현재 MVP 흐름은 다음을 중심으로 한다.

- PDF import와 PDFKit 기반 reading
- text selection과 saved sentence/highlight 저장
- selected text 기반 LLM explanation, glossary extraction, question answering
- quiz generation, quiz attempt tracking, review-again 목록 조회, replay, delete
- 저장된 문장, 문장별 상세 화면, 용어 모음을 통한 기존 결과 조회

현재 iPad UX는 마지막으로 열었던 문서 session 복원, 문제 수 선택 후 명시적인 quiz generation, 빈 답안의 `모름` 제출 등 주요 reading/study flow를 지원한다.

## Architecture 요약

| Layer | Role |
| --- | --- |
| iPad 앱 | SwiftUI/PDFKit 기반 PDF reading, selected text quick actions |
| FastAPI backend | PDF upload/storage, page text extraction, SQLite persistence, LLM provider 호출 |
| SQLite | `documents`, `highlights`, generated results, `quiz_attempts`, review-again records 저장 |
| LLM provider | OpenAI-compatible boundary 뒤에서 explanation, glossary, question, quiz 생성 |

iPad 앱, backend, LLM provider 사이의 책임 boundary는 명확하게 유지한다.

- iPad 앱은 backend API만 호출한다.
- LLM provider secrets는 iPad 앱에 넣지 않고 backend environment variables에만 둔다.
- study action에는 selected text와 필요한 context만 사용한다. 매 요청마다 PDF 전체 text를 LLM provider로 보내는 흐름이 아니다.
- Uploaded PDFs, local SQLite DB, runtime logs, `.env`, `Local.xcconfig`는 public artifact로 commit하지 않는다.

자세한 architecture, ERD, 주요 API sequence, 구현 상태는 [docs/architecture.md](docs/architecture.md)를 참고한다.

Backend API, 환경 변수, 실행 방법, local backend validation은 [backend/README.md](backend/README.md)를 참고한다.

## iPad backend URL 설정

iOS app은 `Info.plist`의 `INFODRIP_BACKEND_BASE_URL` 값을 backend base URL로 사용한다.

이 값은 Xcode target build configuration의 `.xcconfig`에서 주입된다.

- Simulator 기본값: `http://127.0.0.1:8000`
- 실제 iPad에서 backend를 호출하려면 `ios/InfoDrip/Config/Local.xcconfig.example`을 `ios/InfoDrip/Config/Local.xcconfig`로 복사한 뒤 `INFODRIP_BACKEND_BASE_URL` 값을 iPad에서 접근 가능한 backend base URL로 바꾼다.
- `Local.xcconfig`는 로컬 개발 전용 파일이므로 Git에 커밋하지 않는다.
- `.xcconfig`에서는 `//`가 comment로 해석되므로 URL 작성 시 `http://...` 대신 `http:/$()/...`형태로 적는다. Xcode build setting을 거치면 정상적인 `http://...` 형태로 변환된다.

Sanitized example:

```text
INFODRIP_BACKEND_BASE_URL = http:/$()/<BACKEND_HOST>:8000
```

실제 iPad에서 접근하려면 backend는 loopback 전용 주소가 아니라 LAN에서 접근 가능한 host로 실행되어야 한다.

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

이 값은 backend URL만 담는다.

LLM API key와 provider secret은 iPad 앱에 넣지 않고 backend environment variables에만 둔다.

## Validation

Backend CI는 GitHub Actions에서 `backend/scripts/check.sh`를 실행한다.

이 script는 backend dependency sync 후 `ruff`와 `pytest` 기반 check를 실행하는 backend validation entrypoint다.

Local backend validation은 필요시 repo root에서 실행한다.

```bash
backend/scripts/check.sh
```

iPad 변경은 Xcode build가 가능한 환경에서 build validation을 수행하고, 주요 user flow는 physical iPad manual QA로 확인한다. 현재 public docs는 iOS CI 존재를 전제로 쓰지 않는다.

## MVP out of scope

현재 MVP 범위에 포함하지 않는다.

- OCR
- RAG
- vector DB
- LLM streaming
- Android implementation
- page range quiz
- exam mode
- learning-goal-based quiz generation
- advanced/deep mode
- 별도 review card list/detail/edit/delete UX
