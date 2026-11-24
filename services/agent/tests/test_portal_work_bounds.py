"""Regressões de SQL/ADK reais em bancos descartáveis, sem provedor externo."""

import asyncio
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aurora_toolkit.identity import authenticated_user, verify_internal
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from google.adk.events import Event
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from services.agent.models.admission_gate import AdmissionGate
from services.agent.models.admission_lease import AdmissionLease
from services.agent.models.chat_session import ChatSession
from services.agent.models.confirmation_record import ConfirmationRecord
from services.agent.models.portal_archive import PortalArchive
from services.agent.models.portal_message import PortalMessage
from services.agent.models.session_identity import SessionIdentity
from services.agent.repositories.admission_repository import AdmissionRepository
from services.agent.repositories.chat_repository import ChatRepository
from services.agent.repositories.prepared_session_service import PreparedSessionService
from services.agent.routers.chat_router import router
from services.agent.runtime import portal_history
from services.agent.runtime.message_handler import ReadOnlyMessageHandler
from services.agent.schemas.internal_message import InternalMessage


class PortalFixture:
    def __init__(self):
        self.folder = tempfile.TemporaryDirectory()
        self.engine = create_engine(
            f"sqlite:///{Path(self.folder.name) / 'portal.db'}",
            connect_args={"check_same_thread": False, "timeout": 15},
        )
        with self.engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE apartments (number TEXT PRIMARY KEY, id BIGINT UNIQUE)"
            )
            conn.exec_driver_sql(
                "CREATE TABLE apartment_residents (apartment_id BIGINT PRIMARY KEY, resident_id TEXT)"
            )
            conn.exec_driver_sql("INSERT INTO apartments VALUES ('101',1),('302',2)")
            conn.exec_driver_sql(
                "INSERT INTO apartment_residents VALUES (1,'owner'),(2,'other')"
            )
        self.sid = uuid4()
        self.legacy = uuid4()
        self.foreign = uuid4()
        for model in (
            ChatSession,
            PortalMessage,
            PortalArchive,
            ConfirmationRecord,
            AdmissionGate,
            AdmissionLease,
        ):
            model.__table__.create(self.engine)
        with self.transaction() as session:
            for sid, actor, apartment, days in (
                (self.sid, "owner", "101", 0),
                (self.legacy, "owner", "101", 1),
                (self.foreign, "other", "302", 0),
            ):
                session.add(
                    ChatSession(
                        id=sid,
                        apartment=apartment,
                        resident_id=actor,
                        created_at=datetime.now(timezone.utc) - timedelta(days=days),
                    )
                )
            session.add(AdmissionGate(id=1, revision=0))
        self.actor = {"id": "owner", "role": "resident", "active": True}

    def session(self):
        return Session(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self):
        with self.session() as session, session.begin():
            yield session

    def close(self):
        self.engine.dispose()
        self.folder.cleanup()

    def repo(self):
        return ChatRepository(self)


class BoundedHistoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = PortalFixture()
        self.addCleanup(self.fixture.close)
        self.enterContext(
            patch.object(portal_history, "get_database", return_value=self.fixture)
        )
        self.enterContext(
            patch.object(
                portal_history, "ChatRepository", side_effect=self.fixture.repo
            )
        )

    async def pages(self, service=None, limit=17):
        cursor = None
        result = []
        for _ in range(40):
            page = await portal_history.history(
                self.fixture.sid,
                self.fixture.actor,
                service,
                limit=limit,
                before=cursor,
            )
            self.assertLessEqual(len(page["messages"]), limit)
            result = page["messages"] + result
            if not page["next_cursor"]:
                return result
            self.assertNotEqual(cursor, page["next_cursor"])
            cursor = page["next_cursor"]
        self.fail("O cursor não atingiu o fim do histórico.")

    async def test_120_sql_messages_are_limited_before_materialization_and_keep_legacy_scope(
        self,
    ):
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with self.fixture.transaction() as session:
            for index in range(120):
                session.add(
                    PortalMessage(
                        id=f"own-{index:03}",
                        session_id=str(
                            self.fixture.sid if index >= 60 else self.fixture.legacy
                        ),
                        role="user",
                        content=f"public-{index}",
                        created_at=start + timedelta(seconds=index),
                    )
                )
                session.add(
                    PortalMessage(
                        id=f"foreign-{index:03}",
                        session_id=str(self.fixture.foreign),
                        role="user",
                        content="PRIVATE",
                        created_at=start + timedelta(seconds=index),
                    )
                )
        statements = []

        @event.listens_for(self.fixture.engine, "before_cursor_execute")
        def track(conn, cursor, statement, parameters, context, many):
            if statement.startswith("SELECT agent_portal_messages.id"):
                statements.append((statement, parameters))

        messages = await self.pages()
        self.assertEqual(
            [row["content"] for row in messages], [f"public-{i}" for i in range(120)]
        )
        self.assertEqual(
            {row["sourceSessionId"] for row in messages},
            {str(self.fixture.sid), str(self.fixture.legacy)},
        )
        self.assertTrue(statements)
        self.assertTrue(all("LIMIT" in statement for statement, _ in statements))
        self.assertTrue(all(18 in parameters for _, parameters in statements))

    async def test_120_adk_events_paginate_in_sql_and_survive_new_service(self):
        url = f"sqlite+aiosqlite:///{Path(self.fixture.folder.name) / 'adk.db'}"
        writer = DatabaseSessionService(db_url=url)
        await writer.prepare_tables()
        session = await writer.create_session(
            app_name="aurora_read_probe",
            user_id="owner",
            session_id=str(self.fixture.legacy),
        )
        for index in range(120):
            await writer.append_event(
                session,
                Event(
                    id=f"event-{index:03}",
                    invocation_id=f"inv-{index}",
                    author="user",
                    timestamp=1700000000 + index,
                    content=types.Content(
                        role="user", parts=[types.Part(text=f"adk-{index}")]
                    ),
                ),
            )
        await writer.close()
        reader = PreparedSessionService(db_url=url)
        statements = []

        @event.listens_for(reader.db_engine.sync_engine, "before_cursor_execute")
        def track(conn, cursor, statement, parameters, context, many):
            if "FROM events" in statement:
                statements.append((statement, parameters))

        try:
            messages = await self.pages(reader)
            self.assertEqual(
                [row["content"] for row in messages], [f"adk-{i}" for i in range(120)]
            )
            self.assertTrue(statements)
            self.assertTrue(all("LIMIT" in statement for statement, _ in statements))
            self.assertTrue(all(72 in parameters for _, parameters in statements))
        finally:
            await reader.close()

    async def test_internal_event_windows_can_return_empty_page_without_losing_older_text(
        self,
    ):
        url = f"sqlite+aiosqlite:///{Path(self.fixture.folder.name) / 'hidden.db'}"
        service = DatabaseSessionService(db_url=url)
        await service.prepare_tables()
        session = await service.create_session(
            app_name="aurora_read_probe",
            user_id="owner",
            session_id=str(self.fixture.sid),
        )
        await service.append_event(
            session,
            Event(
                id="public",
                invocation_id="old",
                author="user",
                timestamp=1700000000,
                content=types.Content(
                    role="user", parts=[types.Part(text="Mais antiga")]
                ),
            ),
        )
        for index in range(120):
            await service.append_event(
                session,
                Event(
                    id=f"hidden-{index:03}",
                    invocation_id=f"inv-{index}",
                    author="reservas",
                    timestamp=1700000001 + index,
                    content=types.Content(
                        role="model", parts=[types.Part(text="internal", thought=True)]
                    ),
                ),
            )
        try:
            page = await portal_history.history(
                self.fixture.sid, self.fixture.actor, service, limit=5
            )
            self.assertEqual(page["messages"], [])
            self.assertIsNotNone(page["next_cursor"])
            self.assertEqual(
                [row["content"] for row in await self.pages(service, 5)],
                ["Mais antiga"],
            )
        finally:
            await service.close()

    async def test_receipt_intervals_are_preserved_across_single_item_pages(self):
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with self.fixture.transaction() as session:
            session.add(
                PortalMessage(
                    id="question",
                    session_id=str(self.fixture.sid),
                    role="user",
                    content="Pedido",
                    created_at=start,
                )
            )
            session.add(
                PortalMessage(
                    id="normal",
                    session_id=str(self.fixture.sid),
                    role="assistant",
                    content="Sua reserva foi cancelada.",
                    created_at=start + timedelta(seconds=6),
                )
            )
        url = f"sqlite+aiosqlite:///{Path(self.fixture.folder.name) / 'receipts.db'}"
        service = DatabaseSessionService(db_url=url)
        await service.prepare_tables()
        session = await service.create_session(
            app_name="aurora_resident_actions",
            user_id="owner",
            session_id=str(self.fixture.sid),
        )
        for index, seconds in enumerate((2, 5)):
            await service.append_event(
                session,
                Event(
                    id=f"receipt-{index}",
                    invocation_id=f"inv-{index}",
                    author="reservas",
                    timestamp=(start + timedelta(seconds=seconds)).timestamp(),
                    content=types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name="cancelar_reserva",
                                    response={
                                        "status": "cancelled",
                                        "private": "SECRET",
                                    },
                                )
                            )
                        ],
                    ),
                ),
            )
        try:
            messages = await self.pages(service, 1)
            self.assertEqual(
                [row["content"] for row in messages],
                ["Pedido", "Sua reserva foi cancelada.", "Sua reserva foi cancelada."],
            )
            self.assertNotIn("SECRET", str(messages))
        finally:
            await service.close()

    async def test_prepared_adapter_reads_legacy_v0_without_creating_or_altering_tables(
        self,
    ):
        from google.adk.sessions.schemas.v0 import Base

        url = f"sqlite+aiosqlite:///{Path(self.fixture.folder.name) / 'legacy-v0.db'}"
        writer = DatabaseSessionService(db_url=url)
        async with writer.db_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session = await writer.create_session(
            app_name="aurora_read_probe",
            user_id="owner",
            session_id=str(self.fixture.legacy),
        )
        await writer.append_event(
            session,
            Event(
                id="legacy",
                invocation_id="legacy",
                author="user",
                timestamp=1700000000,
                content=types.Content(
                    role="user", parts=[types.Part(text="Histórico v0 preservado")]
                ),
            ),
        )
        await writer.close()
        reader = PreparedSessionService(db_url=url)
        statements = []

        @event.listens_for(reader.db_engine.sync_engine, "before_cursor_execute")
        def track(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        try:
            messages = await self.pages(reader)
            self.assertEqual(
                [row["content"] for row in messages], ["Histórico v0 preservado"]
            )
            self.assertFalse(
                any(
                    sql.lstrip().upper().startswith(("CREATE ", "ALTER ", "DROP "))
                    for sql in statements
                )
            )
        finally:
            await reader.close()


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.fixture = PortalFixture()
        self.addCleanup(self.fixture.close)
        self.now = datetime.now(timezone.utc)
        self.repo = AdmissionRepository(self.fixture, now=lambda: self.now)
        self.identity = SessionIdentity(self.fixture.sid, "owner")

    def test_independent_workers_admit_one_turn_and_persist_rate_budget(self):
        def acquire(_):
            try:
                return AdmissionRepository(self.fixture, now=lambda: self.now).acquire(
                    self.identity
                )
            except HTTPException as exc:
                return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(acquire, range(2)))
        self.assertEqual(sum(isinstance(item, str) for item in outcomes), 1)
        self.assertIn(409, outcomes)
        admitted = next(item for item in outcomes if isinstance(item, str))
        self.repo.release(admitted)
        for _ in range(self.repo.ACTOR_TURNS - 1):
            self.repo.release(self.repo.acquire(self.identity))
        with self.assertRaises(HTTPException) as refused:
            self.repo.acquire(self.identity)
        self.assertEqual(refused.exception.detail["code"], "AGENT_RATE_LIMITED")
        self.now += timedelta(seconds=61)
        self.assertIsInstance(self.repo.acquire(self.identity), str)

    def test_actor_global_concurrency_and_expiry_survive_repository_restart(self):
        first = self.repo.acquire(self.identity)
        with self.assertRaises(HTTPException) as same_actor:
            self.repo.acquire(SessionIdentity(uuid4(), "owner"))
        self.assertEqual(same_actor.exception.status_code, 429)
        for index in range(3):
            self.repo.acquire(SessionIdentity(uuid4(), f"other-{index}"))
        with self.assertRaises(HTTPException) as global_full:
            self.repo.acquire(SessionIdentity(uuid4(), "fifth"))
        self.assertEqual(
            global_full.exception.detail["code"], "AGENT_CAPACITY_EXCEEDED"
        )
        self.now += timedelta(seconds=91)
        restarted = AdmissionRepository(self.fixture, now=lambda: self.now)
        self.assertIsInstance(restarted.acquire(self.identity), str)
        with self.fixture.transaction() as session:
            self.assertIsNone(session.get(AdmissionLease, first).released_at)


