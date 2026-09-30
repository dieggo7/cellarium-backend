# ruff: noqa: F401

from __future__ import annotations

from sqlalchemy.exc import OperationalError

from database.base import Base
from database.session import engine
from models.atendimento_almoxarifado import AtendimentoAlmoxarifado
from models.categoria import Categoria
from models.estoque import Estoque
from models.localizacao import Localizacao
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque
from models.requisicao import Requisicao
from models.requisicao_item import RequisicaoItem
from models.setor import Setor
from models.unidade_medida import UnidadeMedida
from models.usuario import Usuario


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        return




def ensure_database_ready() -> None:
    init_db()




__all__ = ["ensure_database_ready", "init_db"]