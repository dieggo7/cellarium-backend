from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Estoque(Base):
    __tablename__ = "estoque"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materiais.id"), unique=True, nullable=False
    )
    quantidade_atual: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    estoque_minimo: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    estoque_maximo: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    localizacao_id: Mapped[int | None] = mapped_column(
        ForeignKey("localizacoes.id"), nullable=True
    )
    lote: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_ultima_movimentacao: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
