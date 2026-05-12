import json
import os
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import (
    Base,
    Document,
    DocumentPage,
    GlossaryTerm,
    Highlight,
    LLMExplanation,
    LLMRequestLog,
    Quiz,
    QuizAttempt,
    ReviewCard,
    engine,
    get_db_session,
)
from app.llm import (
    ALLOWED_QUIZ_TYPES,
    DEFAULT_QUIZZES_PER_REQUEST,
    ExplanationRequest,
    GlossaryExtractionRequest,
    LLMProvider,
    MAX_QUIZZES_PER_REQUEST,
    QuizGenerationRequest,
    ReviewCardGenerationRequest,
    build_llm_provider_from_env,
)

UPLOAD_DIR_ENV_VAR = "INFODRIP_UPLOAD_DIR"
DEFAULT_UPLOAD_DIR = "uploads/documents"
PROVIDER_REQUEST_FAILED_MESSAGE = "Provider request failed."
PAGE_CONTEXT_MAX_CHARS = 4000


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


class GlossaryTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    highlight_id: int
    term: str
    definition: str
    source_text: str | None
    provider: str
    model: str
    created_at: datetime


class QuizGenerationOptions(BaseModel):
    quiz_types: list[str] = Field(default_factory=lambda: list(ALLOWED_QUIZ_TYPES))
    max_quizzes: int = Field(
        default=DEFAULT_QUIZZES_PER_REQUEST,
        ge=1,
        le=MAX_QUIZZES_PER_REQUEST,
    )

    @field_validator("quiz_types")
    @classmethod
    def quiz_types_must_be_allowed_and_deduplicated(
        cls,
        value: list[str],
    ) -> list[str]:
        if not value:
            raise ValueError("quiz_types must not be empty")

        deduplicated: list[str] = []
        for quiz_type in value:
            normalized = quiz_type.strip()
            if normalized not in ALLOWED_QUIZ_TYPES:
                raise ValueError("unsupported quiz_type")
            if normalized not in deduplicated:
                deduplicated.append(normalized)

        return deduplicated


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    highlight_id: int
    quiz_type: str
    question: str
    answer: str
    explanation: str
    source_text: str
    provider: str
    model: str
    created_at: datetime


class QuizAttemptCreateRequest(BaseModel):
    user_answer: str = Field(min_length=1)
    is_correct: bool | None = None
    feedback: str | None = None

    @field_validator("user_answer")
    @classmethod
    def user_answer_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("user_answer must not be blank")

        return normalized

    @field_validator("feedback")
    @classmethod
    def blank_feedback_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    user_answer: str
    is_correct: bool | None
    feedback: str | None
    created_at: datetime


class ReviewAgainQuizAttemptResponse(BaseModel):
    attempt_id: int
    quiz_id: int
    document_id: int
    highlight_id: int
    user_answer: str
    is_correct: bool | None
    feedback: str | None
    attempted_at: datetime
    quiz_type: str
    question: str
    answer: str
    explanation: str
    source_text: str
    document_title: str
    page_number: int


class ReviewCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    quiz_id: int
    quiz_attempt_id: int
    front: str
    back: str
    source_text: str | None
    provider: str
    model: str
    created_at: datetime


def get_upload_dir() -> Path:
    return Path(os.getenv(UPLOAD_DIR_ENV_VAR, DEFAULT_UPLOAD_DIR))


def get_llm_provider() -> LLMProvider:
    return build_llm_provider_from_env()


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


def sanitize_provider_error_message(_: Exception) -> str:
    return PROVIDER_REQUEST_FAILED_MESSAGE


def bounded_page_context(page_text: str | None) -> str | None:
    if page_text is None:
        return None

    stripped = page_text.strip()
    if not stripped:
        return None

    return stripped[:PAGE_CONTEXT_MAX_CHARS]


def build_explanation_request(db: Session, highlight: Highlight) -> ExplanationRequest:
    document = db.get(Document, highlight.document_id)
    page_text = db.scalar(
        select(DocumentPage.text).where(
            DocumentPage.document_id == highlight.document_id,
            DocumentPage.page_number == highlight.page_number,
        )
    )

    return ExplanationRequest(
        selected_text=highlight.selected_text,
        surrounding_context=bounded_page_context(page_text),
        document_title=document.title if document is not None else None,
    )


def build_glossary_request(db: Session, highlight: Highlight) -> GlossaryExtractionRequest:
    document = db.get(Document, highlight.document_id)
    page_text = db.scalar(
        select(DocumentPage.text).where(
            DocumentPage.document_id == highlight.document_id,
            DocumentPage.page_number == highlight.page_number,
        )
    )

    return GlossaryExtractionRequest(
        selected_text=highlight.selected_text,
        surrounding_context=bounded_page_context(page_text),
        document_title=document.title if document is not None else None,
    )


