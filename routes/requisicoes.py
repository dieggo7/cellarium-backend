# ruff: noqa: B008

import logging
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Integer, cast, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, aliased

from core.estoque import buscar_estoque_para_update
from core.notificacoes import notificar_almoxarifado, notificar_usuario
from core.security import exigir_perfil
from database.session import get_db
from models.atendimento_almoxarifado import (
    AtendimentoAlmoxarifado,
    StatusAtendimentoEnum,
)
from models.estoque_setor import EstoqueSetor, MovimentacaoEstoqueSetor
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacaoEnum
from models.requisicao import Requisicao, StatusRequisicaoEnum
from models.requisicao_item import RequisicaoItem, StatusRequisicaoItemEnum
from models.setor import Setor
from models.usuario import PerfilEnum, Usuario
from routes.requisicoes_itens import obter_itens_requisicao

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requisicoes", tags=["requisições"])


class ItemSolicitado(BaseModel):
    material_id: int = Field(gt=0)
    quantidade_solicitada: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=500)


class RequisicaoCreateRequest(BaseModel):
    setor_id: int | None = Field(default=None, gt=0)
    observacao: str | None = Field(default=None, max_length=500)
    itens: list[ItemSolicitado] = Field(min_length=1)


class RequisicaoUpdateRequest(BaseModel):
    observacao: str | None = Field(default=None, max_length=500)


class CancelarRequest(BaseModel):
    motivo: str | None = Field(default=None, max_length=500)


class ConcluirRequest(BaseModel):
    permitir_parcial: bool = False


class SobraItemRequest(BaseModel):
    item_id: int = Field(gt=0)
    quantidade_sobrante: Decimal = Field(ge=0, max_digits=12, decimal_places=3)


class EncerrarOSRequest(BaseModel):
    itens: list[SobraItemRequest] = Field(default_factory=list, max_length=100)


def _conditions(
    usuario, status_filtro, setor_id, usuario_solicitante_id, numero, data_de, data_ate
):
    conditions = []
    if usuario.perfil == PerfilEnum.solicitante:
        conditions.append(Requisicao.usuario_solicitante_id == usuario.id)
    if status_filtro is not None:
        conditions.append(Requisicao.status == status_filtro)
    if setor_id is not None:
        conditions.append(Requisicao.setor_id == setor_id)
    if usuario_solicitante_id is not None:
        conditions.append(Requisicao.usuario_solicitante_id == usuario_solicitante_id)
    if numero:
        conditions.append(Requisicao.numero.ilike(f"%{numero.strip()}%"))
    if data_de is not None:
        conditions.append(
            Requisicao.data_solicitacao >= datetime.combine(data_de, time.min)
        )
    if data_ate is not None:
        conditions.append(
            Requisicao.data_solicitacao <= datetime.combine(data_ate, time.max)
        )
    return conditions


def _header_dict(row) -> dict:
    requisicao, setor_nome, solicitante_nome, separador_nome = row[:4]
    return {
        "id": requisicao.id,
        "numero": requisicao.numero,
        "setor": {"id": requisicao.setor_id, "nome": setor_nome},
        "usuario_solicitante_id": requisicao.usuario_solicitante_id,
        "solicitante": solicitante_nome,
        "usuario_separador_id": requisicao.usuario_separador_id,
        "separador": separador_nome,
        "status": requisicao.status,
        "data_solicitacao": requisicao.data_solicitacao,
        "data_inicio_separacao": requisicao.data_inicio_separacao,
        "data_conclusao": requisicao.data_conclusao,
        "os_encerrada_at": requisicao.os_encerrada_at,
        "observacao": requisicao.observacao,
    }


def _header_query():
    solicitante = aliased(Usuario)
    separador = aliased(Usuario)
    return (
        select(Requisicao, Setor.nome, solicitante.nome, separador.nome)
        .join(Setor, Setor.id == Requisicao.setor_id)
        .join(solicitante, solicitante.id == Requisicao.usuario_solicitante_id)
        .outerjoin(separador, separador.id == Requisicao.usuario_separador_id)
    )


