# ruff: noqa: B008


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil
from database.session import get_db
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioItem(BaseModel):
    id: int
    nome: str
    login: str
    perfil: PerfilEnum
    setor_id: int | None = None
    ativo: bool


class UsuarioCreateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=6, max_length=1024)
    perfil: PerfilEnum
    setor_id: int | None = None

    @field_validator("nome", "login")
    @classmethod
    def normalizar_texto_obrigatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatório")
        return value

    @field_validator("senha")
    @classmethod
    def validar_tamanho_senha(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("A senha excede o limite permitido")
        return value


class UsuarioUpdateRequest(BaseModel):
    nome: str | None = None
    login: str | None = None
    perfil: PerfilEnum | None = None
    setor_id: int | None = None
    ativo: bool | None = None
    senha: str | None = Field(default=None, min_length=6, max_length=1024)

    @field_validator("nome", "login")
    @classmethod
    def normalizar_texto_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Campo não pode ficar vazio")
        return value

    @field_validator("senha")
    @classmethod
    def validar_tamanho_senha(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 1024:
            raise ValueError("A senha excede o limite permitido")
        return value


def _to_item(usuario: Usuario) -> UsuarioItem:
    return UsuarioItem(
        id=usuario.id,
        nome=usuario.nome,
        login=usuario.login,
        perfil=usuario.perfil,
        setor_id=usuario.setor_id,
        ativo=usuario.ativo,
    )


@router.get("", response_model=list[UsuarioItem])
def list_usuarios(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    query = select(Usuario)
    if apenas_ativos:
        query = query.where(Usuario.ativo == True)

    usuarios = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()
    return [_to_item(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioItem)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return _to_item(usuario)


@router.post("", response_model=UsuarioItem, status_code=201)
def create_usuario(
    payload: UsuarioCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    if usuario_atual.perfil != PerfilEnum.admin:
        raise HTTPException(status_code=403, detail="Somente ADMIN pode criar usuários")
    if payload.perfil == PerfilEnum.solicitante and payload.setor_id is None:
        raise HTTPException(
            status_code=400, detail="setor_id é obrigatório para SOLICITANTE"
        )
    if payload.setor_id is not None:
        from models.setor import Setor

        setor = db.get(Setor, payload.setor_id)
        if setor is None or not setor.ativo:
            raise HTTPException(
                status_code=404, detail="Setor não encontrado ou inativo"
            )
    if db.scalar(select(Usuario).where(Usuario.login == payload.login)):
        raise HTTPException(status_code=409, detail="Login já cadastrado")

    from core.security import get_password_hash

    novo_usuario = Usuario(
        nome=payload.nome,
        login=payload.login,
        senha_hash=get_password_hash(payload.senha),
        perfil=payload.perfil,
        setor_id=payload.setor_id,
        ativo=True,
    )
    db.add(novo_usuario)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Login já cadastrado") from exc
    db.refresh(novo_usuario)

    return _to_item(novo_usuario)


@router.put("/{usuario_id}", response_model=UsuarioItem)
def update_usuario(
    usuario_id: int,
    payload: UsuarioUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    if usuario_atual.perfil != PerfilEnum.admin:
        raise HTTPException(
            status_code=403, detail="Somente ADMIN pode alterar usuários"
        )
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario_atual.id == usuario_id and (
        payload.ativo is False
        or (payload.perfil is not None and payload.perfil != PerfilEnum.admin)
    ):
        raise HTTPException(
            status_code=409,
            detail="Um ADMIN não pode desativar ou rebaixar a própria conta",
        )

    if payload.nome is not None:
        usuario.nome = payload.nome
    if payload.login is not None and payload.login != usuario.login:
        if db.scalar(
            select(Usuario.id).where(
                Usuario.login == payload.login, Usuario.id != usuario_id
            )
        ):
            raise HTTPException(status_code=409, detail="Login já cadastrado")
        usuario.login = payload.login
    if payload.perfil is not None:
        usuario.perfil = payload.perfil
    if "setor_id" in payload.model_fields_set:
        usuario.setor_id = payload.setor_id
    if payload.ativo is not None:
        usuario.ativo = payload.ativo

    if payload.senha is not None:
        from core.security import get_password_hash

        usuario.senha_hash = get_password_hash(payload.senha)
    if usuario.perfil == PerfilEnum.solicitante:
        if usuario.setor_id is None:
            raise HTTPException(
                status_code=400, detail="setor_id é obrigatório para SOLICITANTE"
            )
        from models.setor import Setor

        setor = db.get(Setor, usuario.setor_id)
        if setor is None or not setor.ativo:
            raise HTTPException(
                status_code=404, detail="Setor não encontrado ou inativo"
            )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Login já cadastrado") from exc
    db.refresh(usuario)

    return _to_item(usuario)


@router.delete("/{usuario_id}")
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if usuario.id == usuario_atual.id:
        raise HTTPException(
            status_code=409, detail="Um ADMIN não pode desativar a própria conta"
        )
    usuario.ativo = False
    db.commit()
    return {"message": "Usuário desativado com sucesso"}
