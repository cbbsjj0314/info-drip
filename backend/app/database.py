import os
from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL_ENV_VAR = "INFODRIP_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///./info_drip.db"


def get_database_url() -> str:
    return os.getenv(DATABASE_URL_ENV_VAR, DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    original_filename: Mapped[str]
    storage_path: Mapped[str]
    page_count: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    highlights: Mapped[list["Highlight"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    llm_explanations: Mapped[list["LLMExplanation"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    glossary_terms: Mapped[list["GlossaryTerm"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    user_questions: Mapped[list["UserQuestion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    llm_request_logs: Mapped[list["LLMRequestLog"]] = relationship(
        back_populates="document",
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    page_number: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="pages")


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    page_number: Mapped[int]
    selected_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="highlights")
    llm_explanations: Mapped[list["LLMExplanation"]] = relationship(
        back_populates="highlight",
        cascade="all, delete-orphan",
    )
    glossary_terms: Mapped[list["GlossaryTerm"]] = relationship(
        back_populates="highlight",
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="highlight",
    )
    user_questions: Mapped[list["UserQuestion"]] = relationship(
        back_populates="highlight",
    )
    llm_request_logs: Mapped[list["LLMRequestLog"]] = relationship(
        back_populates="highlight",
    )


class LLMExplanation(Base):
    __tablename__ = "llm_explanations"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    highlight_id: Mapped[int] = mapped_column(ForeignKey("highlights.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    key_points: Mapped[str] = mapped_column(Text)
    provider: Mapped[str]
    model: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="llm_explanations")
    highlight: Mapped[Highlight] = relationship(back_populates="llm_explanations")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    highlight_id: Mapped[int] = mapped_column(ForeignKey("highlights.id"), index=True)
    term: Mapped[str]
    definition: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str]
    model: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="glossary_terms")
    highlight: Mapped[Highlight] = relationship(back_populates="glossary_terms")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    highlight_id: Mapped[int] = mapped_column(ForeignKey("highlights.id"), index=True)
    quiz_type: Mapped[str]
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str]
    model: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="quizzes")
    highlight: Mapped[Highlight] = relationship(back_populates="quizzes")
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
    )


class UserQuestion(Base):
    __tablename__ = "user_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    highlight_id: Mapped[int] = mapped_column(ForeignKey("highlights.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str]
    model: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="user_questions")
    highlight: Mapped[Highlight] = relationship(back_populates="user_questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    user_answer: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    quiz: Mapped[Quiz] = relationship(back_populates="attempts")
    review_cards: Mapped[list["ReviewCard"]] = relationship(
        back_populates="quiz_attempt",
        cascade="all, delete-orphan",
    )


class ReviewCard(Base):
    __tablename__ = "review_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    quiz_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_attempts.id"),
        index=True,
    )
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str]
    model: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    quiz_attempt: Mapped[QuizAttempt] = relationship(back_populates="review_cards")


class LLMRequestLog(Base):
    __tablename__ = "llm_request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str]
    model: Mapped[str]
    task_type: Mapped[str]
    status: Mapped[str]
    latency_ms: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    total_tokens: Mapped[int | None]
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"),
        index=True,
    )
    highlight_id: Mapped[int | None] = mapped_column(
        ForeignKey("highlights.id"),
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document | None] = relationship(back_populates="llm_request_logs")
    highlight: Mapped[Highlight | None] = relationship(back_populates="llm_request_logs")


engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
