from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from core.security import get_current_user
from database.base import Base
from database.session import get_db
from models.categoria import Categoria
from models.estoque import Estoque
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque
from models.requisicao import Requisicao, StatusRequisicaoEnum
from models.requisicao_item import RequisicaoItem, StatusRequisicaoItemEnum
from models.setor import Setor
from models.unidade_medida import UnidadeMedida
from models.usuario import PerfilEnum, Usuario


@pytest.fixture
def inventory_api():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    current_user = {"value": None}

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    def override_user():
        return current_user["value"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app, base_url="http://localhost") as client:
        yield client, factory, current_user
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    engine.dispose()


def seed_inventory(factory, estoque_atual: Decimal = Decimal(10)):
    with factory.begin() as db:
        categoria = Categoria(nome="Fixadores", codigo_prefixo="FX", ativo=True)
        unidade = UnidadeMedida(nome="Unidade", sigla="un", ativo=True)
        setor = Setor(nome="Produção", codigo="PROD", ativo=True)
        db.add_all([categoria, unidade, setor])
        db.flush()
        usuario_almox = Usuario(
            nome="Almoxarife", login="almox", senha_hash="x",
            perfil=PerfilEnum.almoxarife, ativo=True,
        )
        solicitante = Usuario(
            nome="Solicitante", login="solicitante", senha_hash="x",
            perfil=PerfilEnum.solicitante, ativo=True,
        )
        db.add_all([usuario_almox, solicitante])
        db.flush()
        material = Material(
            codigo="FX-001", descricao="Parafuso", categoria_id=categoria.id,
            unidade_medida_id=unidade.id, qr_code=str(uuid4()), ativo=True,
        )
        db.add(material)
        db.flush()
        estoque = Estoque(
            material_id=material.id,
            quantidade_atual=estoque_atual,
            estoque_minimo=Decimal(0),
        )
        requisicao = Requisicao(
            numero=f"REQ-{uuid4().hex[:10]}", setor_id=setor.id,
            usuario_solicitante_id=solicitante.id,
            status=StatusRequisicaoEnum.em_separacao,
        )
        db.add_all([estoque, requisicao])
        db.flush()
        item = RequisicaoItem(
            requisicao_id=requisicao.id,
            material_id=material.id,
            quantidade_solicitada=Decimal(5),
            quantidade_separada=Decimal(0),
            quantidade_atendida=Decimal(0),
            status=StatusRequisicaoItemEnum.pendente,
        )
        db.add(item)
        db.flush()
        return {
            "almoxarife_id": usuario_almox.id,
            "solicitante_id": solicitante.id,
            "setor_id": setor.id,
            "material_id": material.id,
            "estoque_id": estoque.id,
            "requisicao_id": requisicao.id,
            "item_id": item.id,
        }


def test_atendimento_nao_pode_ser_iniciado_duas_vezes(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    first = client.post("/atendimentos/iniciar", json={"setor_id": ids["setor_id"]})
    second = client.post("/atendimentos/iniciar", json={"setor_id": ids["setor_id"]})

    assert first.status_code == 201
    assert first.json()["status"] == "ABERTO"
    assert second.status_code == 409, second.text
    assert second.json()["detail"]["atendimento"]["id"] == first.json()["id"]


def test_separacao_parcial_depois_totaliza_e_nao_debita_duplicado(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    partial = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
        json={"quantidade": "2"},
    )
    completed = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
    )
    duplicate = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
    )

    assert partial.status_code == 200, partial.text
    assert partial.json()["item"]["status"] == "PENDENTE"
    assert completed.status_code == 200, completed.text
    assert Decimal(str(completed.json()["item"]["quantidade_separada"])) == Decimal(5)
    assert completed.json()["status_requisicao"] == "SEPARADA"
    assert duplicate.status_code == 409, duplicate.text

    with factory() as db:
        assert db.get(Estoque, ids["estoque_id"]).quantidade_atual == Decimal("5.000")
        assert db.query(MovimentacaoEstoque).count() == 2


def test_estoque_insuficiente_faz_rollback_completo(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory, Decimal(2))
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    response = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
    )

    assert response.status_code == 409, response.text
    assert Decimal(response.json()["detail"]["estoque_atual"]) == Decimal(2)
    with factory() as db:
        assert db.get(Estoque, ids["estoque_id"]).quantidade_atual == Decimal("2.000")
        assert db.get(RequisicaoItem, ids["item_id"]).quantidade_separada == Decimal("0.000")
        assert db.query(MovimentacaoEstoque).count() == 0


def test_ajuste_negativo_e_rejeitado_com_400(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    response = client.post("/movimentacoes", json={
        "material_id": ids["material_id"],
        "tipo": "AJUSTE",
        "quantidade": "-1",
        "observacao": "Correção de inventário",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "Dados inválidos"


def test_entrada_e_ajuste_usam_saldo_decimal_absoluto(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    entrada = client.post("/movimentacoes", json={
        "material_id": ids["material_id"], "tipo": "ENTRADA", "quantidade": "2.125",
    })
    ajuste_zero = client.post("/movimentacoes", json={
        "material_id": ids["material_id"], "tipo": "AJUSTE", "quantidade": "0",
        "observacao": "Inventário físico",
    })

    assert entrada.status_code == 201, entrada.text
    assert ajuste_zero.status_code == 201, ajuste_zero.text
    assert Decimal(str(ajuste_zero.json()["estoque_atual"])) == Decimal(0)
    assert Decimal(str(ajuste_zero.json()["quantidade"])) == Decimal("12.125")
    with factory() as db:
        assert db.get(Estoque, ids["estoque_id"]).quantidade_atual == Decimal("0.000")
