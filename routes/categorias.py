# ruff: noqa: B008


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.categoria import Categoria
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/categorias", tags=["categorias"])


class CategoriaItem(BaseModel):
    id: int
    nome: str
    codigo_prefixo: str
    descricao: str | None = None
    ativo: bool


class CategoriaCreateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    codigo_prefixo: str = Field(min_length=1, max_length=5)
    descricao: str | None = Field(default=None, max_length=255)

    @field_validator("nome", "codigo_prefixo")
    @classmethod
    def validar_texto_obrigatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatório")
        return value


class CategoriaUpdateRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    codigo_prefixo: str | None = Field(default=None, min_length=1, max_length=5)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None

    @field_validator("nome", "codigo_prefixo")
    @classmethod
    def validar_texto_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Campo não pode ficar vazio")
        return value


def _item(categoria: Categoria) -> CategoriaItem:
    return CategoriaItem.model_validate(categoria, from_attributes=True)


def _salvar(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Nome ou prefixo de categoria já cadastrado"
        ) from exc


@router.get("", response_model=list[CategoriaItem])
def listar_categorias(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    busca: str | None = None,
    ativo: bool | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    query = select(Categoria)
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.where(
            or_(Categoria.nome.ilike(termo), Categoria.codigo_prefixo.ilike(termo))
        )
    if ativo is not None:
        query = query.where(Categoria.ativo.is_(ativo))
    query = query.order_by(Categoria.nome).offset((page - 1) * limit).limit(limit)
    return [_item(categoria) for categoria in db.scalars(query).all()]


@router.get("/{categoria_id}", response_model=CategoriaItem)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return _item(categoria)


@router.post("", response_model=CategoriaItem, status_code=201)
def criar_categoria(
    payload: CategoriaCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    categoria = Categoria(
        nome=payload.nome.strip(),
        codigo_prefixo=payload.codigo_prefixo.strip(),
        descricao=payload.descricao,
        ativo=True,
    )
    db.add(categoria)
    _salvar(db)
    db.refresh(categoria)
    return _item(categoria)


@router.put("/{categoria_id}", response_model=CategoriaItem)
def atualizar_categoria(
    categoria_id: int,
    payload: CategoriaUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str) and field in {"nome", "codigo_prefixo"}:
            value = value.strip()
        setattr(categoria, field, value)
    _salvar(db)
    db.refresh(categoria)
    return _item(categoria)


@router.delete("/{categoria_id}")
def desativar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    categoria.ativo = False
    _salvar(db)
    return {"message": "Categoria desativada com sucesso"}
