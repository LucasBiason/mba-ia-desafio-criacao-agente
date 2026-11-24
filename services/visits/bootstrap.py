"""Criação explícita das visitas com seus vínculos iniciais."""

from datetime import date

from sqlalchemy.orm import Session

from aurora_toolkit.data.bootstrap import initialize_tables
from aurora_toolkit.data.fixtures import initial_resident_id, read_json
from services.apartments.models.apartment import Apartment  # noqa: F401 - Registra destino da chave estrangeira.
from services.visits.models.visit import Visit


def seed_visits(session: Session) -> None:
    for row in read_json("visitantes.json"):
        session.add(
            Visit(
                apartment=row["apartamento"],
                resident_id=initial_resident_id(row["apartamento"]),
                name=row["nome"],
                date=date.fromisoformat(row["data"]),
            )
        )


def initialize() -> bool:
    return initialize_tables([Visit.__table__], seed_visits, lock_key=640204)
