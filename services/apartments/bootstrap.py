"""Criação explícita dos apartamentos e de seus responsáveis iniciais."""

from sqlalchemy.orm import Session

from aurora_toolkit.data.bootstrap import initialize_tables
from aurora_toolkit.data.fixtures import initial_resident_id, read_json
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident


def seed_apartments(session: Session) -> None:
    for row in read_json("apartamentos.json"):
        apartment = Apartment(number=row["numero"])
        session.add(apartment)
        session.flush()
        session.add(
            ApartmentResident(
                apartment_id=apartment.id,
                resident_id=initial_resident_id(apartment.number),
            )
        )


def initialize() -> bool:
    return initialize_tables(
        [Apartment.__table__, ApartmentResident.__table__],
        seed_apartments,
        lock_key=640201,
    )
