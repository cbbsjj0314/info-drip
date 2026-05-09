# InfoDrip Backend

InfoDrip MVP backend bootstrap.

현재 상태:

- FastAPI application entrypoint: `app.main:app`
- Health check: `GET /health`
- SQLite database engine/session skeleton
- SQLAlchemy 2.x `DeclarativeBase`
- Database URL override: `INFODRIP_DATABASE_URL`
- PDF upload: `POST /api/v1/documents`
- PDF page count extraction
- Local upload directory override: `INFODRIP_UPLOAD_DIR`
- Explanation용 `LLMProvider` interface와 deterministic fake provider
- OpenAI-compatible explanation provider
- Highlight explanation quick action: `POST /api/v1/highlights/{highlight_id}/explanations`
- LLM explanation persistence와 request logging

## 환경 변수

```bash
INFODRIP_DATABASE_URL=sqlite:///./info_drip.db
INFODRIP_UPLOAD_DIR=uploads/documents
INFODRIP_LLM_PROVIDER=fake
INFODRIP_OPENAI_API_KEY=
INFODRIP_OPENAI_BASE_URL=
INFODRIP_OPENAI_MODEL=
```

LLM provider 기본값은 `fake`다.

OpenAI-compatible provider를 사용하려면 backend 환경 변수에 다음 값을 설정한다.

- `INFODRIP_LLM_PROVIDER=openai-compatible`
- `INFODRIP_OPENAI_API_KEY`
- `INFODRIP_OPENAI_MODEL`

`INFODRIP_OPENAI_BASE_URL`은 OpenAI-compatible endpoint를 따로 사용할 때만 설정한다.

API key는 backend 환경 변수에서만 읽으며 client API contract에는 포함하지 않는다.

## 실행

```bash
uv run uvicorn app.main:app --reload
```

## 검증

```bash
uv run ruff check .
uv run pytest
```
