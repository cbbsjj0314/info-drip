# InfoDrip

InfoDrip은 개인용 local-first iPad PDF reading assistant입니다.
iPad에서 PDF를 읽다가 궁금한 부분을 선택하고, 선택한 문장을 중심으로 설명,
용어 정리, 질문/답변, 퀴즈, 다시 풀기를 이어 가는 MVP입니다.

InfoDrip은 generic PDF chatbot이 아닙니다.
전체 PDF를 대상으로 대화하는 흐름보다 selected text 기반 reading/study workflow와
그 결과 저장에 초점을 둡니다.

## MVP workflow

현재 MVP 흐름은 다음을 중심으로 한다.

- PDF import와 PDFKit 기반 reading
- text selection과 saved sentence/highlight persistence
- selected text 기반 LLM explanation, glossary extraction, question answering
- quiz generation, quiz attempt tracking, review-again listing/replay/delete
- 저장된 문장, 용어 모음, 관련 detail sheets를 통한 saved result lookup

iPad UX는 최근 merged work 기준으로 last opened document session restore,
문제 수 선택 후 explicit quiz generation, blank quiz answer를 `모름`으로 제출하는 동작,
replay sheet에서 이미 review-again인 항목을 다시 추가하지 않는 동작을 포함한다.

## Architecture summary

| Layer | Role |
| --- | --- |
| iPad app | SwiftUI/PDFKit 기반 PDF reading, selected text quick actions |
| FastAPI backend | PDF upload/storage, page text extraction, SQLite persistence, LLM provider 호출 |
| SQLite | documents, highlights, generated results, quiz attempts, review-again records 저장 |
| LLM provider | OpenAI-compatible boundary 뒤에서 explanation/glossary/question/quiz 생성 |

Boundary는 명확하게 분리한다.

- iPad app은 backend API만 호출한다.
- LLM provider secrets는 iPad app에 넣지 않고 backend environment variables에만 둔다.
- selected text와 필요한 context를 study action에 사용한다.
  매 요청마다 full PDF text를 LLM provider로 보내는 흐름이 아니다.
- Uploaded PDFs, local SQLite DB, runtime logs, `.env`, `Local.xcconfig`는
  public artifact로 commit하지 않는다.

자세한 구조와 현재 MVP boundary는 [docs/architecture.md](docs/architecture.md)를 본다.
Backend API와 local backend 설정은 [backend/README.md](backend/README.md)를 본다.

## iPad backend URL 설정

iOS app은 Info.plist의 `INFODRIP_BACKEND_BASE_URL` 값을 backend base URL로 사용한다.

이 값은 Xcode target build configuration의 `.xcconfig`에서 주입된다.

- Simulator 기본값: `http://127.0.0.1:8000`
- 실제 iPad에서 backend를 호출할 때는
  `ios/InfoDrip/Config/Local.xcconfig.example`을
  `ios/InfoDrip/Config/Local.xcconfig`로 복사한 뒤
  `INFODRIP_BACKEND_BASE_URL` 값을 iPad에서 접근 가능한 backend base URL로 바꾼다.
- `Local.xcconfig`는 개인 개발 환경 파일이므로 Git에 커밋하지 않는다.
- `.xcconfig`에서는 `//`가 comment로 해석되므로 URL은 `http://...` 대신
  `http:/$()/...`로 적는다. Build setting으로 확장된 값은 `http://...`가 된다.

Sanitized example:

```text
INFODRIP_BACKEND_BASE_URL = http:/$()/<LAN_HOST>:8000
```

실제 iPad에서 접근하려면 backend는 loopback 전용 주소가 아니라
LAN에서 접근 가능한 host로 실행되어야 한다.

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

이 값은 backend URL만 담는다.
LLM API key와 provider secret은 iPad app에 넣지 않고
backend environment variables에만 둔다.

## Validation

Backend CI는 GitHub Actions에서 `backend/scripts/check.sh`를 실행한다.
이 script는 backend dependency sync 후 ruff와 pytest 기반 check를 실행하는
backend validation entrypoint다.

Local backend validation은 필요할 때 repo root에서 실행한다.

```bash
backend/scripts/check.sh
```

iPad 변경은 Xcode build가 가능한 환경에서 build validation을 수행하고,
주요 user flow는 physical iPad manual QA로 확인한다.
현재 public docs는 iOS CI가 있다고 주장하지 않는다.

## MVP out of scope

현재 MVP 범위에 포함하지 않는다.

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