def build_quiz_request(
    db: Session,
    highlight: Highlight,
    options: QuizGenerationOptions,
) -> QuizGenerationRequest:
    document = db.get(Document, highlight.document_id)
    page_text = db.scalar(
        select(DocumentPage.text).where(
            DocumentPage.document_id == highlight.document_id,
            DocumentPage.page_number == highlight.page_number,
        )
    )

    return QuizGenerationRequest(
        selected_text=highlight.selected_text,
        surrounding_context=bounded_page_context(page_text),
        document_title=document.title if document is not None else None,
        quiz_types=options.quiz_types,
        max_quizzes=options.max_quizzes,
    )


def build_review_card_request(
    attempt: QuizAttempt,
    quiz: Quiz,
    highlight: Highlight,
    document: Document,
) -> ReviewCardGenerationRequest:
    return ReviewCardGenerationRequest(
        document_title=document.title,
        page_number=highlight.page_number,
        quiz_type=quiz.quiz_type,
        question=quiz.question,
        correct_answer=quiz.answer,
        user_answer=attempt.user_answer,
        quiz_explanation=quiz.explanation,
        quiz_source_text=quiz.source_text,
    )


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


def review_again_attempt_to_response(
    attempt: QuizAttempt,
    quiz: Quiz,
    highlight: Highlight,
    document: Document,
) -> ReviewAgainQuizAttemptResponse:
    return ReviewAgainQuizAttemptResponse(
        attempt_id=attempt.id,
        quiz_id=quiz.id,
        document_id=quiz.document_id,
        highlight_id=quiz.highlight_id,
        user_answer=attempt.user_answer,
        is_correct=attempt.is_correct,
        feedback=attempt.feedback,
        attempted_at=attempt.created_at,
        quiz_type=quiz.quiz_type,
        question=quiz.question,
        answer=quiz.answer,
        explanation=quiz.explanation,
        source_text=quiz.source_text,
        document_title=document.title,
        page_number=highlight.page_number,
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
            build_explanation_request(db, highlight)
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
                error_message=sanitize_provider_error_message(exc),
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


@app.post(
    "/api/v1/highlights/{highlight_id}/glossary-terms",
    response_model=list[GlossaryTermResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_highlight_glossary_terms(
    highlight_id: int,
    db: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> list[GlossaryTerm]:
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
        llm_response = provider.generate_glossary_terms(
            build_glossary_request(db, highlight)
        )
    except Exception as exc:
        db.add(
            LLMRequestLog(
                provider=provider_name,
                model=model_name,
                task_type="glossary_extraction",
                status="error",
                latency_ms=now_latency_ms(start_time),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                estimated_cost=None,
                document_id=highlight.document_id,
                highlight_id=highlight.id,
                error_message=sanitize_provider_error_message(exc),
            )
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Glossary extraction failed.",
        ) from exc

    glossary_terms = [
        GlossaryTerm(
            document_id=highlight.document_id,
            highlight_id=highlight.id,
            term=term.term,
            definition=term.definition,
            source_text=term.source_text,
            provider=llm_response.usage.provider,
            model=llm_response.usage.model,
        )
        for term in llm_response.content.terms
    ]
    db.add_all(glossary_terms)
    db.add(
        LLMRequestLog(
            provider=llm_response.usage.provider,
            model=llm_response.usage.model,
            task_type="glossary_extraction",
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
    for glossary_term in glossary_terms:
        db.refresh(glossary_term)

    return glossary_terms


@app.post(
    "/api/v1/highlights/{highlight_id}/quizzes",
    response_model=list[QuizResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_highlight_quizzes(
    highlight_id: int,
    request: QuizGenerationOptions | None = Body(default=None),
    db: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> list[Quiz]:
    highlight = db.get(Highlight, highlight_id)
    if highlight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found.",
        )

    options = request or QuizGenerationOptions()
    provider_name = getattr(provider, "provider", "unknown")
    model_name = getattr(provider, "model", "unknown")
    start_time = perf_counter()

    try:
        quiz_request = build_quiz_request(db, highlight, options)
        llm_response = provider.generate_quizzes(quiz_request)
        if len(llm_response.content.quizzes) > quiz_request.max_quizzes:
            raise ValueError("Provider returned too many quizzes.")
    except Exception as exc:
        db.rollback()
        db.add(
            LLMRequestLog(
                provider=provider_name,
                model=model_name,
                task_type="quiz_generation",
                status="error",
                latency_ms=now_latency_ms(start_time),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                estimated_cost=None,
                document_id=highlight.document_id,
                highlight_id=highlight.id,
                error_message=sanitize_provider_error_message(exc),
            )
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quiz generation failed.",
        ) from exc

    quizzes = [
        Quiz(
            document_id=highlight.document_id,
            highlight_id=highlight.id,
            quiz_type=quiz.quiz_type,
            question=quiz.question,
            answer=quiz.answer,
            explanation=quiz.explanation,
            source_text=quiz.source_text,
            provider=llm_response.usage.provider,
            model=llm_response.usage.model,
        )
        for quiz in llm_response.content.quizzes
    ]
    db.add_all(quizzes)
    db.add(
        LLMRequestLog(
            provider=llm_response.usage.provider,
            model=llm_response.usage.model,
            task_type="quiz_generation",
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
    for quiz in quizzes:
        db.refresh(quiz)

    return quizzes


@app.post(
    "/api/v1/quizzes/{quiz_id}/attempts",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz_attempt(
    quiz_id: int,
    request: QuizAttemptCreateRequest,
    db: Session = Depends(get_db_session),
) -> QuizAttempt:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_answer=request.user_answer,
        is_correct=request.is_correct,
        feedback=request.feedback,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


@app.get(
    "/api/v1/quiz-attempts/review-again",
    response_model=list[ReviewAgainQuizAttemptResponse],
)
def list_review_again_quiz_attempts(
    document_id: int | None = None,
    db: Session = Depends(get_db_session),
) -> list[ReviewAgainQuizAttemptResponse]:
    if document_id is not None and db.get(Document, document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    statement = (
        select(QuizAttempt, Quiz, Highlight, Document)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Highlight, Quiz.highlight_id == Highlight.id)
        .join(Document, Quiz.document_id == Document.id)
        .where(QuizAttempt.is_correct.is_(False))
        .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
    )
    if document_id is not None:
        statement = statement.where(Quiz.document_id == document_id)

    return [
        review_again_attempt_to_response(attempt, quiz, highlight, document)
        for attempt, quiz, highlight, document in db.execute(statement).all()
    ]


@app.post(
    "/api/v1/quiz-attempts/{attempt_id}/review-cards",
    response_model=ReviewCardResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz_attempt_review_card(
    attempt_id: int,
    db: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> ReviewCard:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz attempt not found.",
        )
    if attempt.is_correct is not False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz attempt is not marked for review again.",
        )

    quiz = db.get(Quiz, attempt.quiz_id)
    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review card generation failed.",
        )
    highlight = db.get(Highlight, quiz.highlight_id)
    document = db.get(Document, quiz.document_id)
    if highlight is None or document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review card generation failed.",
        )

    provider_name = getattr(provider, "provider", "unknown")
    model_name = getattr(provider, "model", "unknown")
    start_time = perf_counter()

    try:
        review_card_request = build_review_card_request(
            attempt=attempt,
            quiz=quiz,
            highlight=highlight,
            document=document,
        )
        llm_response = provider.generate_review_card(review_card_request)
    except Exception as exc:
        db.rollback()
        db.add(
            LLMRequestLog(
                provider=provider_name,
                model=model_name,
                task_type="review_card_generation",
                status="error",
                latency_ms=now_latency_ms(start_time),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                estimated_cost=None,
                document_id=quiz.document_id,
                highlight_id=quiz.highlight_id,
                error_message=sanitize_provider_error_message(exc),
            )
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review card generation failed.",
        ) from exc

    review_card = ReviewCard(
        document_id=quiz.document_id,
        quiz_id=quiz.id,
        quiz_attempt_id=attempt.id,
        front=llm_response.content.front,
        back=llm_response.content.back,
        source_text=llm_response.content.source_text,
        provider=llm_response.usage.provider,
        model=llm_response.usage.model,
    )
    db.add(review_card)
    db.add(
        LLMRequestLog(
            provider=llm_response.usage.provider,
            model=llm_response.usage.model,
            task_type="review_card_generation",
            status="success",
            latency_ms=now_latency_ms(start_time),
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
            total_tokens=llm_response.usage.total_tokens,
            estimated_cost=llm_response.usage.estimated_cost,
            document_id=quiz.document_id,
            highlight_id=quiz.highlight_id,
            error_message=None,
        )
    )
    db.commit()
    db.refresh(review_card)

    return review_card


@app.get(
    "/api/v1/quizzes/{quiz_id}/attempts",
    response_model=list[QuizAttemptResponse],
)
def list_quiz_attempts(
    quiz_id: int,
    db: Session = Depends(get_db_session),
) -> list[QuizAttempt]:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )

    return list(
        db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.created_at, QuizAttempt.id)
        )
    )
