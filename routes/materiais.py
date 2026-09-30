from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.material import Material
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/materiais", tags=["materiais"])


class MaterialItem(BaseModel):
    id: int
    codigo: str
    descricao: str
    categoria_id: int
    unidade_medida_id: int
    especificacao: Optional[str] = None
    qr_code: str
    ativo: bool


class MaterialCreateRequest(BaseModel):
    codigo: str
    descricao: str
    categoria_id: int
    unidade_medida_id: int
    especificacao: Optional[str] = None
    qr_code: Optional[str] = None


class MaterialUpdateRequest(BaseModel):
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    categoria_id: Optional[int] = None
    unidade_medida_id: Optional[int] = None
    especificacao: Optional[str] = None
    qr_code: Optional[str] = None
    ativo: Optional[bool] = None


def _to_item(material: Material) -> MaterialItem:
    return MaterialItem(
        id=material.id,
        codigo=material.codigo,
        descricao=material.descricao,
        categoria_id=material.categoria_id,
        unidade_medida_id=material.unidade_medida_id,
        especificacao=material.especificacao,
        qr_code=material.qr_code,
        ativo=material.ativo,
    )


@router.get("", response_model=list[MaterialItem])
def list_materiais(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    query = select(Material)
    if apenas_ativos:
        query = query.where(Material.ativo == True)  # noqa: E712

    materiais = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()
    return [_to_item(m) for m in materiais]


@router.get("/qrcode/{qr_code}", response_model=MaterialItem)
def get_material_por_qrcode(
    qr_code: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    material = db.scalar(select(Material).where(Material.qr_code == qr_code))
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado para este QR Code")
    return _to_item(material)


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
    if db.scalar(select(Material).where(Material.codigo == payload.codigo)):
        raise HTTPException(status_code=400, detail="Código de material já cadastrado")

    if payload.qr_code and db.scalar(select(Material).where(Material.qr_code == payload.qr_code)):
        raise HTTPException(status_code=400, detail="QR Code já cadastrado para outro material")

    material = Material(
        codigo=payload.codigo,
        descricao=payload.descricao,
        categoria_id=payload.categoria_id,
        unidade_medida_id=payload.unidade_medida_id,
        especificacao=payload.especificacao,
        qr_code=payload.qr_code,
        ativo=True,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    return _to_item(material)


@router.put("/{material_id}", response_model=MaterialItem)
def update_material(
    material_id: int,
    payload: MaterialUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")

    if payload.codigo is not None and payload.codigo != material.codigo:
        if db.scalar(select(Material).where(Material.codigo == payload.codigo)):
            raise HTTPException(status_code=400, detail="Código de material já cadastrado")
        material.codigo = payload.codigo

    if payload.qr_code is not None and payload.qr_code != material.qr_code:
        if db.scalar(select(Material).where(Material.qr_code == payload.qr_code)):
            raise HTTPException(status_code=400, detail="QR Code já cadastrado para outro material")
        material.qr_code = payload.qr_code

    if payload.descricao is not None:
        material.descricao = payload.descricao
    if payload.categoria_id is not None:
        material.categoria_id = payload.categoria_id
    if payload.unidade_medida_id is not None:
        material.unidade_medida_id = payload.unidade_medida_id
    if payload.especificacao is not None:
        material.especificacao = payload.especificacao
    if payload.ativo is not None:
        material.ativo = payload.ativo

    db.commit()
    db.refresh(material)

    return _to_item(material)


@router.delete("/{material_id}")
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    material.ativo = False
    db.commit()
    return {"message": "Material desativado com sucesso"}