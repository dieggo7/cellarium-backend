import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class StatusRequisicaoItemEnum(str, enum.Enum):
    pendente = "PENDENTE"
    separado = "SEPARADO"
    atendido = "ATENDIDO"
    cancelado = "CANCELADO"


class RequisicaoItem(Base):
    __tablename__ = "requisicao_itens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requisicao_id: Mapped[int] = mapped_column(
        ForeignKey("requisicoes.id"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("materiais.id"), nullable=False)
    quantidade_solicitada: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False
    )
    quantidade_separada: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    quantidade_atendida: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    quantidade_sobrante: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    status: Mapped[StatusRequisicaoItemEnum] = mapped_column(
        Enum(StatusRequisicaoItemEnum, values_callable=lambda e: [x.value for x in e]),
        default=StatusRequisicaoItemEnum.pendente,
        nullable=False,
    )
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
