import os
from collections.abc import Generator
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, create_engine, func
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
