

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.categoria import Categoria
from models.usuario import PerfilEnum, Usuario


router = APIRouter(
    prefix="/categorias",
    tags=["categorias"],
)


class CategoriaItem(BaseModel):
    id: int
    nome: str
    codigo_prefixo: str | None = None
    descricao: str | None = None
    ativo: bool


def _to_item(categoria: Categoria) -> CategoriaItem:
    return CategoriaItem(
        id=categoria.id,
        nome=categoria.nome,
        codigo_prefixo=categoria.codigo_prefixo,
        descricao=categoria.descricao,
        ativo=categoria.ativo,
    )


@router.get("", response_model=list[CategoriaItem])
def list_categorias(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    query = select(Categoria)

    if apenas_ativos:
        query = query.where(Categoria.ativo == True)

    categorias = db.scalars(
        query
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return [_to_item(categoria) for categoria in categorias]

@router.get("/{categoria_id}", response_model=CategoriaItem)
def get_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    categoria = db.get(Categoria, categoria_id)

    if not categoria:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Categoria não encontrada",
        )

    return _to_item(categoria)

class CategoriaCreateRequest(BaseModel):
    nome: str
    codigo_prefixo: str | None = None
    descricao: str | None = None

@router.post("", response_model=CategoriaItem, status_code=201)
def create_categoria(
    payload: CategoriaCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    categoria_existente = db.scalar(
        select(Categoria).where(
            Categoria.nome == payload.nome
        )
    )

    if categoria_existente:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="Categoria já cadastrada",
        )

    nova_categoria = Categoria(
        nome=payload.nome,
        codigo_prefixo=payload.codigo_prefixo,
        descricao=payload.descricao,
        ativo=True,
    )

    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return _to_item(nova_categoria)