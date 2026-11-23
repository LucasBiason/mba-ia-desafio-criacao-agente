"""Dedicated PostgreSQL academic backend; never points at the portal implicitly.

Per-operation transaction locks cover receipt lookup, effect and receipt
insertion across workers without serializing unrelated domain writes. The partial unique
index is still the final reservation constraint, not an availability precheck.
"""

from contextlib import asynccontextmanager, contextmanager
from decimal import Decimal
import json
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.pq import TransactionStatus

from services.agent.academic.domain import AcademicDomain, _SCHEMA, _iso, _name

_WRITE_LOCK = 64021901


class PostgresConnection:
    """Small adapter for our constant, parameterized domain SQL only.

    This is not a SQL parser. Application queries may not contain literal '?' or
    '%' characters; user values are always separate bound parameters.
    """

    def __init__(self, raw):
        self.raw = raw

    @property
    def in_transaction(self):
        return self.raw.info.transaction_status == TransactionStatus.INTRANS

    def execute(self, statement, parameters=None):
        if parameters is None:
            return self.raw.execute(statement)
        return self.raw.execute(statement.replace("?", "%s"), parameters)

    def executemany(self, statement, parameters):
        cursor = self.raw.cursor()
        cursor.executemany(statement.replace("?", "%s"), parameters)
        return cursor


class PostgresAcademicDomain(AcademicDomain):
    """Same domain interface, with explicit DSN and an isolated public schema."""

    is_postgres = True

    def __init__(self, dsn: str):
        if not isinstance(dsn, str) or not dsn.startswith(
            ("postgresql://", "postgres://")
        ):
            raise ValueError(
                "An explicit PostgreSQL URI for a dedicated academic database is required."
            )
        self._dsn = dsn

    @asynccontextmanager
    async def try_session_turn(self, session_id: str):
        """Nonblocking cross-replica turn gate; no transaction spans LLM calls.

        Dedicated connection owns the session lock. Closing releases it on
        success, exception or cancellation; callers must reject a false result.
        """
        raw = await psycopg.AsyncConnection.connect(
            self._dsn, autocommit=True, row_factory=dict_row, connect_timeout=10
        )
        try:
            cursor = await raw.execute(
                "SELECT pg_try_advisory_lock(hashtextextended(%s, 1)) AS acquired",
                ("aurora-academic-session:" + session_id,),
            )
            row = await cursor.fetchone()
            # Without a positive acknowledgement, the caller must not run the turn.
            yield row is not None and row.get("acquired") is True
        finally:
            await raw.close()

    def _connect(self):
        return psycopg.connect(
            self._dsn,
            row_factory=dict_row,
            connect_timeout=10,
            options="-c search_path=public",
        )

    @contextmanager
    def connection(self, *, write=False):
        with self._connect() as raw:
            if not raw.execute(
                "SELECT version FROM academic_seed WHERE version=1"
            ).fetchone():
                raise RuntimeError("Academic database is not initialized.")
            yield PostgresConnection(raw)
            # psycopg context commits success, rolls back exceptions and closes.

    def initialize(self, fixtures: Path | str) -> bool:
        fixtures = Path(fixtures)

        def rows(name):
            return json.loads((fixtures / (name + ".json")).read_text(encoding="utf-8"))

        with self._connect() as raw:
            raw.execute("SELECT pg_advisory_xact_lock(%s)", (_WRITE_LOCK,))
            tables = {
                row["table_name"]
                for row in raw.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
            }
            if (
                "academic_seed" in tables
                and raw.execute(
                    "SELECT version FROM academic_seed WHERE version=1"
                ).fetchone()
            ):
                return False
            if tables:
                raise ValueError(
                    "Refusing initialization over an existing non-academic database."
                )
            conn = PostgresConnection(raw)
            for statement in _SCHEMA:
                # SQLite INTEGER PRIMARY KEY auto-generates IDs; PostgreSQL needs identity.
                conn.execute(
                    statement.replace(
                        "id INTEGER PRIMARY KEY, apartment",
                        "id BIGSERIAL PRIMARY KEY, apartment",
                    )
                )
            conn.executemany(
                "INSERT INTO apartments VALUES (?)",
                [(r["numero"],) for r in rows("apartamentos")],
            )
            conn.executemany(
                "INSERT INTO areas VALUES (?,?,?)",
                [
                    (r["id"], r["nome"], int(Decimal(str(r["taxa"])) * 100))
                    for r in rows("areas")
                ],
            )
            conn.executemany(
                "INSERT INTO reservations(code,apartment,area,day) VALUES (?,?,?,?)",
                [
                    (r["codigo"], r["apartamento"], r["area"], _iso(r["data"]))
                    for r in rows("reservas")
                ],
            )
            conn.executemany(
                "INSERT INTO visitors(apartment,name,day) VALUES (?,?,?)",
                [
                    (r["apartamento"], _name(r["nome"]), _iso(r["data"]))
                    for r in rows("visitantes")
                ],
            )
            conn.execute("INSERT INTO academic_seed VALUES (1)")
            return True

    @staticmethod
    def _once(conn, apartment, action, details, operation_id, effect):
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 256:
            raise ValueError("Trusted operation ID is required.")
        # The same ID must serialize even if another caller supplies a different
        # apartment/payload. READ COMMITTED sees its receipt after acquiring lock.
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(?, 0))", (operation_id,)
        )
        return AcademicDomain._once(
            conn, apartment, action, details, operation_id, effect
        )

    @staticmethod
    def _insert_reservation(conn, apartment, area, day):
        for _ in range(3):
            code = "RSV-" + uuid4().hex.upper()
            cursor = conn.execute(
                """INSERT INTO reservations(code,apartment,area,day)
                VALUES (?,?,?,?) ON CONFLICT DO NOTHING""",
                (code, apartment, area, day),
            )
            if cursor.rowcount:
                return {"status": "reserved", "codigo": code, "area": area, "data": day}
            if not AcademicDomain._available(conn, area, day):
                return {"status": "occupied"}
        raise RuntimeError("Could not generate a unique reservation code.")
