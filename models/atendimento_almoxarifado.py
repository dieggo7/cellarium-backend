import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class StatusAtendimentoEnum(str, enum.Enum):
    aberto = "ABERTO"
    encerrado = "ENCERRADO"


class AtendimentoAlmoxarifado(Base):
    __tablename__ = "atendimentos_almoxarifado"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    setor_id: Mapped[int] = mapped_column(ForeignKey("setores.id"), nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    data_fim: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[StatusAtendimentoEnum] = mapped_column(
        Enum(StatusAtendimentoEnum, values_callable=lambda e: [x.value for x in e]),
        default=StatusAtendimentoEnum.aberto,
        nullable=False,
    )