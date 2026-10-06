"""Add sector stock ledger, request messages and notifications.

Revision ID: 20261006_live_requester_tabs
Revises: 20260930_create_devolucoes
"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "20261006_live_requester_tabs"
down_revision = "20260930_create_devolucoes"
branch_labels = None
depends_on = None

MYSQL_ID = mysql.INTEGER(unsigned=True)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("estoque_setor"):
        op.create_table(
            "estoque_setor",
            sa.Column("id", MYSQL_ID, primary_key=True, autoincrement=True),
            sa.Column("setor_id", MYSQL_ID, sa.ForeignKey("setores.id"), nullable=False),
            sa.Column("material_id", MYSQL_ID, sa.ForeignKey("materiais.id"), nullable=False),
            sa.Column("quantidade_atual", sa.Numeric(12, 3), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("setor_id", "material_id", name="uq_estoque_setor_material"),
        )
    if not inspector.has_table("movimentacoes_estoque_setor"):
        op.create_table(
            "movimentacoes_estoque_setor",
            sa.Column("id", MYSQL_ID, primary_key=True, autoincrement=True),
            sa.Column("setor_id", MYSQL_ID, sa.ForeignKey("setores.id"), nullable=False),
            sa.Column("material_id", MYSQL_ID, sa.ForeignKey("materiais.id"), nullable=False),
            sa.Column("usuario_id", MYSQL_ID, sa.ForeignKey("usuarios.id"), nullable=True),
            sa.Column("requisicao_id", MYSQL_ID, sa.ForeignKey("requisicoes.id"), nullable=True),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
            sa.Column("saldo_anterior", sa.Numeric(12, 3), nullable=False),
            sa.Column("saldo_posterior", sa.Numeric(12, 3), nullable=False),
            sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True),
            sa.Column("observacao", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if not inspector.has_table("mensagens_requisicao"):
        op.create_table(
            "mensagens_requisicao",
            sa.Column("id", MYSQL_ID, primary_key=True, autoincrement=True),
            sa.Column("requisicao_id", MYSQL_ID, sa.ForeignKey("requisicoes.id"), nullable=False),
            sa.Column("usuario_id", MYSQL_ID, sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("texto", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_mensagens_requisicao_requisicao_id", "mensagens_requisicao", ["requisicao_id"])
        op.create_index("ix_mensagens_requisicao_created_at", "mensagens_requisicao", ["created_at"])
    if not inspector.has_table("notificacoes"):
        op.create_table(
            "notificacoes",
            sa.Column("id", MYSQL_ID, primary_key=True, autoincrement=True),
            sa.Column("usuario_id", MYSQL_ID, sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("requisicao_id", MYSQL_ID, sa.ForeignKey("requisicoes.id"), nullable=True),
            sa.Column("event_key", sa.String(160), nullable=False),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("titulo", sa.String(150), nullable=False),
            sa.Column("mensagem", sa.Text(), nullable=False),
            sa.Column("lida", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("usuario_id", "event_key", name="uq_notificacao_usuario_evento"),
        )

    # Preserve already completed requests as opening balances without synthetic unread notices.
    stock = sa.table("estoque_setor", sa.column("setor_id", sa.Integer()), sa.column("material_id", sa.Integer()), sa.column("quantidade_atual", sa.Numeric(12, 3)), sa.column("updated_at", sa.DateTime()))
    ledger = sa.table("movimentacoes_estoque_setor", sa.column("setor_id", sa.Integer()), sa.column("material_id", sa.Integer()), sa.column("usuario_id", sa.Integer()), sa.column("requisicao_id", sa.Integer()), sa.column("tipo", sa.String()), sa.column("quantidade", sa.Numeric(12, 3)), sa.column("saldo_anterior", sa.Numeric(12, 3)), sa.column("saldo_posterior", sa.Numeric(12, 3)), sa.column("idempotency_key", sa.String()), sa.column("observacao", sa.String()))
    rows = bind.execute(sa.text("""
        SELECT r.setor_id, i.material_id,
               SUM(i.quantidade_atendida - COALESCE(d.quantidade_devolvida, 0)) AS quantidade,
               MIN(r.usuario_separador_id) AS usuario_id, MIN(r.id) AS requisicao_id
        FROM requisicoes r JOIN requisicao_itens i ON i.requisicao_id = r.id
        LEFT JOIN (
            SELECT requisicao_item_id, SUM(quantidade_calculada) AS quantidade_devolvida
            FROM devolucoes WHERE status = 'ACEITA' GROUP BY requisicao_item_id
        ) d ON d.requisicao_item_id = i.id
        WHERE r.status = 'ATENDIDA' AND i.quantidade_atendida > 0
        GROUP BY r.setor_id, i.material_id
        HAVING SUM(i.quantidade_atendida - COALESCE(d.quantidade_devolvida, 0)) > 0
    """)).mappings()
    for row in rows:
        exists = bind.execute(sa.select(sa.func.count()).select_from(stock).where(stock.c.setor_id == row["setor_id"], stock.c.material_id == row["material_id"])).scalar_one()
        if exists:
            continue
        amount = row["quantidade"]
        bind.execute(stock.insert().values(setor_id=row["setor_id"], material_id=row["material_id"], quantidade_atual=amount, updated_at=sa.func.now()))
        bind.execute(ledger.insert().values(setor_id=row["setor_id"], material_id=row["material_id"], usuario_id=row["usuario_id"], requisicao_id=row["requisicao_id"], tipo="SALDO_INICIAL_HISTORICO", quantidade=amount, saldo_anterior=0, saldo_posterior=amount, idempotency_key=f"historico:{row['setor_id']}:{row['material_id']}", observacao="Saldo recomposto a partir de requisições atendidas antes da ativação do estoque por setor"))


def downgrade() -> None:
    raise NotImplementedError("A reversão apagaria saldos, movimentos, mensagens e notificações; exporte e reconcilie os dados antes.")
