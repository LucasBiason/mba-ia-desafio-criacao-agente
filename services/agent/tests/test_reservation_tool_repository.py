"""Query real em SQLite descartável: valida recorte, não constraints PostgreSQL."""

import unittest
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from services.agenda.models.reservation import Reservation
from services.agent.models.chat_session import ChatSession
from services.agent.repositories.reservation_tool_repository import (
    ReservationToolRepository,
)
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident
from services.common_areas.models.area import Area


class MemoryDatabase:
    def __init__(self, engine):
        self.engine = engine

    def session(self):
        return Session(self.engine, expire_on_commit=False)


class ReservationToolRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        # Fixture SQLite mínima. Não copia nem altera metadata/constraints do
        # produto, nem pretende provar locks ou unicidade do PostgreSQL.
        statements = (
            "CREATE TABLE apartments (number TEXT PRIMARY KEY, id BIGINT UNIQUE)",
            "CREATE TABLE apartment_residents (apartment_id BIGINT PRIMARY KEY, resident_id TEXT)",
            "CREATE TABLE areas (id TEXT PRIMARY KEY, name TEXT, fee_cents INTEGER)",
            "CREATE TABLE chat_sessions (id UUID PRIMARY KEY, apartment TEXT, resident_id TEXT, created_at DATETIME)",
            "CREATE TABLE reservations (code TEXT PRIMARY KEY, apartment TEXT, resident_id TEXT, area_id TEXT, date DATE, fee_cents INTEGER, status TEXT, start_time TIME, end_time TIME)",
        )
        self.session_id = uuid4()
        with self.engine.begin() as connection:
            for statement in statements:
                connection.exec_driver_sql(statement)
            connection.execute(
                Apartment.__table__.insert(),
                [
                    {"number": "101", "id": 1},
                    {"number": "102", "id": 2},
                    {"number": "302", "id": 3},
                ],
            )
            connection.execute(
                ApartmentResident.__table__.insert(),
                [
                    {"apartment_id": 1, "resident_id": "a"},
                    {"apartment_id": 2, "resident_id": "a"},
                    {"apartment_id": 3, "resident_id": "b"},
                ],
            )
            connection.execute(
                Area.__table__.insert(),
                {"id": "quadra", "name": "Quadra", "fee_cents": 0},
            )
            connection.execute(
                ChatSession.__table__.insert(),
                {
                    "id": self.session_id,
                    "apartment": "101",
                    "resident_id": "a",
                    "created_at": datetime.now(UTC),
                },
            )
            connection.execute(
                Reservation.__table__.insert(),
                [
                    {
                        "code": code,
                        "apartment": unit,
                        "resident_id": owner,
                        "area_id": "quadra",
                        "date": date(2030, 4, 6),
                        "fee_cents": 0,
                        "status": status,
                    }
                    for code, unit, owner, status in (
                        ("mine", "101", "a", "active"),
                        ("cancelled", "101", "a", "cancelled"),
                        ("other-unit", "102", "a", "active"),
                        ("foreign", "302", "b", "active"),
                    )
                ],
            )
        self.database = MemoryDatabase(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def read_codes(self, owner="a", session_id=None):
        with ReservationToolRepository(self.database) as repository:
            return [
                row[0].code
                for row in repository.active_reservations(
                    session_id or self.session_id, owner
                )
            ]

    def test_only_active_fixed_unit_even_when_owner_has_two_units(self):
        self.assertEqual(self.read_codes(), ["mine"])

    def test_foreign_owner_and_unknown_session_return_no_rows(self):
        self.assertEqual(self.read_codes(owner="b"), [])
        self.assertEqual(self.read_codes(session_id=uuid4()), [])

    def test_new_resident_session_does_not_inherit_former_resident_reservations(self):
        new_session = uuid4()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE apartment_residents SET resident_id = :owner WHERE apartment_id = 1"
                ),
                {"owner": "b"},
            )
            connection.execute(
                ChatSession.__table__.insert(),
                {
                    "id": new_session,
                    "apartment": "101",
                    "resident_id": "b",
                    "created_at": datetime.now(UTC),
                },
            )
            connection.execute(
                Reservation.__table__.insert(),
                {
                    "code": "new-owner",
                    "apartment": "101",
                    "resident_id": "b",
                    "area_id": "quadra",
                    "date": date(2030, 4, 7),
                    "fee_cents": 0,
                    "status": "active",
                },
            )
        self.assertEqual(
            self.read_codes(owner="b", session_id=new_session), ["new-owner"]
        )
        self.assertEqual(self.read_codes(), [])

    def test_ownership_revoked_before_query_does_not_leak_old_session(self):
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE apartment_residents SET resident_id = :owner WHERE apartment_id = 1"
                ),
                {"owner": "b"},
            )
        self.assertEqual(self.read_codes(), [])
        self.assertEqual(self.read_codes(owner="b"), [])


if __name__ == "__main__":
    unittest.main()
