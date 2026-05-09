from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.main import UPLOAD_DIR_ENV_VAR, app


def create_test_pdf(path: Path, page_count: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)

    with path.open("wb") as output:
        writer.write(output)

    return path.read_bytes()


def test_upload_document_stores_pdf_and_creates_document_row(
    monkeypatch,
    tmp_path,
) -> None:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv(UPLOAD_DIR_ENV_VAR, str(upload_dir))

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db_session() -> Session:
        with test_session() as session:
            yield session

    app.dependency_overrides[database.get_db_session] = override_db_session

    try:
        client = TestClient(app)
        pdf_bytes = create_test_pdf(tmp_path / "sample.pdf", page_count=2)

        response = client.post(
            "/api/v1/documents",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["title"] == "sample"
        assert payload["original_filename"] == "sample.pdf"
        assert payload["page_count"] == 2
        assert payload["storage_path"].endswith(".pdf")
        assert "created_at" in payload

        stored_path = Path(payload["storage_path"])
        assert stored_path.exists()
        assert stored_path.parent == upload_dir

        with test_session() as session:
            document = session.scalars(select(database.Document)).one()
            assert document.id == payload["id"]
            assert document.storage_path == payload["storage_path"]
            assert document.page_count == 2
            assert document.pages == []
            assert session.scalars(select(database.DocumentPage)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_upload_document_rejects_non_pdf(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(UPLOAD_DIR_ENV_VAR, str(tmp_path / "uploads"))

    client = TestClient(app)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only PDF uploads are supported."}
    assert not (tmp_path / "uploads").exists()