def _detalhe(db: Session, requisicao_id: int) -> dict:
    row = db.execute(_header_query().where(Requisicao.id == requisicao_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    result = _header_dict(row)
    result["itens"] = obter_itens_requisicao(db, requisicao_id)
    return result


def _anexar_observacao(atual: str | None, adicional: str) -> str:
    valor = f"{atual}\n{adicional}" if atual else adicional
    if len(valor) > 500:
        raise HTTPException(
            status_code=409,
            detail="O histórico excede o limite de observação permitido",
        )
    return valor


@router.get("")
def listar_requisicoes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filtro: StatusRequisicaoEnum | None = Query(default=None, alias="status"),
    setor_id: int | None = Query(default=None, gt=0),
    usuario_solicitante_id: int | None = Query(default=None, gt=0),
    numero: str | None = None,
    data_de: date | None = None,
    data_ate: date | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(
            PerfilEnum.solicitante,
            PerfilEnum.almoxarife,
            PerfilEnum.gestor,
            PerfilEnum.admin,
        )
    ),
):
    if data_de is not None and data_ate is not None and data_de > data_ate:
        raise HTTPException(
            status_code=400, detail="data_de não pode ser posterior a data_ate"
        )
    conditions = _conditions(
        usuario_atual,
        status_filtro,
        setor_id,
        usuario_solicitante_id,
        numero,
        data_de,
        data_ate,
    )
    total = (
        db.scalar(select(func.count()).select_from(Requisicao).where(*conditions)) or 0
    )
    item_count = (
        select(func.count())
        .select_from(RequisicaoItem)
        .where(
            RequisicaoItem.requisicao_id == Requisicao.id,
        )
        .scalar_subquery()
    )
    rows = db.execute(
        _header_query()
        .add_columns(item_count.label("quantidade_itens"))
        .where(*conditions)
        .order_by(Requisicao.data_solicitacao.desc(), Requisicao.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    dados = []
    for row in rows:
        item = _header_dict(row)
        item["quantidade_itens"] = row[4]
        dados.append(item)
    return {"dados": dados, "total": total, "page": page, "limit": limit}


@router.get("/pendentes")
def listar_pendentes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    todos: bool = False,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(
            PerfilEnum.solicitante,
            PerfilEnum.almoxarife,
            PerfilEnum.gestor,
            PerfilEnum.admin,
        )
    ),
):
    clauses = []
    params: dict[str, object] = {}
    if usuario_atual.perfil == PerfilEnum.solicitante:
        clauses.append("usuario_solicitante_id = :usuario_id")
        params["usuario_id"] = usuario_atual.id
    elif usuario_atual.perfil == PerfilEnum.almoxarife and not todos:
        atendimento = db.scalar(
            select(AtendimentoAlmoxarifado)
            .where(
                AtendimentoAlmoxarifado.usuario_id == usuario_atual.id,
                AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
            )
            .order_by(AtendimentoAlmoxarifado.data_inicio.desc())
        )
        if atendimento is None:
            raise HTTPException(
                status_code=409,
                detail="Inicie um atendimento para consultar as requisições do setor",
            )
        clauses.append("setor_id = :setor_id")
        params["setor_id"] = atendimento.setor_id
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(
        text("SELECT COUNT(*) FROM vw_requisicoes_pendentes" + where), params
    ).scalar_one()
    rows = (
        db.execute(
            text(
                "SELECT * FROM vw_requisicoes_pendentes"
                + where
                + " ORDER BY data ASC, requisicao_id ASC LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": limit, "offset": (page - 1) * limit},
        )
        .mappings()
        .all()
    )
    return {
        "dados": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{requisicao_id}")
def obter_requisicao(
    requisicao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(
            PerfilEnum.solicitante,
            PerfilEnum.almoxarife,
            PerfilEnum.gestor,
            PerfilEnum.admin,
        )
    ),
):
    row = db.execute(_header_query().where(Requisicao.id == requisicao_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    if (
        usuario_atual.perfil == PerfilEnum.solicitante
        and row[0].usuario_solicitante_id != usuario_atual.id
    ):
        raise HTTPException(
            status_code=403, detail="Você só pode consultar suas próprias requisições"
        )
    result = _header_dict(row)
    result["itens"] = obter_itens_requisicao(db, requisicao_id)
    return result


@router.post("", status_code=201)
def criar_requisicao(
    payload: RequisicaoCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)
    ),
):
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    material_ids = [item.material_id for item in payload.itens]
    if len(material_ids) != len(set(material_ids)):
        raise HTTPException(
            status_code=400, detail="Não informe o mesmo material mais de uma vez"
        )
    if perfil == PerfilEnum.solicitante:
        setor_id = usuario_atual.setor_id
        if setor_id is None:
            raise HTTPException(
                status_code=409, detail="O solicitante não possui setor cadastrado"
            )
    else:
        setor_id = payload.setor_id
        if setor_id is None:
            raise HTTPException(
                status_code=400, detail="setor_id é obrigatório para ADMIN"
            )
    db.rollback()
    for tentativa in range(3):
        try:
            with db.begin():
                setor = db.get(Setor, setor_id)
                if setor is None or not setor.ativo:
                    raise HTTPException(
                        status_code=404, detail="Setor não encontrado ou inativo"
                    )
                materiais = db.scalars(
                    select(Material).where(
                        Material.id.in_(material_ids), Material.ativo.is_(True)
                    )
                ).all()
                if {material.id for material in materiais} != set(material_ids):
                    raise HTTPException(
                        status_code=404,
                        detail="Um ou mais materiais não existem ou estão inativos",
                    )
                ano = datetime.now().astimezone().year
                prefixo = f"REQ-{ano}-"
                sequencia = (
                    db.scalar(
                        select(
                            func.coalesce(
                                func.max(
                                    cast(func.substr(Requisicao.numero, 10), Integer)
                                ),
                                0,
                            )
                        ).where(Requisicao.numero.like(f"{prefixo}%"))
                    )
                    or 0
                )
                if sequencia >= 999999:
                    raise HTTPException(
                        status_code=409,
                        detail="Limite anual de números de requisição atingido",
                    )
                requisicao = Requisicao(
                    numero=f"{prefixo}{sequencia + 1:06d}",
                    setor_id=setor_id,
                    usuario_solicitante_id=usuario_id,
                    status=StatusRequisicaoEnum.pendente,
                    data_solicitacao=func.now(),
                    observacao=payload.observacao,
                )
                db.add(requisicao)
                db.flush()
                for item in payload.itens:
                    db.add(
                        RequisicaoItem(
                            requisicao_id=requisicao.id,
                            material_id=item.material_id,
                            quantidade_solicitada=item.quantidade_solicitada,
                            quantidade_separada=Decimal(0),
                            quantidade_atendida=Decimal(0),
                            status=StatusRequisicaoItemEnum.pendente,
                            observacao=item.observacao,
                        )
                    )
                notificar_almoxarifado(db, f"requisicao:{requisicao.id}:criada", "REQUISICAO", "Nova requisição", f"A requisição {requisicao.numero} aguarda atendimento.", requisicao.id)
                db.flush()
            return _detalhe(db, requisicao.id)
        except HTTPException:
            db.rollback()
            raise
        except (IntegrityError, OperationalError) as exc:
            logger.error(
                "Failed to create request (attempt %s/3): exc=%r orig=%r",
                tentativa + 1,
                exc,
                exc.orig,
                exc_info=True,
            )
            db.rollback()
            if tentativa == 2:
                raise HTTPException(
                    status_code=409,
                    detail="Não foi possível reservar número de requisição; tente novamente",
                ) from exc
    raise HTTPException(status_code=409, detail="Não foi possível criar a requisição")


