"""Offline adapter contracts; real PostgreSQL concurrency needs cluster tests."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from psycopg.pq import TransactionStatus
from services.agent.academic.postgres import PostgresAcademicDomain, PostgresConnection


class PostgresAdapterTest(unittest.TestCase):
    def test_parameters_remain_bound(self):
        raw = MagicMock()
        conn = PostgresConnection(raw)
        values = ("text with ? and %",)
        conn.execute("SELECT name FROM visitors WHERE name=?", values)
        raw.execute.assert_called_once_with(
            "SELECT name FROM visitors WHERE name=%s", values
        )
        raw.info.transaction_status = TransactionStatus.INTRANS
        self.assertTrue(conn.in_transaction)

    def test_explicit_postgres_uri_required(self):
        for value in (None, "", "sqlite:///domain.db"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PostgresAcademicDomain(value)

    def test_receipt_lock_precedes_lookup(self):
        conn = MagicMock()
        with patch(
            "services.agent.academic.postgres.AcademicDomain._once",
            return_value={"status": "reserved"},
        ) as once:
            result = PostgresAcademicDomain._once(
                conn, "101", "reserve", {}, "operation-1", lambda: None
            )
            conn.execute.assert_called_once_with(
                "SELECT pg_advisory_xact_lock(hashtextextended(?, 0))", ("operation-1",)
            )
            once.assert_called_once()
            self.assertEqual(result["status"], "reserved")

    def test_invalid_receipt_id_does_not_issue_sql(self):
        conn = MagicMock()
        with self.assertRaises(ValueError):
            PostgresAcademicDomain._once(conn, "101", "reserve", {}, "", lambda: None)
        conn.execute.assert_not_called()

    def test_postgres_insert_uses_one_conflict_clause(self):
        conn = MagicMock()
        conn.execute.return_value.rowcount = 1
        result = PostgresAcademicDomain._insert_reservation(
            conn, "101", "quadra", "2030-06-01"
        )
        statement, values = conn.execute.call_args.args
        self.assertEqual(statement.count("ON CONFLICT"), 1)
        self.assertEqual(values[1:], ("101", "quadra", "2030-06-01"))
        self.assertEqual(result["status"], "reserved")


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
                    "services.agent.academic.postgres.psycopg.AsyncConnection.connect",
                    new=AsyncMock(return_value=raw),
                ):
                    async with domain.try_session_turn("fixture-session") as acquired:
                        self.assertIs(acquired, expected)
                raw.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
