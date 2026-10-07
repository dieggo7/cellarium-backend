"""Persist service-order closure and leftover quantities."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_close_service_orders"
down_revision = "20261006_history_request_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    request_columns = {column["name"] for column in inspector.get_columns("requisicoes")}
    item_columns = {column["name"] for column in inspector.get_columns("requisicao_itens")}

    if "os_encerrada_at" not in request_columns:
        op.add_column("requisicoes", sa.Column("os_encerrada_at", sa.DateTime(), nullable=True))
    if "quantidade_sobrante" not in item_columns:
        op.add_column("requisicao_itens", sa.Column("quantidade_sobrante", sa.Numeric(12, 3), nullable=True))

def downgrade() -> None:
    raise NotImplementedError(
        "A reversão apagaria o histórico de fechamento e sobras das OS."
    )
