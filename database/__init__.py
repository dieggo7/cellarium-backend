"""Database package for the Cellarium backend.


This package centralizes the SQLAlchemy base class, database engine creation,
request-scoped sessions and startup initialization logic.
"""


from database.base import Base
from database.init_db import ensure_database_ready, init_db
from database.session import SessionLocal, engine, get_db


__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
    "ensure_database_ready",
]