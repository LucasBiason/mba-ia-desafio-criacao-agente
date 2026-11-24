"""Receipt regressions: faults after commit must not erase durable evidence."""

import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from services.agent.confirmations.ledger import ConfirmationRecord
from services.agent.runtime import portal_history as history
from services.agent.runtime.resident_actions import ProductActions
from services.agent.tools.reservation_read import SessionIdentity


class PendingReceiptTest(unittest.TestCase):
    def test_committed_decision_survives_pending_refresh_outage(self):
        actions = ProductActions(SessionIdentity(uuid4(), "owner"))
        actions._actor = MagicMock()
        ledger = MagicMock()
        ledger.decide.return_value = {
            "result": {"status": "reserved", "code": "RSV-safe"},
            "id": "confirmation",
        }
        actions._ledger = MagicMock(return_value=ledger)
        actions.pending = MagicMock(side_effect=OSError("offline"))
        reply = actions.decide("confirmation", True)
        self.assertIn("RSV-safe", reply["message"])
        self.assertTrue(reply["pending_refresh_failed"])
        ledger.decide.assert_called_once()

    def test_projection_keeps_commit_but_does_not_mask_revocation(self):
        actions = ProductActions(SessionIdentity(uuid4(), "owner"))
        actions.results = [{"status": "cancelled"}]
        actions.pending = MagicMock(side_effect=OSError("offline"))
        self.assertIn("cancelada", actions.message_projection("")["message"])
        actions.pending.side_effect = HTTPException(403, "revoked")
        with self.assertRaises(HTTPException):
            actions.message_projection("")


class LedgerRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_failed_append_after_existing_history_recovers_once_and_scopes_owner(
        self,
    ):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        for table in (
            history.PortalMessage.__table__,
            history.PortalArchive.__table__,
            ConfirmationRecord.__table__,
        ):
            table.create(engine)

        @contextmanager
        def transaction():
            with Session(engine) as session, session.begin():
                yield session

        db = SimpleNamespace(transaction=transaction)
        sid = str(uuid4())
        now = datetime.now(timezone.utc)
        with transaction() as session:
            session.add(
                history.PortalMessage(
                    id="old",
                    session_id=sid,
                    role="user",
                    content="earlier",
                    created_at=now - timedelta(seconds=5),
                )
            )
            for ident, owner, apt in [
                ("own", "owner", "101"),
                ("foreign", "other", "101"),
                ("unit", "owner", "302"),
            ]:
                session.add(
                    ConfirmationRecord(
                        id=ident,
                        session_id=sid,
                        resident_id=owner,
                        apartment=apt,
                        action="reservar_area",
                        payload={},
                        status="approved",
                        result={"status": "reserved", "code": "RSV-" + ident},
                        created_at=now - timedelta(seconds=1),
                        decided_at=now,
                    )
                )
        with (
            patch.object(history, "get_database", return_value=db),
            patch.object(history, "scope", return_value=("101", [sid])),
            patch.object(ProductActions, "pending", return_value=[]),
        ):
            page = await history.history(
                sid,
                {"id": "owner", "role": "resident", "active": True},
                None,
                include_pending=True,
            )
            self.assertEqual(
                sum("RSV-own" in row["content"] for row in page["messages"]), 1
            )
            self.assertNotIn("RSV-foreign", str(page))
            self.assertNotIn("RSV-unit", str(page))
            from unittest.mock import AsyncMock

            from google.genai import types

            receipt_event = SimpleNamespace(
                id="duplicate-source",
                author="reservas",
                timestamp=now.timestamp() + 0.01,
                content=types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                name="reservar_area",
                                response={"status": "reserved", "code": "RSV-own"},
                            )
                        )
                    ],
                ),
                is_final_response=lambda: True,
            )

            async def get_session(**kwargs):
                return (
                    SimpleNamespace(events=[receipt_event])
                    if kwargs["app_name"] == "aurora_resident_actions"
                    else None
                )

            duplicate = await history.history(
                sid,
                {"id": "owner", "role": "resident", "active": True},
                SimpleNamespace(get_session=AsyncMock(side_effect=get_session)),
                include_pending=True,
            )
            self.assertEqual(
                sum("RSV-own" in row["content"] for row in duplicate["messages"]), 1
            )
            history.append_message(
                sid, "assistant", "Reserva gravada. Código: RSV-own."
            )
            page = await history.history(
                sid,
                {"id": "owner", "role": "resident", "active": True},
                None,
                include_pending=True,
            )
            self.assertEqual(
                sum("RSV-own" in row["content"] for row in page["messages"]), 1
            )
            # A later identical decision must not absorb an earlier missing reply.
            later = datetime.now(timezone.utc) + timedelta(seconds=1)
            with transaction() as session:
                session.add(
                    ConfirmationRecord(
                        id="rejected-first",
                        session_id=sid,
                        resident_id="owner",
                        apartment="101",
                        action="reservar_area",
                        payload={},
                        status="rejected",
                        result=None,
                        created_at=now,
                        decided_at=now,
                    )
                )
                session.add(
                    ConfirmationRecord(
                        id="rejected-second",
                        session_id=sid,
                        resident_id="owner",
                        apartment="101",
                        action="reservar_area",
                        payload={},
                        status="rejected",
                        result=None,
                        created_at=later,
                        decided_at=later,
                    )
                )
                session.add(
                    history.PortalMessage(
                        id="normal-second",
                        session_id=sid,
                        role="assistant",
                        content="Pedido negado. Nenhuma alteração foi feita.",
                        created_at=later + timedelta(seconds=1),
                    )
                )
            page = await history.history(
                sid,
                {"id": "owner", "role": "resident", "active": True},
                None,
                include_pending=True,
            )
            self.assertEqual(
                sum("Pedido negado" in row["content"] for row in page["messages"]), 2
            )
        engine.dispose()


class AdkReceiptRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_adk_receipts_recover_after_transcript_without_duplicate_or_leak(
        self,
    ):
        from unittest.mock import AsyncMock

        from google.genai import types

        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        history.PortalMessage.__table__.create(engine)
        history.PortalArchive.__table__.create(engine)

        @contextmanager
        def transaction():
            with Session(engine) as session, session.begin():
                yield session

        sid = str(uuid4())
        start = datetime.now(timezone.utc) - timedelta(seconds=20)
        with transaction() as session:
            session.add(
                history.PortalMessage(
                    id="user",
                    session_id=sid,
                    role="user",
                    content="Pedido",
                    created_at=start,
                )
            )
            session.add(
                history.PortalMessage(
                    id="normal",
                    session_id=sid,
                    role="assistant",
                    content="Sua reserva foi cancelada.",
                    created_at=start + timedelta(seconds=6),
                )
            )

        def event(number, seconds, status, code=None):
            result = {"status": status, "private": "SECRET"}
            if code:
                result["code"] = code
            return SimpleNamespace(
                id=str(number),
                author="reservas",
                timestamp=(start + timedelta(seconds=seconds)).timestamp(),
                content=types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                name="reservar_area"
                                if status == "reserved"
                                else "cancelar_reserva",
                                response=result,
                            )
                        )
                    ],
                ),
                is_final_response=lambda: True,
            )

        events = [
            event(1, 2, "cancelled"),
            event(2, 5, "cancelled"),
            event(3, 8, "reserved", "RSV-safe"),
        ]

        async def get_session(**kwargs):
            self.assertEqual(kwargs["user_id"], "owner")
            self.assertEqual(kwargs["session_id"], sid)
            return (
                SimpleNamespace(events=events)
                if kwargs["app_name"] == "aurora_resident_actions"
                else None
            )

        service = SimpleNamespace(get_session=AsyncMock(side_effect=get_session))
        with (
            patch.object(
                history,
                "get_database",
                return_value=SimpleNamespace(transaction=transaction),
            ),
            patch.object(history, "scope", return_value=("101", [sid])),
        ):
            page = await history.history(sid, {"id": "owner"}, service)
            texts = [row["content"] for row in page["messages"]]
            self.assertEqual(
                texts,
                [
                    "Pedido",
                    "Sua reserva foi cancelada.",
                    "Sua reserva foi cancelada.",
                    "Reserva gravada. Código: RSV-safe.",
                ],
            )
            self.assertNotIn("SECRET", str(page))
            self.assertFalse(
                any(any(k.startswith("_") for k in row) for row in page["messages"])
            )
        engine.dispose()


