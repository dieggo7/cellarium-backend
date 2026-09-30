from __future__ import annotations

from sqlalchemy.exc import OperationalError

from database.base import Base
from database.session import engine


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        return


def ensure_database_ready() -> None:
    init_db()


__all__ = ["init_db", "ensure_database_ready"]
