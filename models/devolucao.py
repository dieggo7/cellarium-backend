import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class StatusDevolucaoEnum(str, enum.Enum):
    pendente = "PENDENTE"
    aceita = "ACEITA"
    rejeitada = "REJEITADA"


class Devolucao(Base):
    __tablename__ = "devolucoes"
    __table_args__ = (
        CheckConstraint("peso_total_g > 0", name="chk_devolucoes_peso_positivo"),
        CheckConstraint("peso_unitario_g > 0", name="chk_devolucoes_unidade_positiva"),
        CheckConstraint(
            "quantidade_calculada > 0", name="chk_devolucoes_quantidade_positiva"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requisicao_item_id: Mapped[int] = mapped_column(
        ForeignKey("requisicao_itens.id"), nullable=False
    )
    usuario_operador_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    usuario_analise_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    peso_total_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    peso_unitario_g: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    quantidade_calculada: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False
    )
    status: Mapped[StatusDevolucaoEnum] = mapped_column(
        Enum(
            StatusDevolucaoEnum,
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
        ),
        default=StatusDevolucaoEnum.pendente,
        nullable=False,
        index=True,
    )
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacao_analise: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    analisada_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
