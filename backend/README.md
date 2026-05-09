# InfoDrip Backend

InfoDrip MVP backend bootstrap.

현재 상태:

- FastAPI application entrypoint: `app.main:app`
- Health check: `GET /health`
- Database, PDF upload, LLM provider는 아직 구현하지 않음

## 실행

```bash
uv run uvicorn app.main:app --reload
```

## 검증

```bash
uv run ruff check .
uv run pytest
```
