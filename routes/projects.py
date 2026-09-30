from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from core.security import exigir_perfil, get_current_user
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectItem(BaseModel):
    id: int
    name: str
    description: str
    status: Literal["draft", "in_progress", "done", "archived"] = "draft"
    owner_id: int


class ProjectCreateRequest(BaseModel):
    name: str
    description: str
    status: Literal["draft", "in_progress", "done", "archived"] = "draft"
    owner_id: int


PROJECTS_DB = [
    ProjectItem(
        id=1,
        name="Site Institucional",
        description="Landing page para o cliente",
        status="done",
        owner_id=1,
    ),
    ProjectItem(
        id=2,
        name="Dashboard Admin",
        description="Painel de métricas internas",
        status="in_progress",
        owner_id=2,
    ),
    ProjectItem(
        id=3,
        name="Portal do Cliente",
        description="Area para gestão de pedidos",
        status="draft",
        owner_id=3,
    ),
]


def _require_project_access(current_user: Usuario, project_owner_id: int) -> None:
    if current_user.perfil in {PerfilEnum.admin, PerfilEnum.gestor}:
        return
    if project_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esse recurso",
        )


@router.get("", response_model=list[ProjectItem])
def list_projects(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = None,
    current_user: Usuario = Depends(get_current_user),
):
    items = PROJECTS_DB
    if current_user.perfil not in {PerfilEnum.admin, PerfilEnum.gestor}:
        items = [project for project in PROJECTS_DB if project.owner_id == current_user.id]
    if status:
        items = [project for project in items if project.status == status]
    return items[(page - 1) * limit : page * limit]


@router.get("/{project_id}", response_model=ProjectItem)
def get_project(
    project_id: int,
    current_user: Usuario = Depends(get_current_user),
):
    for project in PROJECTS_DB:
        if project.id == project_id:
            _require_project_access(current_user, project.owner_id)
            return project
    raise HTTPException(status_code=404, detail="Project not found")


@router.post("", response_model=ProjectItem, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    current_user: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor, PerfilEnum.almoxarife)
    ),
):
    if payload.owner_id != current_user.id and current_user.perfil not in {
        PerfilEnum.admin,
        PerfilEnum.gestor,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode registrar projetos próprios",
        )
    new_project = ProjectItem(
        id=max((project.id for project in PROJECTS_DB), default=0) + 1,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        owner_id=payload.owner_id,
    )
    PROJECTS_DB.append(new_project)
    return new_project


@router.put("/{project_id}", response_model=ProjectItem)
def update_project(
    project_id: int,
    payload: ProjectCreateRequest,
    current_user: Usuario = Depends(get_current_user),
):
    for index, project in enumerate(PROJECTS_DB):
        if project.id == project_id:
            _require_project_access(current_user, project.owner_id)
            updated_project = ProjectItem(
                id=project.id,
                name=payload.name,
                description=payload.description,
                status=payload.status,
                owner_id=payload.owner_id,
            )
            PROJECTS_DB[index] = updated_project
            return updated_project
    raise HTTPException(status_code=404, detail="Project not found")


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: Usuario = Depends(get_current_user),
):
    for index, project in enumerate(PROJECTS_DB):
        if project.id == project_id:
            _require_project_access(current_user, project.owner_id)
            del PROJECTS_DB[index]
            return {"message": "Project deleted successfully"}
    raise HTTPException(status_code=404, detail="Project not found")
