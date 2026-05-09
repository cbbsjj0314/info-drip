import json
import os
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import (
    Base,
    Document,
    DocumentPage,
    Highlight,
    LLMExplanation,
    LLMRequestLog,
    engine,
    get_db_session,
)
from app.llm import ExplanationRequest, FakeLLMProvider, LLMProvider

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


class HighlightCreateRequest(BaseModel):
    document_id: int
    page_number: int = Field(ge=1)
    selected_text: str = Field(min_length=1)


class HighlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    page_number: int
    selected_text: str
    created_at: datetime


class LLMExplanationResponse(BaseModel):
    id: int
    highlight_id: int
    summary: str
    key_points: list[str]
    provider: str
    model: str
    created_at: datetime


def get_upload_dir() -> Path:
    return Path(os.getenv(UPLOAD_DIR_ENV_VAR, DEFAULT_UPLOAD_DIR))


def get_llm_provider() -> LLMProvider:
    return FakeLLMProvider()


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


def now_latency_ms(start_time: float) -> int:
    return max(0, round((perf_counter() - start_time) * 1000))


def serialize_key_points(key_points: list[str]) -> str:
    return json.dumps(key_points, ensure_ascii=True)


def explanation_to_response(explanation: LLMExplanation) -> LLMExplanationResponse:
    return LLMExplanationResponse(
        id=explanation.id,
        highlight_id=explanation.highlight_id,
        summary=explanation.summary,
        key_points=list(json.loads(explanation.key_points)),
        provider=explanation.provider,
        model=explanation.model,
        created_at=explanation.created_at,
    )


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


@app.post(
    "/api/v1/highlights",
    response_model=HighlightResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_highlight(
    request: HighlightCreateRequest,
    db: Session = Depends(get_db_session),
) -> Highlight:
    document = db.get(Document, request.document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    page_exists = db.scalar(
        select(DocumentPage.id).where(
            DocumentPage.document_id == request.document_id,
            DocumentPage.page_number == request.page_number,
        )
    )
    if page_exists is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document page not found.",
        )

    highlight = Highlight(
        document_id=request.document_id,
        page_number=request.page_number,
        selected_text=request.selected_text,
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)

    return highlight


@app.get(
    "/api/v1/documents/{document_id}/highlights",
    response_model=list[HighlightResponse],
)
def list_document_highlights(
    document_id: int,
    db: Session = Depends(get_db_session),
) -> list[Highlight]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return list(
        db.scalars(
            select(Highlight)
            .where(Highlight.document_id == document_id)
            .order_by(Highlight.page_number, Highlight.id)
        )
    )


@app.post(
    "/api/v1/highlights/{highlight_id}/explanations",
    response_model=LLMExplanationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_highlight_explanation(
    highlight_id: int,
    db: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> LLMExplanationResponse:
    highlight = db.get(Highlight, highlight_id)
    if highlight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found.",
        )

    provider_name = getattr(provider, "provider", "unknown")
    model_name = getattr(provider, "model", "unknown")
    start_time = perf_counter()

    try:
        llm_response = provider.generate_explanation(
            ExplanationRequest(selected_text=highlight.selected_text)
        )
    except Exception as exc:
        db.add(
            LLMRequestLog(
                provider=provider_name,
                model=model_name,
                task_type="explanation",
                status="error",
                latency_ms=now_latency_ms(start_time),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                estimated_cost=None,
                document_id=highlight.document_id,
                highlight_id=highlight.id,
                error_message=str(exc),
            )
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Explanation generation failed.",
        ) from exc

    explanation = LLMExplanation(
        document_id=highlight.document_id,
        highlight_id=highlight.id,
        summary=llm_response.content.summary,
        key_points=serialize_key_points(llm_response.content.key_points),
        provider=llm_response.usage.provider,
        model=llm_response.usage.model,
    )
    db.add(explanation)
    db.add(
        LLMRequestLog(
            provider=llm_response.usage.provider,
            model=llm_response.usage.model,
            task_type="explanation",
            status="success",
            latency_ms=now_latency_ms(start_time),
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
            total_tokens=llm_response.usage.total_tokens,
            estimated_cost=llm_response.usage.estimated_cost,
            document_id=highlight.document_id,
            highlight_id=highlight.id,
            error_message=None,
        )
    )
    db.commit()
    db.refresh(explanation)

    return explanation_to_response(explanation)
