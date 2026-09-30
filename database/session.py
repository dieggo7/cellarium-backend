from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from database.base import Base

engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
    future=True,
    echo=settings.database_echo,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session]:
    """Yield a SQLAlchemy session for FastAPI dependencies.


    The dependency pattern is the standard in FastAPI + SQLAlchemy: each request
    gets a scoped session, and the session is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "SessionLocal", "engine", "get_db"]
