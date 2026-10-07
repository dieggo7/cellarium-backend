# ruff: noqa: B008

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.atendimento_almoxarifado import (
    AtendimentoAlmoxarifado,
    StatusAtendimentoEnum,
)
from models.setor import Setor
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/atendimentos", tags=["atendimentos"])


class AtendimentoCreateRequest(BaseModel):
    setor_id: int = Field(gt=0)


def _atendimento_dict(
    atendimento: AtendimentoAlmoxarifado, setor: str, usuario: str | None = None
):
    result = {
        "id": atendimento.id,
        "usuario_id": atendimento.usuario_id,
        "setor_id": atendimento.setor_id,
        "setor": setor,
        "data_inicio": (
            atendimento.data_inicio.isoformat() if atendimento.data_inicio else None
        ),
        "data_fim": atendimento.data_fim.isoformat() if atendimento.data_fim else None,
        "status": atendimento.status,
    }
    if usuario is not None:
        result["usuario"] = usuario
    return result


def _consulta_atendimento(db: Session, atendimento_id: int):
    return db.execute(
        select(AtendimentoAlmoxarifado, Setor.nome, Usuario.nome)
        .join(Setor, Setor.id == AtendimentoAlmoxarifado.setor_id)
        .join(Usuario, Usuario.id == AtendimentoAlmoxarifado.usuario_id)
        .where(AtendimentoAlmoxarifado.id == atendimento_id)
    ).first()


@router.post("/iniciar", status_code=status.HTTP_201_CREATED)
def iniciar_atendimento(
    payload: AtendimentoCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
):
    usuario_id = usuario_atual.id
    db.rollback()
    try:
        with db.begin():
            db.scalar(select(Usuario).where(Usuario.id == usuario_id).with_for_update())
            setor = db.get(Setor, payload.setor_id)
            if setor is None or not setor.ativo:
                raise HTTPException(
                    status_code=404, detail="Setor não encontrado ou inativo"
                )
            aberto = db.scalar(
                select(AtendimentoAlmoxarifado)
                .where(
                    AtendimentoAlmoxarifado.usuario_id == usuario_id,
                    AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
                )
                .with_for_update()
            )
            if aberto is not None:
                setor_aberto = db.get(Setor, aberto.setor_id)
                if setor_aberto is None:
                    raise HTTPException(
                        status_code=409,
                        detail="O setor do atendimento aberto não existe",
                    )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensagem": "O usuário já possui um atendimento aberto",
                        "atendimento": _atendimento_dict(aberto, setor_aberto.nome),
                    },
                )
            atendimento = AtendimentoAlmoxarifado(
                usuario_id=usuario_id,
                setor_id=setor.id,
                status=StatusAtendimentoEnum.aberto,
                data_inicio=func.now(),
            )
            db.add(atendimento)
            db.flush()
            db.refresh(atendimento)
            return _atendimento_dict(atendimento, setor.nome)
    except HTTPException:
        db.rollback()
        raise


@router.post("/trocar")
def trocar_atendimento(
    payload: AtendimentoCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
):
    usuario_id = usuario_atual.id
    db.rollback()
    try:
        with db.begin():
            db.scalar(select(Usuario).where(Usuario.id == usuario_id).with_for_update())
            setor = db.get(Setor, payload.setor_id)
            if setor is None or not setor.ativo:
                raise HTTPException(
                    status_code=404, detail="Setor não encontrado ou inativo"
                )
            aberto = db.scalar(
                select(AtendimentoAlmoxarifado)
                .where(
                    AtendimentoAlmoxarifado.usuario_id == usuario_id,
                    AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
                )
                .order_by(AtendimentoAlmoxarifado.data_inicio.desc())
                .with_for_update()
            )
            if aberto is None:
                raise HTTPException(
                    status_code=409, detail="Não há atendimento aberto para trocar"
                )
            if aberto.setor_id == setor.id:
                return _atendimento_dict(aberto, setor.nome)

            aberto.status = StatusAtendimentoEnum.encerrado
            aberto.data_fim = func.now()
            atendimento = AtendimentoAlmoxarifado(
                usuario_id=usuario_id,
                setor_id=setor.id,
                status=StatusAtendimentoEnum.aberto,
                data_inicio=func.now(),
            )
            db.add(atendimento)
            db.flush()
            db.refresh(atendimento)
            return _atendimento_dict(atendimento, setor.nome)
    except HTTPException:
        db.rollback()
        raise


