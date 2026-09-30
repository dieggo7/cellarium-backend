"""create controlled return workflow

Revision ID: 20260930_create_devolucoes
Revises: 20260930_expand_views_and_indexes
Create Date: 2026-09-30 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260930_create_devolucoes"
down_revision = "20260930_expand_views_and_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not any(column["name"] == "peso_unitario_g" for column in inspector.get_columns("materiais")):
        op.add_column("materiais", sa.Column("peso_unitario_g", sa.Numeric(12, 6), nullable=True))

    if not inspector.has_table("devolucoes"):
        op.create_table(
            "devolucoes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("requisicao_item_id", sa.Integer(), nullable=False),
            sa.Column("usuario_operador_id", sa.Integer(), nullable=False),
            sa.Column("usuario_analise_id", sa.Integer(), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("peso_total_g", sa.Numeric(12, 3), nullable=False),
            sa.Column("peso_unitario_g", sa.Numeric(12, 6), nullable=False),
            sa.Column("quantidade_calculada", sa.Numeric(12, 3), nullable=False),
            sa.Column(
                "status",
                sa.Enum("PENDENTE", "ACEITA", "REJEITADA", name="statusdevolucaoenum"),
                nullable=False,
                server_default="PENDENTE",
            ),
            sa.Column("observacao", sa.String(length=500), nullable=True),
            sa.Column("observacao_analise", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("analisada_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["requisicao_item_id"], ["requisicao_itens.id"], name="fk_devolucoes_item"),
            sa.ForeignKeyConstraint(["usuario_operador_id"], ["usuarios.id"], name="fk_devolucoes_operador"),
            sa.ForeignKeyConstraint(["usuario_analise_id"], ["usuarios.id"], name="fk_devolucoes_analise"),
            sa.CheckConstraint("peso_total_g > 0", name="chk_devolucoes_peso_positivo"),
            sa.CheckConstraint("peso_unitario_g > 0", name="chk_devolucoes_unidade_positiva"),
            sa.CheckConstraint("quantidade_calculada > 0", name="chk_devolucoes_quantidade_positiva"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key", name="uq_devolucoes_idempotency_key"),
        )
        op.create_index("idx_devolucoes_status_created", "devolucoes", ["status", "created_at"])
        op.create_index("idx_devolucoes_item", "devolucoes", ["requisicao_item_id"])


def downgrade() -> None:
    raise NotImplementedError(
        "O downgrade apagaria pesos cadastrados e o histórico de devoluções; faça a reversão "
        "somente após exportar e reconciliar esses dados."
    )
