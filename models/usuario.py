import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class PerfilEnum(str, enum.Enum):
    admin = "ADMIN"
    gestor = "GESTOR"
    almoxarife = "ALMOXARIFE"
    solicitante = "SOLICITANTE"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    login: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[PerfilEnum] = mapped_column(
        Enum(PerfilEnum, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    setor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("setores.id"), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )