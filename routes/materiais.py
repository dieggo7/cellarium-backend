# ruff: noqa: B008


from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.categoria import Categoria
from models.material import Material
from models.unidade_medida import UnidadeMedida
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/materiais", tags=["materiais"])


class MaterialItem(BaseModel):
    id: int
    codigo: str
    descricao: str
    categoria_id: int
    unidade_medida_id: int
    especificacao: str | None = None
    qr_code: str | None = None
    peso_unitario_g: Decimal | None = None
    ativo: bool


class MaterialCreateRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    descricao: str = Field(min_length=1, max_length=255)
    categoria_id: int = Field(gt=0)
    unidade_medida_id: int = Field(gt=0)
    especificacao: str | None = Field(default=None, max_length=255)
    qr_code: str | None = Field(default=None, max_length=36)
    peso_unitario_g: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=6)

    @field_validator("codigo", "descricao")
    @classmethod
    def validar_texto_obrigatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatório")
        return value


class MaterialUpdateRequest(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    descricao: str | None = Field(default=None, min_length=1, max_length=255)
    categoria_id: int | None = Field(default=None, gt=0)
    unidade_medida_id: int | None = Field(default=None, gt=0)
    especificacao: str | None = Field(default=None, max_length=255)
    qr_code: str | None = Field(default=None, max_length=36)
    peso_unitario_g: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=6)
    ativo: bool | None = None

    @field_validator("codigo", "descricao")
    @classmethod
    def validar_texto_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Campo não pode ficar vazio")
        return value


def _to_item(material: Material) -> MaterialItem:
    return MaterialItem(
        id=material.id,
        codigo=material.codigo,
        descricao=material.descricao,
        categoria_id=material.categoria_id,
        unidade_medida_id=material.unidade_medida_id,
        especificacao=material.especificacao,
        qr_code=material.qr_code,
        peso_unitario_g=material.peso_unitario_g,
        ativo=material.ativo,
    )


@router.get("", response_model=list[MaterialItem])
def list_materiais(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    busca: str | None = None,
    categoria_id: int | None = Query(default=None, gt=0),
    ativo: bool | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    query = select(Material)
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.where(or_(Material.codigo.ilike(termo), Material.descricao.ilike(termo)))
    if categoria_id is not None:
        query = query.where(Material.categoria_id == categoria_id)
    if ativo is not None:
        query = query.where(Material.ativo.is_(ativo))

    materiais = db.scalars(query.order_by(Material.descricao).offset((page - 1) * limit).limit(limit)).all()
    return [_to_item(m) for m in materiais]


@router.get("/{material_id}", response_model=MaterialItem)
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    return _to_item(material)


@router.post("", response_model=MaterialItem, status_code=201)
def create_material(
    payload: MaterialCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    categoria = db.get(Categoria, payload.categoria_id)
    unidade = db.get(UnidadeMedida, payload.unidade_medida_id)
    if categoria is None or not categoria.ativo:
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou inativa")
    if unidade is None or not unidade.ativo:
        raise HTTPException(status_code=404, detail="Unidade de medida não encontrada ou inativa")
    if db.scalar(select(Material).where(Material.codigo == payload.codigo)):
        raise HTTPException(status_code=409, detail="Código de material já cadastrado")

    if payload.qr_code and db.scalar(select(Material).where(Material.qr_code == payload.qr_code)):
        raise HTTPException(status_code=409, detail="Identificador legado já cadastrado")

    material = Material(
        codigo=payload.codigo,
        descricao=payload.descricao,
        categoria_id=payload.categoria_id,
        unidade_medida_id=payload.unidade_medida_id,
        especificacao=payload.especificacao,
        qr_code=payload.qr_code,
        peso_unitario_g=payload.peso_unitario_g,
        ativo=True,
    )
    db.add(material)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Código de material ou identificador legado já cadastrado") from exc
    db.refresh(material)

    return _to_item(material)


@router.put("/{material_id}", response_model=MaterialItem)
def update_material(
    material_id: int,
    payload: MaterialUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    material = db.scalar(select(Material).where(Material.id == material_id).with_for_update())
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")

    if payload.codigo is not None and payload.codigo != material.codigo:
        if db.scalar(select(Material).where(Material.codigo == payload.codigo)):
            raise HTTPException(status_code=409, detail="Código de material já cadastrado")
        material.codigo = payload.codigo

    if (
        "qr_code" in payload.model_fields_set
        and payload.qr_code is not None
        and payload.qr_code != material.qr_code
        and db.scalar(select(Material).where(Material.qr_code == payload.qr_code))
    ):
        raise HTTPException(status_code=409, detail="Identificador legado já cadastrado")
    if "qr_code" in payload.model_fields_set:
        material.qr_code = payload.qr_code
    if "peso_unitario_g" in payload.model_fields_set:
        material.peso_unitario_g = payload.peso_unitario_g

    if payload.descricao is not None:
        material.descricao = payload.descricao
    if payload.categoria_id is not None:
        categoria = db.get(Categoria, payload.categoria_id)
        if categoria is None or not categoria.ativo:
            raise HTTPException(status_code=404, detail="Categoria não encontrada ou inativa")
        material.categoria_id = payload.categoria_id
    if payload.unidade_medida_id is not None:
        unidade = db.get(UnidadeMedida, payload.unidade_medida_id)
        if unidade is None or not unidade.ativo:
            raise HTTPException(status_code=404, detail="Unidade de medida não encontrada ou inativa")
        material.unidade_medida_id = payload.unidade_medida_id
    if payload.especificacao is not None:
        material.especificacao = payload.especificacao
    if payload.ativo is not None:
        material.ativo = payload.ativo

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Código de material ou identificador legado já cadastrado") from exc
    db.refresh(material)

    return _to_item(material)


@router.delete("/{material_id}")
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    material = db.scalar(select(Material).where(Material.id == material_id).with_for_update())
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    material.ativo = False
    db.commit()
    return {"message": "Material desativado com sucesso"}