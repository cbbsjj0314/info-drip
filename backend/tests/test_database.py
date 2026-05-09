from contextlib import suppress

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

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


def test_document_tables_can_be_created_from_metadata() -> None:
    engine = create_engine("sqlite:///:memory:")

    database.Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "documents",
        "document_pages",
        "highlights",
    }

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    assert document_columns == {
        "id",
        "title",
        "original_filename",
        "storage_path",
        "page_count",
        "created_at",
    }

    page_columns = {column["name"] for column in inspector.get_columns("document_pages")}
    assert page_columns == {
        "id",
        "document_id",
        "page_number",
        "text",
        "created_at",
    }

    page_foreign_keys = inspector.get_foreign_keys("document_pages")
    assert page_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        }
    ]

    highlight_columns = {column["name"] for column in inspector.get_columns("highlights")}
    assert highlight_columns == {
        "id",
        "document_id",
        "page_number",
        "selected_text",
        "created_at",
    }

    highlight_foreign_keys = inspector.get_foreign_keys("highlights")
    assert highlight_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        }
    ]


def test_document_page_relationship_persists_pages() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
        document = database.Document(
            title="Sample",
            original_filename="sample.pdf",
            storage_path="documents/sample.pdf",
            page_count=1,
            pages=[
                database.DocumentPage(
                    page_number=1,
                    text="Sanitized sample page text.",
                )
            ],
        )

        session.add(document)
        session.commit()
        session.refresh(document)

        assert document.id is not None
        assert len(document.pages) == 1
        assert document.pages[0].document_id == document.id
        assert document.pages[0].document is document


def test_document_highlight_relationship_persists_highlights() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
        document = database.Document(
            title="Sample",
            original_filename="sample.pdf",
            storage_path="documents/sample.pdf",
            page_count=1,
            pages=[
                database.DocumentPage(
                    page_number=1,
                    text="Sanitized sample page text.",
                )
            ],
            highlights=[
                database.Highlight(
                    page_number=1,
                    selected_text="Sanitized selected text.",
                )
            ],
        )

        session.add(document)
        session.commit()
        session.refresh(document)

        assert document.id is not None
        assert len(document.highlights) == 1
        assert document.highlights[0].document_id == document.id
        assert document.highlights[0].document is document
