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
- Highlight explanation quick action: `POST /api/v1/highlights/{highlight_id}/explanations`
- LLM explanation persistence와 request logging

## 환경 변수

```bash
INFODRIP_DATABASE_URL=sqlite:///./info_drip.db
INFODRIP_UPLOAD_DIR=uploads/documents
```

## 실행

```bash
uv run uvicorn app.main:app --reload
```

## 검증

```bash
uv run ruff check .
uv run pytest
```
