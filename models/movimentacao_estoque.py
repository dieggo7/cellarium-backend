import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class TipoMovimentacaoEnum(str, enum.Enum):
    entrada = "ENTRADA"
    saida = "SAIDA"
    ajuste = "AJUSTE"
    devolucao = "DEVOLUCAO"


class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiais.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    requisicao_id: Mapped[Optional[int]] = mapped_column(ForeignKey("requisicoes.id"), nullable=True)
    tipo: Mapped[TipoMovimentacaoEnum] = mapped_column(
        Enum(TipoMovimentacaoEnum, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    estoque_anterior: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    estoque_posterior: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    observacao: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)