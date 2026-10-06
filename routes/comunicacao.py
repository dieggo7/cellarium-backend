# ruff: noqa: B008

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.notificacoes import nome_requisicao, notificar_almoxarifado, notificar_usuario
from core.security import exigir_perfil
from database.session import get_db
from models.mensagem_requisicao import MensagemRequisicao
from models.notificacao import Notificacao
from models.requisicao import Requisicao
from models.usuario import PerfilEnum, Usuario

router = APIRouter(tags=["conversas e notificações"])
ROLES = (PerfilEnum.solicitante, PerfilEnum.almoxarife, PerfilEnum.gestor, PerfilEnum.admin)


class MensagemRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


def _acesso(requisicao: Requisicao, usuario: Usuario):
    if usuario.perfil == PerfilEnum.solicitante and requisicao.usuario_solicitante_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você só pode acessar suas próprias conversas")


@router.get("/requisicoes/{requisicao_id}/mensagens")
def listar_mensagens(requisicao_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(exigir_perfil(*ROLES))):
    requisicao = db.get(Requisicao, requisicao_id)
    if requisicao is None:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    _acesso(requisicao, usuario)
    rows = db.execute(select(MensagemRequisicao, Usuario.nome).join(Usuario, Usuario.id == MensagemRequisicao.usuario_id)
        .where(MensagemRequisicao.requisicao_id == requisicao_id).order_by(MensagemRequisicao.created_at, MensagemRequisicao.id)).all()
    return [{"id": message.id, "requisicao_id": requisicao_id, "usuario_id": message.usuario_id,
             "usuario": name, "texto": message.texto, "created_at": message.created_at} for message, name in rows]


@router.post("/requisicoes/{requisicao_id}/mensagens", status_code=201)
def enviar_mensagem(requisicao_id: int, payload: MensagemRequest, db: Session = Depends(get_db), usuario: Usuario = Depends(exigir_perfil(*ROLES))):
    requisicao = db.get(Requisicao, requisicao_id)
    if requisicao is None:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    _acesso(requisicao, usuario)
    text = payload.texto.strip()
    if not text:
        raise HTTPException(status_code=400, detail="A mensagem não pode ficar vazia")
    message = MensagemRequisicao(requisicao_id=requisicao_id, usuario_id=usuario.id, texto=text)
    db.add(message)
    db.flush()
    number = nome_requisicao(db, requisicao_id)
    if usuario.perfil == PerfilEnum.solicitante:
        notificar_almoxarifado(db, f"mensagem:{message.id}", "MENSAGEM", "Nova mensagem", f"{usuario.nome} escreveu na requisição {number}.", requisicao_id)
    else:
        notificar_usuario(db, requisicao.usuario_solicitante_id, f"mensagem:{message.id}", "MENSAGEM", "Resposta do almoxarifado", f"Há uma nova mensagem na requisição {number}.", requisicao_id)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "requisicao_id": requisicao_id, "usuario_id": message.usuario_id,
            "usuario": usuario.nome, "texto": message.texto, "created_at": message.created_at}


@router.get("/notificacoes")
def listar_notificacoes(db: Session = Depends(get_db), usuario: Usuario = Depends(exigir_perfil(*ROLES))):
    rows = db.scalars(select(Notificacao).where(Notificacao.usuario_id == usuario.id).order_by(Notificacao.created_at.desc(), Notificacao.id.desc()).limit(100)).all()
    return [{"id": row.id, "requisicao_id": row.requisicao_id, "tipo": row.tipo, "titulo": row.titulo,
             "mensagem": row.mensagem, "lida": row.lida, "created_at": row.created_at} for row in rows]


@router.patch("/notificacoes/{notificacao_id}/lida")
def marcar_lida(notificacao_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(exigir_perfil(*ROLES))):
    row = db.scalar(select(Notificacao).where(Notificacao.id == notificacao_id, Notificacao.usuario_id == usuario.id).with_for_update())
    if row is None:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    row.lida = True
    db.commit()
    return {"id": row.id, "lida": row.lida}


@router.patch("/notificacoes/lidas")
def marcar_todas_lidas(db: Session = Depends(get_db), usuario: Usuario = Depends(exigir_perfil(*ROLES))):
    result = db.execute(update(Notificacao).where(Notificacao.usuario_id == usuario.id, Notificacao.lida.is_(False)).values(lida=True))
    db.commit()
    return {"atualizadas": result.rowcount or 0}
