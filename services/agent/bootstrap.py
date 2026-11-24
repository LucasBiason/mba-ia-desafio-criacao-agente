"""Preparação explícita do portal; o servidor HTTP não cria tabelas."""

from sqlalchemy import select, Table
from typing import cast
from aurora_toolkit.data.bootstrap import initialize_tables
from microservice_toolkit import get_database
from services.agent.models.chat_session import ChatSession
from services.agent.models.portal_message import PortalMessage
from services.agent.models.portal_archive import PortalArchive
from services.agent.models.confirmation_record import ConfirmationRecord
from services.agent.models.admission_gate import AdmissionGate
from services.agent.models.admission_lease import AdmissionLease
from services.apartments.models.apartment import Apartment  # noqa: F401


def initialize() -> bool:
    created = initialize_tables(
        [
            cast(Table, model.__table__)
            for model in (
                ChatSession,
                PortalMessage,
                PortalArchive,
                ConfirmationRecord,
                AdmissionGate,
                AdmissionLease,
            )
        ],
        lock_key=640206,
    )
    with get_database().transaction() as session:
        # The explicit bootstrap may run concurrently; serialize the singleton.
        from sqlalchemy import func

        session.execute(select(func.pg_advisory_xact_lock(640206)))
        # Existing tables keep their rows/columns; prepare only missing indexes.
        for model in (PortalMessage, ConfirmationRecord, AdmissionLease):
            for index in cast(Table, model.__table__).indexes:
                index.create(session.connection(), checkfirst=True)
        if session.get(AdmissionGate, 1) is None:
            session.add(AdmissionGate(id=1, revision=0))
    return created


def initialize_sessions(database_url: str) -> None:
    """Prepara o banco dedicado ADK explicitamente, sem ler credencial do modelo."""
    import asyncio
    from google.adk.sessions import DatabaseSessionService

    if (
        not database_url.startswith(
            ("sqlite+aiosqlite:///", "postgresql+asyncpg://", "postgresql+psycopg://")
        )
        or ":memory:" in database_url
    ):
        raise ValueError(
            "Configure persistência assíncrona dedicada em disco para o ADK."
        )

    async def prepare():
        service = DatabaseSessionService(db_url=database_url)
        try:
            await service.prepare_tables()
        finally:
            await service.close()

    asyncio.run(prepare())
