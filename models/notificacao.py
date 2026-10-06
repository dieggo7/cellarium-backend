from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base

MYSQL_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (UniqueConstraint("usuario_id", "event_key", name="uq_notificacao_usuario_evento"),)

    id: Mapped[int] = mapped_column(MYSQL_ID, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("usuarios.id"), nullable=False)
    requisicao_id: Mapped[int | None] = mapped_column(MYSQL_ID, ForeignKey("requisicoes.id"), nullable=True)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    lida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
