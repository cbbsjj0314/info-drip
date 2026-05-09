import os
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.database import Base, Document, DocumentPage, engine, get_db_session

UPLOAD_DIR_ENV_VAR = "INFODRIP_UPLOAD_DIR"
DEFAULT_UPLOAD_DIR = "uploads/documents"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="InfoDrip Backend", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_filename: str
    storage_path: str
    page_count: int
    created_at: datetime


def get_upload_dir() -> Path:
    return Path(os.getenv(UPLOAD_DIR_ENV_VAR, DEFAULT_UPLOAD_DIR))


def get_relative_storage_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def extract_pdf_page_texts(path: Path) -> list[str]:
    try:
        reader = PdfReader(path)
        return [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a readable PDF.",
        ) from exc


@app.post(
    "/api/v1/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> Document:
    original_filename = Path(file.filename or "").name
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF uploads are supported.",
        )

    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{uuid4().hex}.pdf"

    try:
        with destination.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        page_texts = extract_pdf_page_texts(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()

    document = Document(
        title=Path(original_filename).stem,
        original_filename=original_filename,
        storage_path=get_relative_storage_path(destination),
        page_count=len(page_texts),
        pages=[
            DocumentPage(page_number=index, text=text)
            for index, text in enumerate(page_texts, start=1)
        ],
    )
    try:
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    db.refresh(document)

    return document
