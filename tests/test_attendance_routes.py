import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from core.security import get_current_user
from database.base import Base
from database.session import get_db
from models.atendimento_almoxarifado import (
    AtendimentoAlmoxarifado,
    StatusAtendimentoEnum,
)
from models.setor import Setor
from models.usuario import PerfilEnum, Usuario


@pytest.fixture
def attendance_api(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'attendance.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, base_url="http://localhost")
    with factory.begin() as db:
        current_sector = Setor(nome="Produção", codigo="PROD", ativo=True)
        next_sector = Setor(nome="Manutenção", codigo="MAN", ativo=True)
        inactive_sector = Setor(nome="Inativo", codigo="INA", ativo=False)
        user = Usuario(
            nome="Almoxarife",
            login="almox",
            senha_hash="x",
            perfil=PerfilEnum.almoxarife,
            ativo=True,
        )
        db.add_all([current_sector, next_sector, inactive_sector, user])
        db.flush()
        active = AtendimentoAlmoxarifado(
            usuario_id=user.id,
            setor_id=current_sector.id,
            status=StatusAtendimentoEnum.aberto,
        )
        db.add(active)
        db.flush()
        ids = {
            "user": user.id,
            "next_sector": next_sector.id,
            "inactive_sector": inactive_sector.id,
            "active_attendance": active.id,
        }
        current_user = user

    app.dependency_overrides[get_current_user] = lambda: current_user
    yield client, factory, ids
    client.close()
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    engine.dispose()


def test_switching_attendance_closes_old_and_opens_selected_sector(attendance_api):
    client, factory, ids = attendance_api

    response = client.post(
        "/atendimentos/trocar", json={"setor_id": ids["next_sector"]}
    )

    assert response.status_code == 200
    assert response.json()["setor_id"] == ids["next_sector"]
    with factory() as db:
        old = db.get(AtendimentoAlmoxarifado, ids["active_attendance"])
        rows = db.scalars(
            select(AtendimentoAlmoxarifado).where(
                AtendimentoAlmoxarifado.usuario_id == ids["user"],
                AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
            )
        ).all()
        assert old.status == StatusAtendimentoEnum.encerrado
        assert old.data_fim is not None
        assert len(rows) == 1
        assert rows[0].setor_id == ids["next_sector"]


def test_switching_to_inactive_sector_keeps_current_attendance(attendance_api):
    client, factory, ids = attendance_api

    response = client.post(
        "/atendimentos/trocar", json={"setor_id": ids["inactive_sector"]}
    )

    assert response.status_code == 404
    with factory() as db:
        active = db.get(AtendimentoAlmoxarifado, ids["active_attendance"])
        assert active.status == StatusAtendimentoEnum.aberto
        assert active.data_fim is None