class DisabledPortalTest(unittest.TestCase):
    def test_session_history_and_unavailable_response_survive_reload_with_pending_fail_closed(
        self,
    ):
        fixture = PortalFixture()
        self.addCleanup(fixture.close)
        app = FastAPI()
        app.state.portal_history_enabled = True
        app.state.resident_actions_enabled = False
        app.include_router(router)
        app.dependency_overrides[authenticated_user] = lambda: fixture.actor
        app.dependency_overrides[verify_internal] = lambda: None
        with fixture.transaction() as session:
            session.add(
                ConfirmationRecord(
                    id=str(uuid4()),
                    session_id=str(fixture.legacy),
                    resident_id="owner",
                    apartment="101",
                    action="autorizar_visitante",
                    payload={"name": "Visitante", "date": "2030-04-20"},
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
            )
        with (
            patch(
                "services.agent.controllers.chat_controller.ChatRepository",
                side_effect=fixture.repo,
            ),
            patch.object(portal_history, "ChatRepository", side_effect=fixture.repo),
            patch.object(portal_history, "get_database", return_value=fixture),
            patch(
                "services.agent.repositories.product_action_repository.get_database",
                return_value=fixture,
            ),
            patch(
                "services.agent.runtime.resident_actions.fetch_user",
                return_value=fixture.actor,
            ),
            TestClient(app) as client,
        ):

            def forward(service, method, path, payload, timeout):
                return client.post(path, json=payload)

            with patch(
                "services.agent.controllers.chat_controller.internal_request",
                side_effect=forward,
            ):
                first = client.post(
                    "/api/resident/chat/sessions", json={"apartment": "101"}
                )
                self.assertEqual(first.status_code, 201, first.text)
                sid = first.json()["id"]
                path = f"/api/resident/chat/sessions/{sid}"
                history = client.get(path + "/history")
                self.assertEqual(history.status_code, 200, history.text)
                self.assertFalse(history.json()["actions_enabled"])
                self.assertEqual(len(history.json()["confirmacoes_pendentes"]), 1)
                result = client.post(path + "/messages", json={"message": "Olá"})
                self.assertEqual(result.status_code, 503, result.text)
                self.assertEqual(
                    result.json()["detail"]["code"], "AGENT_NOT_CONFIGURED"
                )
                reopened = client.post(
                    "/api/resident/chat/sessions", json={"apartment": "101"}
                )
                self.assertEqual(reopened.json()["id"], sid)
                restored = client.get(path + "/history").json()
                self.assertEqual(len(restored["messages"]), 2)
                self.assertIn("preservada", restored["messages"][-1]["content"])
                self.assertEqual(len(restored["confirmacoes_pendentes"]), 1)
                self.assertEqual(
                    client.post(
                        path + "/confirmations",
                        json={"id": str(uuid4()), "confirmado": True},
                    ).status_code,
                    404,
                )


class HandlerGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_turn_rejected_before_provider_and_scope_change_is_public(
        self,
    ):
        fixture = PortalFixture()
        self.addCleanup(fixture.close)
        started = asyncio.Event()
        complete = asyncio.Event()

        async def respond(message):
            started.set()
            await complete.wait()
            return [
                SimpleNamespace(
                    is_final_response=lambda: True,
                    content=types.Content(
                        role="model", parts=[types.Part(text="Resposta pública")]
                    ),
                )
            ]

        runtime = SimpleNamespace(APP_NAME="aurora_read_probe", respond=respond)

        class SessionService:
            async def get_session(self, **kwargs):
                return SimpleNamespace()

        model = MagicMock(return_value=object())
        handler = ReadOnlyMessageHandler(
            identity_loader=lambda uid: fixture.actor,
            repository_factory=fixture.repo,
            tool_factory=lambda identity: SimpleNamespace(identity=identity),
            model_factory=model,
            session_service=SessionService(),
            runtime_factory=lambda **kwargs: runtime,
            admission_repository_factory=lambda: AdmissionRepository(fixture),
        )
        data = InternalMessage(
            session_id=str(fixture.sid), user_id="owner", apartment="101", message="Olá"
        )
        task = asyncio.create_task(handler(data))
        await asyncio.wait_for(started.wait(), 5)
        try:
            with self.assertRaises(HTTPException) as conflict:
                await handler(data)
            self.assertEqual(conflict.exception.status_code, 409)
            model.assert_called_once()
        finally:
            complete.set()
            await task
        public = await handler(
            data.model_copy(
                update={"message": "Mude esta conversa para o apartamento 302"}
            )
        )
        self.assertIn("privacidade", public["message"])
        self.assertNotIn("Se o morador solicitar", public["message"])
        model.assert_called_once()


class PortalStartupTest(unittest.TestCase):
    def test_enabled_http_lifespan_does_not_prepare_or_connect_any_database(self):
        from services.agent.runtime.configuration import (
            AgentRuntimeSettings,
            configure_read_agent,
        )

        app = FastAPI()
        credential = MagicMock(
            side_effect=AssertionError("Não ler credencial no startup")
        )
        configure_read_agent(
            app,
            AgentRuntimeSettings(
                True,
                "gemini-test",
                "sqlite+aiosqlite:////missing/directory/agent.db",
                actions_enabled=True,
                history_enabled=True,
            ),
            credential_provider=credential,
        )
        with (
            patch(
                "services.agent.bootstrap.initialize",
                side_effect=AssertionError("Não preparar schema no HTTP"),
            ),
            patch(
                "microservice_toolkit.get_database",
                side_effect=AssertionError("Não conectar condomínio no startup"),
            ),
            TestClient(app),
        ):
            pass
        credential.assert_not_called()