@router.put("/{requisicao_id}")
def atualizar_requisicao(
    requisicao_id: int,
    payload: RequisicaoUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)
    ),
):
    if not payload.model_fields_set:
        raise HTTPException(status_code=400, detail="Informe observacao para atualizar")
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    db.rollback()
    try:
        with db.begin():
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == requisicao_id)
                .with_for_update()
            )
            if requisicao is None:
                raise HTTPException(status_code=404, detail="Requisição não encontrada")
            if (
                perfil == PerfilEnum.solicitante
                and requisicao.usuario_solicitante_id != usuario_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Você só pode alterar suas próprias requisições",
                )
            if requisicao.status != StatusRequisicaoEnum.pendente:
                raise HTTPException(
                    status_code=409, detail="A requisição precisa estar PENDENTE"
                )
            requisicao.observacao = payload.observacao
            db.flush()
        return _detalhe(db, requisicao_id)
    except HTTPException:
        db.rollback()
        raise


@router.patch("/{requisicao_id}/encerrar-os")
def encerrar_os(
    requisicao_id: int,
    payload: EncerrarOSRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante)),
):
    usuario_id = usuario_atual.id
    db.rollback()
    try:
        with db.begin():
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == requisicao_id)
                .with_for_update()
            )
            if requisicao is None:
                raise HTTPException(status_code=404, detail="OS não encontrada")
            if requisicao.usuario_solicitante_id != usuario_id:
                raise HTTPException(
                    status_code=403, detail="Você só pode fechar OS da sua conta"
                )
            if usuario_atual.setor_id != requisicao.setor_id:
                raise HTTPException(
                    status_code=403, detail="A OS pertence a outro setor"
                )
            if requisicao.status != StatusRequisicaoEnum.atendida:
                raise HTTPException(
                    status_code=409,
                    detail="A OS só pode ser fechada após a entrega dos materiais",
                )
            if requisicao.os_encerrada_at is not None:
                raise HTTPException(status_code=409, detail="Esta OS já foi fechada")

            itens = db.scalars(
                select(RequisicaoItem)
                .where(RequisicaoItem.requisicao_id == requisicao_id)
                .order_by(RequisicaoItem.material_id)
                .with_for_update()
            ).all()
            itens_entregues = {
                item.id: item for item in itens if item.quantidade_atendida > 0
            }
            sobras = {item.item_id: item.quantidade_sobrante for item in payload.itens}
            if len(sobras) != len(payload.itens) or set(sobras) != set(itens_entregues):
                raise HTTPException(
                    status_code=422,
                    detail="Informe uma quantidade sobrante para cada material entregue",
                )

            setor = db.scalar(
                select(Setor)
                .where(Setor.id == requisicao.setor_id)
                .with_for_update()
            )
            if setor is None:
                raise HTTPException(status_code=409, detail="Setor da OS não encontrado")
            material_ids = sorted({item.material_id for item in itens_entregues.values()})
            balances = db.scalars(
                select(EstoqueSetor)
                .where(
                    EstoqueSetor.setor_id == requisicao.setor_id,
                    EstoqueSetor.material_id.in_(material_ids),
                )
                .order_by(EstoqueSetor.material_id)
                .with_for_update()
            ).all() if material_ids else []
            balances_by_material = {balance.material_id: balance for balance in balances}

            ajustes = []
            for item_id, item in itens_entregues.items():
                sobra = sobras[item_id]
                if sobra > item.quantidade_atendida:
                    raise HTTPException(
                        status_code=422,
                        detail=f"A sobra do item {item_id} excede a quantidade entregue",
                    )
                balance = balances_by_material.get(item.material_id)
                if balance is None:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Saldo setorial do material {item.material_id} não encontrado",
                    )
                consumida = item.quantidade_atendida - sobra
                if balance.quantidade_atual < consumida:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Saldo insuficiente para reconciliar o fechamento do material {item.material_id}",
                    )
                ajustes.append((item, balance, sobra, consumida))

            for item, balance, sobra, consumida in ajustes:
                item.quantidade_sobrante = sobra
                if consumida <= 0:
                    continue
                anterior = balance.quantidade_atual
                posterior = anterior - consumida
                balance.quantidade_atual = posterior
                db.add(
                    MovimentacaoEstoqueSetor(
                        setor_id=requisicao.setor_id,
                        material_id=item.material_id,
                        usuario_id=usuario_id,
                        requisicao_id=requisicao.id,
                        tipo="CONSUMO_OS",
                        quantidade=consumida,
                        saldo_anterior=anterior,
                        saldo_posterior=posterior,
                        idempotency_key=f"os:{requisicao.id}:item:{item.id}:consumo",
                        observacao=f"Consumo no fechamento da OS {requisicao.numero}; sobra: {sobra}",
                    )
                )

            requisicao.os_encerrada_at = func.now()
            db.flush()
        return _detalhe(db, requisicao_id)
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao fechar OS") from exc


