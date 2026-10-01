# ruff: noqa: B008


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.estoque import Estoque
from models.localizacao import Localizacao
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/localizacoes", tags=["localizações"])


class LocalizacaoItem(BaseModel):
    id: int
    codigo: str
    descricao: str | None = None
    corredor: str | None = None
    estante: str | None = None
    prateleira: str | None = None
    posicao: str | None = None
    ativo: bool


class LocalizacaoCreateRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    descricao: str | None = Field(default=None, max_length=150)
    corredor: str | None = Field(default=None, max_length=20)
    estante: str | None = Field(default=None, max_length=20)
    prateleira: str | None = Field(default=None, max_length=20)
    posicao: str | None = Field(default=None, max_length=20)

    @field_validator("codigo")
    @classmethod
    def validar_codigo(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("codigo é obrigatório")
        return value


class LocalizacaoUpdateRequest(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    descricao: str | None = Field(default=None, max_length=150)
    corredor: str | None = Field(default=None, max_length=20)
    estante: str | None = Field(default=None, max_length=20)
    prateleira: str | None = Field(default=None, max_length=20)
    posicao: str | None = Field(default=None, max_length=20)
    ativo: bool | None = None

    @field_validator("codigo")
    @classmethod
    def validar_codigo_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("codigo não pode ficar vazio")
        return value


def _item(localizacao: Localizacao) -> LocalizacaoItem:
    return LocalizacaoItem.model_validate(localizacao, from_attributes=True)


def _salvar(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Código de localização já cadastrado"
        ) from exc


@router.get("")
def listar_localizacoes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    busca: str | None = None,
    ativo: bool | None = None,
    corredor: str | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    conditions = []
    if busca:
        termo = f"%{busca.strip()}%"
        conditions.append(
            or_(
                Localizacao.codigo.ilike(termo),
                Localizacao.descricao.ilike(termo),
                Localizacao.corredor.ilike(termo),
                Localizacao.estante.ilike(termo),
            )
        )
    if ativo is not None:
        conditions.append(Localizacao.ativo.is_(ativo))
    if corredor:
        conditions.append(Localizacao.corredor == corredor)
    total = (
        db.scalar(select(func.count()).select_from(Localizacao).where(*conditions)) or 0
    )
    rows = db.scalars(
        select(Localizacao)
        .where(*conditions)
        .order_by(Localizacao.codigo)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "dados": [_item(localizacao) for localizacao in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{localizacao_id}", response_model=LocalizacaoItem)
def obter_localizacao(
    localizacao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    localizacao = db.get(Localizacao, localizacao_id)
    if localizacao is None:
        raise HTTPException(status_code=404, detail="Localização não encontrada")
    return _item(localizacao)


@router.post("", response_model=LocalizacaoItem, status_code=201)
def criar_localizacao(
    payload: LocalizacaoCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.almoxarife)
    ),
):
    localizacao = Localizacao(**payload.model_dump())
    db.add(localizacao)
    _salvar(db)
    db.refresh(localizacao)
    return _item(localizacao)


@router.put("/{localizacao_id}", response_model=LocalizacaoItem)
def atualizar_localizacao(
    localizacao_id: int,
    payload: LocalizacaoUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.almoxarife)
    ),
):
    localizacao = db.get(Localizacao, localizacao_id)
    if localizacao is None:
        raise HTTPException(status_code=404, detail="Localização não encontrada")
    alteracoes = payload.model_dump(exclude_unset=True)
    if (
        "codigo" in alteracoes
        and alteracoes["codigo"] != localizacao.codigo
        and db.scalar(
            select(Localizacao.id).where(
                Localizacao.codigo == alteracoes["codigo"],
                Localizacao.id != localizacao_id,
            )
        )
    ):
        raise HTTPException(
            status_code=409, detail="Código de localização já cadastrado"
        )
    for field, value in alteracoes.items():
        setattr(localizacao, field, value)
    _salvar(db)
    db.refresh(localizacao)
    return _item(localizacao)


@router.delete("/{localizacao_id}")
def desativar_localizacao(
    localizacao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.almoxarife)
    ),
):
    db.rollback()
    try:
        with db.begin():
            localizacao = db.scalar(
                select(Localizacao)
                .where(Localizacao.id == localizacao_id)
                .with_for_update()
            )
            if localizacao is None:
                raise HTTPException(
                    status_code=404, detail="Localização não encontrada"
                )
            quantidade = (
                db.scalar(
                    select(func.count())
                    .select_from(Estoque)
                    .where(
                        Estoque.localizacao_id == localizacao_id,
                    )
                )
                or 0
            )
            if quantidade:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensagem": "A localização ainda é usada por materiais em estoque",
                        "materiais_vinculados": quantidade,
                    },
                )
            localizacao.ativo = False
            db.flush()
            return {"message": "Localização desativada com sucesso"}
    except HTTPException:
        db.rollback()
        raise
