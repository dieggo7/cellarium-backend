from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from core.security import get_current_user, verify_password
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
def inventory_api(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'inventory.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE VIEW vw_estoque_atual AS
            SELECT m.codigo, m.descricao AS material, c.nome AS categoria, um.nome AS unidade,
                   e.quantidade_atual AS estoque_atual, e.estoque_minimo,
                   CASE WHEN e.quantidade_atual <= 0 THEN 'SEM_ESTOQUE'
                        WHEN e.quantidade_atual <= e.estoque_minimo THEN 'ESTOQUE_BAIXO'
                        ELSE 'NORMAL' END AS situacao,
                   e.id AS estoque_id, m.id AS material_id, m.categoria_id, e.estoque_maximo, e.lote,
                   e.localizacao_id, COALESCE(l.descricao, l.codigo) AS localizacao_descricao
            FROM materiais m JOIN categorias c ON c.id = m.categoria_id
            JOIN unidades_medida um ON um.id = m.unidade_medida_id
            JOIN estoque e ON e.material_id = m.id
            LEFT JOIN localizacoes l ON l.id = e.localizacao_id
            WHERE m.ativo = 1
        """)
        connection.exec_driver_sql("""
            CREATE VIEW vw_requisicoes_pendentes AS
            SELECT r.numero, s.nome AS setor, r.data_solicitacao AS data, r.status,
                   COUNT(ri.id) AS quantidade_itens, r.id AS requisicao_id, r.setor_id,
                   r.usuario_solicitante_id, r.usuario_separador_id, r.data_inicio_separacao
            FROM requisicoes r JOIN setores s ON s.id = r.setor_id
            LEFT JOIN requisicao_itens ri ON ri.requisicao_id = r.id
            WHERE r.status IN ('PENDENTE', 'EM_SEPARACAO', 'SEPARADA')
            GROUP BY r.id, r.numero, s.nome, r.data_solicitacao, r.status, r.setor_id,
                     r.usuario_solicitante_id, r.usuario_separador_id, r.data_inicio_separacao
        """)
        connection.exec_driver_sql("""
            CREATE VIEW vw_historico_movimentacoes AS
            SELECT me.created_at AS data, u.nome AS usuario, s.nome AS setor, m.descricao AS material,
                   me.tipo, me.quantidade, me.estoque_anterior, me.estoque_posterior,
                   me.id, me.material_id, me.usuario_id, me.requisicao_id, r.setor_id
            FROM movimentacoes_estoque me JOIN usuarios u ON u.id = me.usuario_id
            JOIN materiais m ON m.id = me.material_id
            LEFT JOIN requisicoes r ON r.id = me.requisicao_id
            LEFT JOIN setores s ON s.id = r.setor_id
        """)
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
    client = TestClient(app, base_url="http://localhost")
    yield client, factory, current_user
    client.close()
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
            perfil=PerfilEnum.solicitante, setor_id=setor.id, ativo=True,
        )
        admin = Usuario(
            nome="Administrador", login="admin", senha_hash="x",
            perfil=PerfilEnum.admin, ativo=True,
        )
        db.add_all([usuario_almox, solicitante, admin])
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
            "admin_id": admin.id,
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


def test_duas_separacoes_simultaneas_debitam_uma_vez(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)
    path = f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(client.patch, path) for _ in range(2)]
        responses = [future.result() for future in futures]

    assert sorted(response.status_code for response in responses) == [200, 409]
    with factory() as db:
        assert db.get(Estoque, ids["estoque_id"]).quantidade_atual == Decimal("5.000")
        assert db.query(MovimentacaoEstoque).count() == 1


def test_separacao_parcial_depois_totaliza_e_nao_debita_duplicado(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    partial = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
        json={"quantidade": "2"},
        headers={"Idempotency-Key": "partial-test-1"},
    )
    repeated_partial = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
        json={"quantidade": "2"},
        headers={"Idempotency-Key": "partial-test-1"},
    )
    completed = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
    )
    duplicate = client.patch(
        f"/requisicoes/{ids['requisicao_id']}/itens/{ids['item_id']}/separar",
    )

    assert partial.status_code == 200, partial.text
    assert repeated_partial.status_code == 409
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


def test_fluxo_requisicao_completo_e_numero_anual(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(
        id=ids["solicitante_id"], perfil=PerfilEnum.solicitante, setor_id=ids["setor_id"],
    )

    created = client.post("/requisicoes", json={
        "setor_id": 999,
        "observacao": "Urgente",
        "itens": [{"material_id": ids["material_id"], "quantidade_solicitada": "3"}],
    })
    assert created.status_code == 201, created.text
    assert created.json()["numero"].startswith("REQ-")
    assert created.json()["setor"]["id"] == ids["setor_id"]
    assert created.json()["status"] == "PENDENTE"
    requisicao_id = created.json()["id"]

    pendentes = client.get("/requisicoes/pendentes")
    assert pendentes.status_code == 200, pendentes.text
    assert requisicao_id in {item["requisicao_id"] for item in pendentes.json()["dados"]}

    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)
    atendimento = client.post("/atendimentos/iniciar", json={"setor_id": ids["setor_id"]})
    iniciar = client.patch(f"/requisicoes/{requisicao_id}/iniciar-separacao")
    separar = client.patch(f"/requisicoes/{requisicao_id}/itens/{created.json()['itens'][0]['id']}/separar")
    concluir = client.patch(f"/requisicoes/{requisicao_id}/concluir")

    assert atendimento.status_code == 201, atendimento.text
    assert iniciar.status_code == 200, iniciar.text
    assert separar.status_code == 200, separar.text
    assert separar.json()["status_requisicao"] == "SEPARADA"
    assert concluir.status_code == 200, concluir.text
    assert concluir.json()["status"] == "ATENDIDA"

    with factory() as db:
        assert db.get(Estoque, ids["estoque_id"]).quantidade_atual == Decimal("7.000")
        item = db.get(RequisicaoItem, created.json()["itens"][0]["id"])
        assert item.status == StatusRequisicaoItemEnum.atendido
        assert item.quantidade_atendida == Decimal("3.000")


def test_cancelamento_com_devolucao_e_idempotencia(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(
        id=ids["solicitante_id"], perfil=PerfilEnum.solicitante, setor_id=ids["setor_id"],
    )
    created = client.post("/requisicoes", json={
        "itens": [{"material_id": ids["material_id"], "quantidade_solicitada": "5"}],
    })
    requisicao_id = created.json()["id"]
    item_id = created.json()["itens"][0]["id"]

    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)
    client.post("/atendimentos/iniciar", json={"setor_id": ids["setor_id"]})
    started = client.patch(f"/requisicoes/{requisicao_id}/iniciar-separacao")
    partial = client.patch(
        f"/requisicoes/{requisicao_id}/itens/{item_id}/separar",
        json={"quantidade": "2"},
        headers={"Idempotency-Key": "cancel-partial-test-1"},
    )
    canceled = client.patch(f"/requisicoes/{requisicao_id}/cancelar", json={"motivo": "Mudança de prioridade"})
    repeated = client.patch(f"/requisicoes/{requisicao_id}/cancelar")

    assert started.status_code == 200, started.text
    assert partial.status_code == 200, partial.text
    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["status"] == "CANCELADA"
    assert repeated.status_code == 409
    with factory() as db:
        assert db.get(Estoque, ids["estoque_id"]).quantidade_atual == Decimal("10.000")
        assert db.query(MovimentacaoEstoque).count() == 2
        assert db.get(RequisicaoItem, item_id).status == StatusRequisicaoItemEnum.cancelado


def test_estoque_inicial_e_qr_legado_opcional(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    with factory.begin() as db:
        db.delete(db.get(Estoque, ids["estoque_id"]))
    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)

    created = client.post("/estoque", json={
        "material_id": ids["material_id"],
        "estoque_minimo": "1.250",
        "estoque_maximo": "20",
        "quantidade_inicial": "4.500",
    })
    assert created.status_code == 201, created.text
    assert Decimal(str(created.json()["estoque_atual"])) == Decimal("4.5")
    assert client.put(f"/estoque/{created.json()['estoque_id']}", json={"quantidade_atual": "8"}).status_code == 400
    stock_list = client.get("/estoque", params={
        "busca": "Parafuso", "categoria_id": 1, "situacao": "NORMAL",
    })
    assert stock_list.status_code == 200, stock_list.text
    assert stock_list.json()["total"] == 1

    current_user["value"] = SimpleNamespace(id=ids["admin_id"], perfil=PerfilEnum.admin)
    material = client.put(f"/materiais/{ids['material_id']}", json={"qr_code": None})
    assert material.status_code == 200, material.text
    assert material.json()["qr_code"] is None
    assert all("qrcode" not in path for path in app.openapi()["paths"])
    history = client.get("/movimentacoes", params={"material_id": ids["material_id"]})
    material_history = client.get(f"/materiais/{ids['material_id']}/movimentacoes")
    assert history.status_code == 200, history.text
    assert material_history.status_code == 200, material_history.text
    assert history.json()["total"] == 1
    assert history.json()["dados"][0]["material_id"] == ids["material_id"]

    with factory() as db:
        assert db.query(MovimentacaoEstoque).count() == 1
        assert db.query(MovimentacaoEstoque).one().observacao == "Saldo inicial"


def test_usuario_criado_e_atualizado_com_hash_sem_exposicao(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["admin_id"], perfil=PerfilEnum.admin)

    created = client.post("/usuarios", json={
        "nome": "Novo solicitante",
        "login": "novo.solicitante",
        "senha": "senha-segura",
        "perfil": "SOLICITANTE",
        "setor_id": ids["setor_id"],
    })
    assert created.status_code == 201, created.text
    assert "senha_hash" not in created.json()
    user_id = created.json()["id"]
    with factory() as db:
        first_hash = db.get(Usuario, user_id).senha_hash
        assert verify_password("senha-segura", first_hash)

    updated = client.put(f"/usuarios/{user_id}", json={"senha": "nova-senha-segura"})
    assert updated.status_code == 200, updated.text
    assert "senha_hash" not in updated.json()
    with factory() as db:
        new_hash = db.get(Usuario, user_id).senha_hash
        assert new_hash != first_hash
        assert verify_password("nova-senha-segura", new_hash)

    self_demote = client.put(f"/usuarios/{ids['admin_id']}", json={"perfil": "SOLICITANTE"})
    self_disable = client.delete(f"/usuarios/{ids['admin_id']}")
    assert self_demote.status_code == 409
    assert self_disable.status_code == 409


def test_filtros_catalogo_e_soft_delete_com_vinculo(inventory_api):
    client, factory, current_user = inventory_api
    ids = seed_inventory(factory)
    current_user["value"] = SimpleNamespace(id=ids["admin_id"], perfil=PerfilEnum.admin)

    created_category = client.post("/categorias", json={
        "nome": "Ferramentas especiais", "codigo_prefixo": "FE", "descricao": "Teste",
    })
    created_location = client.post("/localizacoes", json={
        "codigo": "A9-E1", "descricao": "Corredor A9", "corredor": "A9", "estante": "E1",
    })
    assert created_category.status_code == 201, created_category.text
    assert created_location.status_code == 201, created_location.text
    location_id = created_location.json()["id"]

    material = client.post("/materiais", json={
        "codigo": "FE-001", "descricao": "Ferramenta teste",
        "categoria_id": created_category.json()["id"],
        "unidade_medida_id": 1,
    })
    assert material.status_code == 201, material.text
    assert material.json()["qr_code"] is None
    filtered = client.get("/materiais", params={
        "busca": "ferramenta", "categoria_id": created_category.json()["id"], "ativo": True,
    })
    assert [item["id"] for item in filtered.json()] == [material.json()["id"]]

    current_user["value"] = SimpleNamespace(id=ids["almoxarife_id"], perfil=PerfilEnum.almoxarife)
    stock = client.put(f"/estoque/{ids['estoque_id']}", json={"localizacao_id": location_id})
    assert stock.status_code == 200, stock.text
    blocked = client.delete(f"/localizacoes/{location_id}")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["materiais_vinculados"] == 1

    cleared = client.put(f"/estoque/{ids['estoque_id']}", json={"localizacao_id": None})
    assert cleared.status_code == 200, cleared.text
    deleted = client.delete(f"/localizacoes/{location_id}")
    assert deleted.status_code == 200
    current_user["value"] = SimpleNamespace(id=ids["admin_id"], perfil=PerfilEnum.admin)
    category_deleted = client.delete(f"/categorias/{created_category.json()['id']}")
    assert category_deleted.status_code == 200
    assert client.get(f"/categorias/{created_category.json()['id']}").json()["ativo"] is False
