from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base

MYSQL_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class EstoqueSetor(Base):
    __tablename__ = "estoque_setor"
    __table_args__ = (UniqueConstraint("setor_id", "material_id", name="uq_estoque_setor_material"),)

    id: Mapped[int] = mapped_column(MYSQL_ID, primary_key=True)
    setor_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("setores.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("materiais.id"), nullable=False)
    quantidade_atual: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class MovimentacaoEstoqueSetor(Base):
    __tablename__ = "movimentacoes_estoque_setor"

    id: Mapped[int] = mapped_column(MYSQL_ID, primary_key=True)
    setor_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("setores.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("materiais.id"), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(MYSQL_ID, ForeignKey("usuarios.id"), nullable=True)
    requisicao_id: Mapped[int | None] = mapped_column(MYSQL_ID, ForeignKey("requisicoes.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    saldo_anterior: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    saldo_posterior: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
