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
