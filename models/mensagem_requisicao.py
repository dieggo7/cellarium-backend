from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base

MYSQL_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class MensagemRequisicao(Base):
    __tablename__ = "mensagens_requisicao"

    id: Mapped[int] = mapped_column(MYSQL_ID, primary_key=True)
    requisicao_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("requisicoes.id"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(MYSQL_ID, ForeignKey("usuarios.id"), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