@router.patch("/{requisicao_id}/cancelar")
def cancelar_requisicao(
    requisicao_id: int,
    payload: CancelarRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(
            PerfilEnum.solicitante,
            PerfilEnum.almoxarife,
            PerfilEnum.admin,
        )
    ),
):
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    db.rollback()
    try:
        with db.begin():
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == requisicao_id)
                .with_for_update()
            )
            if requisicao is None:
                raise HTTPException(status_code=404, detail="Requisição não encontrada")
            if perfil == PerfilEnum.solicitante:
                if requisicao.usuario_solicitante_id != usuario_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Você só pode cancelar suas próprias requisições",
                    )
                allowed = {StatusRequisicaoEnum.pendente}
            else:
                allowed = {
                    StatusRequisicaoEnum.pendente,
                    StatusRequisicaoEnum.em_separacao,
                    StatusRequisicaoEnum.separada,
                }
            if requisicao.status not in allowed:
                raise HTTPException(
                    status_code=409,
                    detail="A requisição não pode ser cancelada neste estado",
                )
            if payload and payload.motivo:
                requisicao.observacao = _anexar_observacao(
                    requisicao.observacao, f"Cancelamento: {payload.motivo}"
                )
            itens = db.scalars(
                select(RequisicaoItem)
                .where(RequisicaoItem.requisicao_id == requisicao_id)
                .order_by(RequisicaoItem.material_id)
                .with_for_update()
            ).all()
            for item in itens:
                if item.quantidade_separada > 0:
                    estoque = buscar_estoque_para_update(item.material_id, db)
                    if estoque is None:
                        raise HTTPException(
                            status_code=409,
                            detail=f"Estoque do material {item.material_id} não encontrado",
                        )
                    anterior = estoque.quantidade_atual
                    posterior = anterior + item.quantidade_separada
                    estoque.quantidade_atual = posterior
                    estoque.data_ultima_movimentacao = func.now()
                    db.add(
                        MovimentacaoEstoque(
                            material_id=item.material_id,
                            usuario_id=usuario_id,
                            requisicao_id=requisicao_id,
                            tipo=TipoMovimentacaoEnum.devolucao,
                            quantidade=item.quantidade_separada,
                            estoque_anterior=anterior,
                            estoque_posterior=posterior,
                            observacao=f"Devolução por cancelamento da requisição {requisicao.numero}",
                        )
                    )
                    item.quantidade_separada = Decimal(0)
                    item.quantidade_atendida = Decimal(0)
                item.status = StatusRequisicaoItemEnum.cancelado
            requisicao.status = StatusRequisicaoEnum.cancelada
            notificar_usuario(db, requisicao.usuario_solicitante_id, f"requisicao:{requisicao.id}:cancelada", "STATUS", "Requisição cancelada", f"A requisição {requisicao.numero} foi cancelada.", requisicao.id)
            db.flush()
        return _detalhe(db, requisicao_id)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Conflito ao cancelar requisição"
        ) from exc


