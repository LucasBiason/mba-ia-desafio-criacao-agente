"""Criação explícita das áreas comuns e das taxas iniciais."""

from decimal import Decimal

from sqlalchemy.orm import Session

from aurora_toolkit.data.bootstrap import initialize_tables
from aurora_toolkit.data.fixtures import read_json
from services.common_areas.models.area import Area


def seed_areas(session: Session) -> None:
    for row in read_json("areas.json"):
        session.add(
            Area(
                id=row["id"],
                name=row["nome"],
                fee_cents=int(Decimal(row["taxa"]) * 100),
            )
        )


def initialize() -> bool:
    return initialize_tables([Area.__table__], seed_areas, lock_key=640202)
