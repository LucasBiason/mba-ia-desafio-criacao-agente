"""Backend PostgreSQL isolado, com locks de sessão e recibo entre réplicas."""

from contextlib import asynccontextmanager

import psycopg
from psycopg.rows import dict_row
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from ..domain import AcademicDomain


class PostgresAcademicDomain(AcademicDomain):
    is_postgres = True

    def __init__(self, dsn: str):
        if not isinstance(dsn, str) or not dsn.startswith(
            ("postgresql://", "postgres://")
        ):
            raise ValueError(
                "An explicit PostgreSQL URI for a dedicated academic database is required."
            )
        self._dsn = dsn

    def _engine(self, *, create=False):
        return create_engine(
            "postgresql+psycopg://" + self._dsn.split("://", 1)[1],
            poolclass=NullPool,
            connect_args={"connect_timeout": 10, "options": "-c search_path=public"},
        )

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

    @staticmethod
    def _once(work, apartment, action, details, operation_id, effect):
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 256:
            raise ValueError("Trusted operation ID is required.")
        work.orm.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:operation_id, 0))"),
            {"operation_id": operation_id},
        )
        return AcademicDomain._once(
            work, apartment, action, details, operation_id, effect
        )