@router.patch("/{requisicao_id}/iniciar-separacao")
def iniciar_separacao(
    requisicao_id: int,
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
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == requisicao_id)
                .with_for_update()
            )
            if requisicao is None:
                raise HTTPException(status_code=404, detail="Requisição não encontrada")
            if requisicao.status != StatusRequisicaoEnum.pendente:
                separador = (
                    db.get(Usuario, requisicao.usuario_separador_id)
                    if requisicao.usuario_separador_id
                    else None
                )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensagem": "A requisição já foi iniciada ou não está PENDENTE",
                        "status": requisicao.status.value,
                        "iniciada_por": separador.nome if separador else None,
                    },
                )
            if perfil == PerfilEnum.almoxarife:
                atendimento = db.scalar(
                    select(AtendimentoAlmoxarifado)
                    .where(
                        AtendimentoAlmoxarifado.usuario_id == usuario_id,
                        AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
                    )
                    .order_by(AtendimentoAlmoxarifado.data_inicio.desc())
                    .with_for_update()
                )
                setor = db.get(Setor, requisicao.setor_id)
                if atendimento is None or atendimento.setor_id != requisicao.setor_id:
                    nome_setor = setor.nome if setor else str(requisicao.setor_id)
                    raise HTTPException(
                        status_code=409,
                        detail=f"Inicie um atendimento para o setor {nome_setor}",
                    )
            requisicao.status = StatusRequisicaoEnum.em_separacao
            requisicao.usuario_separador_id = usuario_id
            requisicao.data_inicio_separacao = func.now()
            notificar_usuario(db, requisicao.usuario_solicitante_id, f"requisicao:{requisicao.id}:separacao", "STATUS", "Requisição em separação", f"A requisição {requisicao.numero} está sendo separada.", requisicao.id)
            db.flush()
        return _detalhe(db, requisicao_id)
    except HTTPException:
        db.rollback()
        raise


