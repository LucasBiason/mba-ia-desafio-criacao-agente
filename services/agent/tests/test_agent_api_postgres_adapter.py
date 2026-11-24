"""Offline adapter contracts; real PostgreSQL concurrency needs cluster tests."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

from services.agent.api.domain import AcademicDomain
from services.agent.api.postgres import PostgresAcademicDomain


class PostgresAdapterTest(unittest.TestCase):
    def test_operation_identity_remains_bound(self):
        work = MagicMock()
        value = "identity with ' ? % and ;"
        with patch(
            "services.agent.api.repositories.postgres_academic_repository.AcademicDomain._once"
        ):
            PostgresAcademicDomain._once(
                work, "101", "reserve", {}, value, lambda: None
            )
        statement, parameters = work.orm.execute.call_args.args
        self.assertNotIn(value, str(statement))
        self.assertEqual(parameters, {"operation_id": value})

    def test_explicit_postgres_uri_required(self):
        for value in (None, "", "sqlite:///domain.db"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PostgresAcademicDomain(value)

    def test_receipt_lock_precedes_lookup(self):
        conn = MagicMock()
        with patch(
            "services.agent.api.repositories.postgres_academic_repository.AcademicDomain._once",
            return_value={"status": "reserved"},
        ) as once:
            result = PostgresAcademicDomain._once(
                conn, "101", "reserve", {}, "operation-1", lambda: None
            )
            statement, parameters = conn.orm.execute.call_args.args
            self.assertIn("pg_advisory_xact_lock", str(statement))
            self.assertEqual(parameters, {"operation_id": "operation-1"})
            once.assert_called_once()
            self.assertEqual(result["status"], "reserved")

    def test_invalid_receipt_id_does_not_issue_sql(self):
        conn = MagicMock()
        with self.assertRaises(ValueError):
            PostgresAcademicDomain._once(conn, "101", "reserve", {}, "", lambda: None)
        conn.orm.execute.assert_not_called()

    def test_conflicting_insert_preserves_outer_transaction(self):
        with TemporaryDirectory() as folder:
            domain = AcademicDomain(Path(folder) / "domain.db")
            domain.initialize(Path(__file__).resolve().parents[3] / "dados")
            with domain.connection(write=True) as work:
                self.assertEqual(
                    domain._insert_reservation(work, "101", "quadra", "2030-03-09"),
                    {"status": "occupied"},
                )
                result = domain._insert_reservation(work, "101", "quadra", "2030-06-01")
                self.assertEqual(result["status"], "reserved")
            self.assertEqual(len(domain.reservations("101")), 2)


class PostgresAdvisoryLockTest(unittest.IsolatedAsyncioTestCase):
    async def test_turn_requires_explicit_positive_lock_and_closes_connection(self):
        domain = PostgresAcademicDomain("postgresql://local.invalid/aurora")
        for row, expected in (
            (None, False),
            ({}, False),
            ({"acquired": False}, False),
            ({"acquired": True}, True),
        ):
            with self.subTest(row=row):
                cursor = MagicMock()
                cursor.fetchone = AsyncMock(return_value=row)
                raw = MagicMock()
                raw.execute = AsyncMock(return_value=cursor)
                raw.close = AsyncMock()
                with patch(
                    "services.agent.api.repositories.postgres_academic_repository.psycopg.AsyncConnection.connect",
                    new=AsyncMock(return_value=raw),
                ):
                    async with domain.try_session_turn("fixture-session") as acquired:
                        self.assertIs(acquired, expected)
                raw.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
