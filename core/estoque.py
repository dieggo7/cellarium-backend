from sqlalchemy import select
from sqlalchemy.orm import Session

from models.estoque import Estoque


def buscar_estoque_para_update(material_id: int, db: Session) -> Estoque | None:
    """Retorna e bloqueia o único registro de estoque do material."""
    return db.scalar(
        select(Estoque)
        .where(Estoque.material_id == material_id)
        .with_for_update()
    )