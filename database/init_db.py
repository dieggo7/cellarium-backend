from sqlalchemy.exc import OperationalError

from database.base import Base
from database.session import engine
from models.usuario import Usuario  # noqa: F401
from models.setor import Setor  # noqa: F401
from models.categoria import Categoria  # noqa: F401
from models.unidade_medida import UnidadeMedida  # noqa: F401
from models.material import Material  # noqa: F401
from models.localizacao import Localizacao  # noqa: F401
from models.estoque import Estoque  # noqa: F401
from models.atendimento_almoxarifado import AtendimentoAlmoxarifado  # noqa: F401
from models.movimentacao_estoque import MovimentacaoEstoque  # noqa: F401
from models.requisicao import Requisicao  # noqa: F401
from models.requisicao_item import RequisicaoItem  # noqa: F401


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        # MySQL is not available yet; keep the app bootable until the DB is configured.
        pass