class StructuredReceiptProjectionTest(unittest.TestCase):
    def test_new_executor_receipts_never_expose_internal_payloads(self):
        from google.genai import types

        now = datetime.now(timezone.utc).timestamp()
        events = []
        for index, (name, result) in enumerate(
            [
                (
                    "delegar_solicitacao",
                    {"operation": "reserve", "internal": "PRIVATE"},
                ),
                (
                    "executar_reserva_validada",
                    {"status": "reserved", "code": "RSV-safe", "internal": "PRIVATE"},
                ),
                (
                    "executar_convivencia_validada",
                    {"status": "authorized", "internal": "PRIVATE"},
                ),
            ]
        ):
            events.append(
                SimpleNamespace(
                    id=str(index),
                    author="reservas" if index != 2 else "convivencia",
                    timestamp=now + index,
                    content=types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=name, response=result
                                )
                            )
                        ],
                    ),
                    is_final_response=lambda: True,
                )
            )
        rows = history.public_events(events)
        self.assertEqual(
            [row["content"] for row in rows],
            [
                "Reserva gravada. Código: RSV-safe.",
                "A autorização do visitante foi gravada.",
            ],
        )
        self.assertNotIn("PRIVATE", str(rows))
        self.assertNotIn("operation", str(rows))


class StructuredSqlReceiptTest(unittest.IsolatedAsyncioTestCase):
    async def test_new_receipts_recover_across_single_item_pages_and_reopen(self):
        from pathlib import Path

        from google.adk.events import Event
        from google.adk.sessions import DatabaseSessionService
        from google.genai import types
        from sqlalchemy import event as sql_event
        from test_portal_work_bounds import BoundedHistoryTest

        from services.agent.models.portal_message import PortalMessage
        from services.agent.repositories.prepared_session_service import (
            PreparedSessionService,
        )

        # Same SQL fixture and pagination helper as the legacy receipt test;
        # this scenario targets the new executor names with no normal reply
        # for the first cancellation and for the committed reservation.
        await BoundedHistoryTest.asyncSetUp(self)
        self.pages = BoundedHistoryTest.pages.__get__(self)
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        sid = str(self.fixture.sid)
        with self.fixture.transaction() as session:
            session.add(
                PortalMessage(
                    id="question",
                    session_id=sid,
                    role="user",
                    content="Pedido",
                    created_at=start,
                )
            )
            session.add(
                PortalMessage(
                    id="normal",
                    session_id=sid,
                    role="assistant",
                    content="Sua reserva foi cancelada.",
                    created_at=start + timedelta(seconds=6),
                )
            )
        url = (
            f"sqlite+aiosqlite:///{Path(self.fixture.folder.name) / 'new-receipts.db'}"
        )
        writer = DatabaseSessionService(db_url=url)
        await writer.prepare_tables()
        session = await writer.create_session(
            app_name="aurora_resident_actions", user_id="owner", session_id=sid
        )
        for index, seconds, result in [
            (0, 2, {"status": "cancelled", "private": "PRIVATE"}),
            (1, 5, {"status": "cancelled", "private": "PRIVATE"}),
            (
                2,
                8,
                {"status": "reserved", "code": "RSV-new-safe", "private": "PRIVATE"},
            ),
        ]:
            await writer.append_event(
                session,
                Event(
                    id=f"new-receipt-{index}",
                    invocation_id=f"new-inv-{index}",
                    author="reservas",
                    timestamp=(start + timedelta(seconds=seconds)).timestamp(),
                    content=types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name="executar_reserva_validada", response=result
                                )
                            )
                        ],
                    ),
                ),
            )
        await writer.close()
        reader = PreparedSessionService(db_url=url)
        statements = []

        @sql_event.listens_for(reader.db_engine.sync_engine, "before_cursor_execute")
        def track(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        try:
            messages = await self.pages(reader, 1)
            self.assertEqual(
                [row["content"] for row in messages],
                [
                    "Pedido",
                    "Sua reserva foi cancelada.",
                    "Sua reserva foi cancelada.",
                    "Reserva gravada. Código: RSV-new-safe.",
                ],
            )
            self.assertEqual(len({row["id"] for row in messages}), 4)
            self.assertNotIn("PRIVATE", str(messages))
            event_reads = [query for query in statements if "FROM events" in query]
            self.assertTrue(event_reads)
            self.assertTrue(all("LIMIT" in query for query in event_reads))
            self.assertFalse(
                any(
                    query.lstrip().upper().startswith(("CREATE ", "ALTER ", "DROP "))
                    for query in statements
                )
            )
        finally:
            await reader.close()
