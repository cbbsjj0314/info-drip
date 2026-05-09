from contextlib import suppress

from sqlalchemy import text

from app import database


def test_default_database_url_is_local_sqlite(monkeypatch) -> None:
    monkeypatch.delenv(database.DATABASE_URL_ENV_VAR, raising=False)

    assert database.DEFAULT_DATABASE_URL == "sqlite:///./info_drip.db"
    assert database.get_database_url() == database.DEFAULT_DATABASE_URL


def test_database_url_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv(database.DATABASE_URL_ENV_VAR, "sqlite:///:memory:")

    assert database.get_database_url() == "sqlite:///:memory:"


def test_db_session_provider_yields_working_session() -> None:
    session_provider = database.get_db_session()
    session = next(session_provider)

    try:
        assert session.execute(text("select 1")).scalar_one() == 1
    finally:
        with suppress(StopIteration):
            next(session_provider)