@router.get("/ativo")
def atendimento_ativo(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    row = db.execute(
        select(AtendimentoAlmoxarifado, Setor.nome)
        .join(Setor, Setor.id == AtendimentoAlmoxarifado.setor_id)
        .where(
            AtendimentoAlmoxarifado.usuario_id == usuario_atual.id,
            AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
        )
        .order_by(AtendimentoAlmoxarifado.data_inicio.desc())
    ).first()
    if row is None:
        raise HTTPException(
            status_code=404, detail="Você não possui atendimento aberto"
        )
    return _atendimento_dict(row[0], row[1])


@router.get("")
def listar_atendimentos(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    usuario_id: int | None = Query(default=None, gt=0),
    setor_id: int | None = Query(default=None, gt=0),
    status_filtro: StatusAtendimentoEnum | None = Query(default=None, alias="status"),
    data_inicio_de: datetime | None = None,
    data_inicio_ate: datetime | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    if (
        data_inicio_de is not None
        and data_inicio_ate is not None
        and data_inicio_de > data_inicio_ate
    ):
        raise HTTPException(
            status_code=400,
            detail="data_inicio_de não pode ser posterior a data_inicio_ate",
        )
    conditions = []
    if usuario_atual.perfil == PerfilEnum.almoxarife:
        conditions.append(AtendimentoAlmoxarifado.usuario_id == usuario_atual.id)
    elif usuario_id is not None:
        conditions.append(AtendimentoAlmoxarifado.usuario_id == usuario_id)
    if setor_id is not None:
        conditions.append(AtendimentoAlmoxarifado.setor_id == setor_id)
    if status_filtro is not None:
        conditions.append(AtendimentoAlmoxarifado.status == status_filtro)
    if data_inicio_de is not None:
        conditions.append(AtendimentoAlmoxarifado.data_inicio >= data_inicio_de)
    if data_inicio_ate is not None:
        conditions.append(AtendimentoAlmoxarifado.data_inicio <= data_inicio_ate)

    total = (
        db.scalar(
            select(func.count()).select_from(AtendimentoAlmoxarifado).where(*conditions)
        )
        or 0
    )
    rows = db.execute(
        select(AtendimentoAlmoxarifado, Setor.nome, Usuario.nome)
        .join(Setor, Setor.id == AtendimentoAlmoxarifado.setor_id)
        .join(Usuario, Usuario.id == AtendimentoAlmoxarifado.usuario_id)
        .where(*conditions)
        .order_by(AtendimentoAlmoxarifado.data_inicio.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "dados": [_atendimento_dict(row[0], row[1], row[2]) for row in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{atendimento_id}")
def detalhe_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    row = _consulta_atendimento(db, atendimento_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    if (
        usuario_atual.perfil == PerfilEnum.almoxarife
        and row[0].usuario_id != usuario_atual.id
    ):
        raise HTTPException(
            status_code=403, detail="Você só pode consultar seus próprios atendimentos"
        )
    return _atendimento_dict(row[0], row[1], row[2])


@router.patch("/{atendimento_id}/encerrar")
def encerrar_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
):
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    db.rollback()
    try:
        with db.begin():
            atendimento = db.scalar(
                select(AtendimentoAlmoxarifado)
                .where(AtendimentoAlmoxarifado.id == atendimento_id)
                .with_for_update()
            )
            if atendimento is None:
                raise HTTPException(
                    status_code=404, detail="Atendimento não encontrado"
                )
            if perfil != PerfilEnum.admin and atendimento.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=403,
                    detail="Você só pode encerrar seu próprio atendimento",
                )
            if atendimento.status != StatusAtendimentoEnum.aberto:
                raise HTTPException(
                    status_code=409, detail="O atendimento não está aberto"
                )
            atendimento.status = StatusAtendimentoEnum.encerrado
            atendimento.data_fim = func.now()
            db.flush()
            db.refresh(atendimento)
            setor = db.get(Setor, atendimento.setor_id)
            if setor is None:
                raise HTTPException(
                    status_code=409, detail="O setor do atendimento não existe"
                )
            return _atendimento_dict(atendimento, setor.nome)
    except HTTPException:
        db.rollback()
        raise
