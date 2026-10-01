import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class StatusRequisicaoEnum(str, enum.Enum):
    pendente = "PENDENTE"
    em_separacao = "EM_SEPARACAO"
    separada = "SEPARADA"
    atendida = "ATENDIDA"
    cancelada = "CANCELADA"


class Requisicao(Base):
    __tablename__ = "requisicoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    numero: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    setor_id: Mapped[int] = mapped_column(ForeignKey("setores.id"), nullable=False)
    usuario_solicitante_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    usuario_separador_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    status: Mapped[StatusRequisicaoEnum] = mapped_column(
        Enum(StatusRequisicaoEnum, values_callable=lambda e: [x.value for x in e]),
        default=StatusRequisicaoEnum.pendente,
        nullable=False,
    )
    data_solicitacao: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    data_inicio_separacao: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    data_conclusao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
