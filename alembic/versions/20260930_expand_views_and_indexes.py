"""expand views and indexes

Revision ID: 20260930_expand_views_and_indexes
Revises: 20260924_create_users_table
Create Date: 2026-09-30 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260930_expand_views_and_indexes"
down_revision = "20260924_create_users_table"
branch_labels = None
depends_on = None


def _table_has_unique_constraint(bind: sa.engine.Connection, table_name: str, columns: list[str]) -> bool:
    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints(table_name):
        constraint_columns = constraint.get("column_names", [])
        if set(constraint_columns) == set(columns):
            return True
    return False


def _table_has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_has_columns(bind: sa.engine.Connection, table_name: str, columns: list[str]) -> bool:
    inspector = sa.inspect(bind)
    return any(index.get("column_names") == columns for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_has_column(bind, "movimentacoes_estoque", "idempotency_key"):
        op.add_column("movimentacoes_estoque", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    if not _table_has_unique_constraint(bind, "movimentacoes_estoque", ["idempotency_key"]):
        op.create_unique_constraint(
            "uq_mov_idempotency_key", "movimentacoes_estoque", ["idempotency_key"]
        )

    if not _table_has_column(bind, "materiais", "qr_code"):
        op.add_column("materiais", sa.Column("qr_code", sa.CHAR(length=36), nullable=True))
    elif not next(
        column["nullable"]
        for column in sa.inspect(bind).get_columns("materiais")
        if column["name"] == "qr_code"
    ):
        op.alter_column(
            "materiais",
            "qr_code",
            existing_type=sa.CHAR(length=36),
            nullable=True,
            existing_nullable=False,
        )
    if not _table_has_unique_constraint(bind, "materiais", ["qr_code"]):
        op.create_unique_constraint("uq_materiais_qrcode", "materiais", ["qr_code"])

    if not _table_has_unique_constraint(bind, "estoque", ["material_id"]):
        op.create_unique_constraint("uq_estoque_material", "estoque", ["material_id"])
    if not _table_has_unique_constraint(bind, "requisicoes", ["numero"]):
        op.create_unique_constraint("uq_requisicoes_numero", "requisicoes", ["numero"])
    if not _table_has_unique_constraint(bind, "localizacoes", ["codigo"]):
        op.create_unique_constraint("uq_localizacoes_codigo", "localizacoes", ["codigo"])
    if not _table_has_unique_constraint(bind, "usuarios", ["login"]):
        op.create_unique_constraint("uq_usuarios_login", "usuarios", ["login"])

    if not _index_has_columns(bind, "movimentacoes_estoque", ["material_id", "created_at"]):
        op.create_index(
            "idx_mov_material_created",
            "movimentacoes_estoque",
            ["material_id", "created_at"],
        )
    if not _index_has_columns(bind, "requisicoes", ["status", "setor_id"]):
        op.create_index("idx_requisicoes_status_setor", "requisicoes", ["status", "setor_id"])
    if not _index_has_columns(bind, "requisicao_itens", ["requisicao_id"]):
        op.create_index("idx_requisicao_itens_requisicao", "requisicao_itens", ["requisicao_id"])

    op.execute(
        """
        CREATE OR REPLACE VIEW vw_estoque_atual AS
        SELECT
            m.codigo,
            m.descricao AS material,
            c.nome AS categoria,
            um.nome AS unidade,
            e.quantidade_atual AS estoque_atual,
            e.estoque_minimo,
            CASE
                WHEN e.quantidade_atual <= 0 THEN 'SEM_ESTOQUE'
                WHEN e.quantidade_atual <= e.estoque_minimo THEN 'ESTOQUE_BAIXO'
                ELSE 'NORMAL'
            END AS situacao,
            e.id AS estoque_id,
            m.id AS material_id,
            m.categoria_id,
            e.estoque_maximo,
            e.lote,
            e.localizacao_id,
            COALESCE(
                NULLIF(l.descricao, ''),
                NULLIF(CONCAT_WS(' - ', l.corredor, l.estante, l.prateleira, l.posicao), ''),
                l.codigo
            ) AS localizacao_descricao
        FROM materiais m
        JOIN categorias c ON c.id = m.categoria_id
        JOIN unidades_medida um ON um.id = m.unidade_medida_id
        JOIN estoque e ON e.material_id = m.id
        LEFT JOIN localizacoes l ON l.id = e.localizacao_id
        WHERE m.ativo = 1
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW vw_requisicoes_pendentes AS
        SELECT
            r.numero,
            s.nome AS setor,
            r.data_solicitacao AS data,
            r.status,
            COUNT(ri.id) AS quantidade_itens,
            r.id AS requisicao_id,
            r.setor_id,
            r.usuario_solicitante_id,
            r.usuario_separador_id,
            r.data_inicio_separacao
        FROM requisicoes r
        JOIN setores s ON s.id = r.setor_id
        LEFT JOIN requisicao_itens ri ON ri.requisicao_id = r.id
        WHERE r.status IN ('PENDENTE', 'EM_SEPARACAO', 'SEPARADA')
        GROUP BY
            r.id,
            r.numero,
            s.nome,
            r.data_solicitacao,
            r.status,
            r.setor_id,
            r.usuario_solicitante_id,
            r.usuario_separador_id,
            r.data_inicio_separacao
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW vw_historico_movimentacoes AS
        SELECT
            me.created_at AS data,
            u.nome AS usuario,
            s.nome AS setor,
            m.descricao AS material,
            me.tipo,
            me.quantidade,
            me.estoque_anterior,
            me.estoque_posterior,
            me.id,
            me.material_id,
            me.usuario_id,
            me.requisicao_id,
            r.setor_id
        FROM movimentacoes_estoque me
        JOIN usuarios u ON u.id = me.usuario_id
        JOIN materiais m ON m.id = me.material_id
        LEFT JOIN requisicoes r ON r.id = me.requisicao_id
        LEFT JOIN setores s ON s.id = r.setor_id
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Esta migration reconcilia objetos preexistentes; reverta manualmente após identificar "
        "quais objetos foram criados por ela."
    )
