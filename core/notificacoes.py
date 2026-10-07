from sqlalchemy import select
from sqlalchemy.orm import Session

from models.notificacao import Notificacao
from models.requisicao import Requisicao
from models.usuario import PerfilEnum, Usuario


def notificar_usuario(
    db: Session,
    usuario_id: int,
    event_key: str,
    tipo: str,
    titulo: str,
    mensagem: str,
    requisicao_id: int | None = None,
) -> None:
    exists = db.scalar(
        select(Notificacao.id).where(
            Notificacao.usuario_id == usuario_id,
            Notificacao.event_key == event_key,
        )
    )
    if exists is None:
        db.add(
            Notificacao(
                usuario_id=usuario_id,
                requisicao_id=requisicao_id,
                event_key=event_key,
                tipo=tipo,
                titulo=titulo,
                mensagem=mensagem,
            )
        )


def notificar_almoxarifado(
    db: Session, event_key: str, tipo: str, titulo: str, mensagem: str, requisicao_id: int
) -> None:
    users = db.scalars(
        select(Usuario.id).where(
            Usuario.ativo.is_(True),
            Usuario.perfil.in_([PerfilEnum.almoxarife, PerfilEnum.admin, PerfilEnum.gestor]),
        )
    ).all()
    for usuario_id in users:
        notificar_usuario(db, usuario_id, event_key, tipo, titulo, mensagem, requisicao_id)


def nome_requisicao(db: Session, requisicao_id: int) -> str:
    return db.scalar(select(Requisicao.numero).where(Requisicao.id == requisicao_id)) or f"#{requisicao_id}"