@router.patch("/{requisicao_id}/concluir")
def concluir_requisicao(
    requisicao_id: int,
    payload: ConcluirRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
):
    if payload is None:
        payload = ConcluirRequest()
    db.rollback()
    try:
        with db.begin():
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == requisicao_id)
                .with_for_update()
            )
            if requisicao is None:
                raise HTTPException(status_code=404, detail="Requisição não encontrada")
            conclusao_parcial_em_andamento = (
                requisicao.status == StatusRequisicaoEnum.em_separacao
                and payload.permitir_parcial
            )
            if (
                requisicao.status != StatusRequisicaoEnum.separada
                and not conclusao_parcial_em_andamento
            ):
                raise HTTPException(
                    status_code=409,
                    detail="A requisição precisa estar SEPARADA para ser concluída",
                )
            itens = db.scalars(
                select(RequisicaoItem)
                .where(RequisicaoItem.requisicao_id == requisicao_id)
                .order_by(RequisicaoItem.material_id)
                .with_for_update()
            ).all()
            pendentes = [
                item
                for item in itens
                if item.status == StatusRequisicaoItemEnum.pendente
            ]
            if pendentes and not payload.permitir_parcial:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensagem": "Existem itens pendentes; envie permitir_parcial=true para concluir parcialmente",
                        "itens_pendentes": [
                            {
                                "id": item.id,
                                "material_id": item.material_id,
                                "quantidade_pendente": item.quantidade_solicitada
                                - item.quantidade_separada,
                            }
                            for item in pendentes
                        ],
                    },
                )
            for item in pendentes:
                quantidade_nao_separada = (
                    item.quantidade_solicitada - item.quantidade_separada
                )
                if item.quantidade_separada > 0:
                    item.status = StatusRequisicaoItemEnum.atendido
                    item.quantidade_atendida = item.quantidade_separada
                    item.observacao = _anexar_observacao(
                        item.observacao,
                        f"Atendido parcialmente; quantidade não separada: {quantidade_nao_separada}",
                    )
                else:
                    item.status = StatusRequisicaoItemEnum.cancelado
                    item.observacao = _anexar_observacao(
                        item.observacao,
                        "Não atendido na conclusão parcial da requisição",
                    )
            for item in itens:
                if item.status == StatusRequisicaoItemEnum.separado:
                    item.status = StatusRequisicaoItemEnum.atendido
                    item.quantidade_atendida = item.quantidade_separada
            setor = db.scalar(select(Setor).where(Setor.id == requisicao.setor_id).with_for_update())
            if setor is None:
                raise HTTPException(status_code=409, detail="Setor da requisição não encontrado")
            for item in itens:
                quantidade = item.quantidade_atendida or Decimal(0)
                if quantidade <= 0:
                    continue
                balance = db.scalar(select(EstoqueSetor).where(EstoqueSetor.setor_id == requisicao.setor_id, EstoqueSetor.material_id == item.material_id).with_for_update())
                if balance is None:
                    balance = EstoqueSetor(setor_id=requisicao.setor_id, material_id=item.material_id, quantidade_atual=Decimal(0))
                    db.add(balance)
                    db.flush()
                before = balance.quantidade_atual
                after = before + quantidade
                balance.quantidade_atual = after
                db.add(MovimentacaoEstoqueSetor(setor_id=requisicao.setor_id, material_id=item.material_id,
                    usuario_id=usuario_atual.id, requisicao_id=requisicao.id, tipo="ENTRADA_REQUISICAO",
                    quantidade=quantidade, saldo_anterior=before, saldo_posterior=after,
                    idempotency_key=f"requisicao:{requisicao.id}:item:{item.id}:entrada",
                    observacao=f"Atendimento da requisição {requisicao.numero}"))
            requisicao.status = StatusRequisicaoEnum.atendida
            requisicao.data_conclusao = func.now()
            notificar_usuario(db, requisicao.usuario_solicitante_id, f"requisicao:{requisicao.id}:atendida", "STATUS", "Requisição atendida", f"A requisição {requisicao.numero} foi concluída.", requisicao.id)
            db.flush()
        return _detalhe(db, requisicao_id)
    except HTTPException:
        db.rollback()
        raise
