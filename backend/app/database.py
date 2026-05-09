import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL_ENV_VAR = "INFODRIP_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///./info_drip.db"


def get_database_url() -> str:
    return os.getenv(DATABASE_URL_ENV_VAR, DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    pass


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
