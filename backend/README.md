# InfoDrip Backend

InfoDrip MVP backend bootstrap.

현재 상태:

- FastAPI application entrypoint: `app.main:app`
- Health check: `GET /health`
- SQLite database engine/session skeleton
- SQLAlchemy 2.x `DeclarativeBase`
- Database URL override: `INFODRIP_DATABASE_URL`
- PDF upload, LLM provider는 아직 구현하지 않음

## 환경 변수

```bash
INFODRIP_DATABASE_URL=sqlite:///./info_drip.db
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
