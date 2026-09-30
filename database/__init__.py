"""Database package with lazy exports to avoid model import cycles."""

from importlib import import_module
from typing import Any

from database.base import Base

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "ensure_database_ready",
    "get_db",
    "init_db",
]

_LAZY_EXPORTS = {
    "SessionLocal": ("database.session", "SessionLocal"),
    "engine": ("database.session", "engine"),
    "get_db": ("database.session", "get_db"),
    "init_db": ("database.init_db", "init_db"),
    "ensure_database_ready": ("database.init_db", "ensure_database_ready"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value