"""Criação explícita das reservas com os vínculos e valores da fonte."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from aurora_toolkit.data.bootstrap import initialize_tables
from aurora_toolkit.data.fixtures import initial_resident_id, read_json
from services.agenda.models.agenda_seed import AgendaSeed
from services.agenda.models.reservation import Reservation
from services.apartments.models.apartment import Apartment  # noqa: F401 - Registra destino da chave estrangeira.
from services.common_areas.models.area import Area


def seed_reservations(session: Session) -> None:
    fees = dict(session.execute(select(Area.id, Area.fee_cents)).all())
    for row in read_json("reservas.json"):
        if row["area"] not in fees:
            raise RuntimeError(
                f"Área comum da reserva inicial não cadastrada: {row['area']}."
            )
        session.add(
            Reservation(
                code=row["codigo"],
                apartment=row["apartamento"],
                resident_id=initial_resident_id(row["apartamento"]),
                area_id=row["area"],
                date=date.fromisoformat(row["data"]),
                fee_cents=fees[row["area"]],
                status="active",
            )
        )


def initialize() -> bool:
    return initialize_tables(
        [Reservation.__table__, AgendaSeed.__table__],
        seed_reservations,
        lock_key=640203,
    )
