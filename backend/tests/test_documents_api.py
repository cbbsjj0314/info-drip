from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.main import UPLOAD_DIR_ENV_VAR, app, extract_pdf_page_texts


TEXT_PDF_BYTES = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 44 >> stream
BT /F1 12 Tf 72 72 Td (Hello InfoDrip) Tj ET
endstream endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000311 00000 n 
trailer << /Root 1 0 R /Size 6 >>
startxref
405
%%EOF
"""


def create_test_pdf(path: Path, page_count: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)

    with path.open("wb") as output:
        writer.write(output)

    return path.read_bytes()


def test_extract_pdf_page_texts_reads_text_and_preserves_blank_pages(tmp_path) -> None:
    text_pdf = tmp_path / "text.pdf"
    text_pdf.write_bytes(TEXT_PDF_BYTES)

    assert extract_pdf_page_texts(text_pdf) == ["Hello InfoDrip"]

    blank_pdf = tmp_path / "blank.pdf"
    create_test_pdf(blank_pdf, page_count=1)

    assert extract_pdf_page_texts(blank_pdf) == [""]


def test_upload_document_stores_pdf_and_creates_document_pages(
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
        monkeypatch.setattr(
            "app.main.extract_pdf_page_texts",
            lambda _: ["First page text.", ""],
        )
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
            pages = session.scalars(
                select(database.DocumentPage).order_by(database.DocumentPage.page_number)
            ).all()
            assert len(pages) == 2
            assert [page.document_id for page in pages] == [document.id, document.id]
            assert [page.page_number for page in pages] == [1, 2]
            assert [page.text for page in pages] == ["First page text.", ""]
    finally:
        app.dependency_overrides.clear()


def test_upload_document_deletes_file_when_text_extraction_fails(
    monkeypatch,
    tmp_path,
) -> None:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv(UPLOAD_DIR_ENV_VAR, str(upload_dir))

    def fail_extraction(_: Path) -> list[str]:
        raise RuntimeError("extraction failed")

    monkeypatch.setattr("app.main.extract_pdf_page_texts", fail_extraction)

    client = TestClient(app)
    pdf_bytes = create_test_pdf(tmp_path / "sample.pdf", page_count=1)

    with pytest.raises(RuntimeError, match="extraction failed"):
        client.post(
            "/api/v1/documents",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        )

    assert list(upload_dir.glob("*.pdf")) == []


def test_upload_document_rolls_back_and_deletes_file_when_db_commit_fails(
    monkeypatch,
    tmp_path,
) -> None:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv(UPLOAD_DIR_ENV_VAR, str(upload_dir))
    monkeypatch.setattr("app.main.extract_pdf_page_texts", lambda _: ["Stored text."])

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    rollback_called = False

    class FailingCommitSession(Session):
        def commit(self) -> None:
            raise RuntimeError("commit failed")

        def rollback(self) -> None:
            nonlocal rollback_called
            rollback_called = True
            super().rollback()

    failing_session = sessionmaker(
        bind=engine,
        class_=FailingCommitSession,
        autoflush=False,
        autocommit=False,
    )

    def override_db_session() -> Session:
        with failing_session() as session:
            yield session

    app.dependency_overrides[database.get_db_session] = override_db_session

    try:
        client = TestClient(app)
        pdf_bytes = create_test_pdf(tmp_path / "sample.pdf", page_count=1)

        with pytest.raises(RuntimeError, match="commit failed"):
            client.post(
                "/api/v1/documents",
                files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            )

        assert rollback_called is True
        assert list(upload_dir.glob("*.pdf")) == []

        with test_session() as session:
            assert session.scalars(select(database.Document)).all() == []
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
