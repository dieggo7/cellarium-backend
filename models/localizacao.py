from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Localizacao(Base):
    __tablename__ = "localizacoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(150), nullable=True)
    corredor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estante: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prateleira: Mapped[str | None] = mapped_column(String(20), nullable=True)
    posicao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )