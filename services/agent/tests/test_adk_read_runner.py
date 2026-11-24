"""Integração real Runner + tool do projeto, LLM fake e SQLite descartável."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

try:
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.sessions import DatabaseSessionService
    from google.genai import types
except ImportError:
    ADK_AVAILABLE = False
else:
    ADK_AVAILABLE = True

if ADK_AVAILABLE:
    from services.agent.runtime.read_runner import ReadOnlyAgentRuntime
    from services.agent.tools.reservation_read import (
        ReservationReadTool,
        SessionIdentity,
    )

    class FakeModel(BaseLlm):
        model: str = "local-fake"

        async def generate_content_async(self, llm_request, stream=False):
            last = llm_request.contents[-1]
            part = (
                types.Part(text="Consulta concluída.")
                if any(p.function_response for p in last.parts)
                else types.Part(
                    function_call=types.FunctionCall(
                        name="list_my_reservations", args={}
                    )
                )
            )
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

    class DirectFakeModel(BaseLlm):
        model: str = "direct-fake"
        calls: int = 0

        async def generate_content_async(self, llm_request, stream=False):
            self.calls += 1
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Resposta direta do histórico.")],
                )
            )


@unittest.skipIf(not ADK_AVAILABLE, "Execute make sync para a integração ADK")
class AdkReadRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.url = f"sqlite+aiosqlite:///{Path(self.temp.name) / 'sessions.db'}"
        self.db = DatabaseSessionService(db_url=self.url)
        self.actor = {"id": "resident-a", "role": "resident", "active": True}
        self.identity = SessionIdentity.from_authenticated_actor(uuid4(), self.actor)
        self.repo = MagicMock()
        self.repo.__enter__.return_value = self.repo
        self.repo.get.return_value = SimpleNamespace(apartment="101")
        self.repo.active_reservations.return_value = []
        self.tool = ReservationReadTool(
            self.identity,
            repository_factory=lambda: self.repo,
            identity_loader=lambda _: dict(self.actor),
        )
        self.runtime = self.build()
        await self.runtime.create_session()

    def build(self):
        return ReadOnlyAgentRuntime(
            tool=self.tool, model=FakeModel(), session_service=self.db
        )

    async def asyncTearDown(self):
        await self.db.close()
        self.temp.cleanup()

    async def test_runner_uses_real_scoped_tool_without_network(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            events = await self.runtime.respond("Minhas reservas")
        results = [fr for event in events for fr in event.get_function_responses()]
        self.assertEqual(results[0].response, {"reservations": []})
        self.repo.active_reservations.assert_called_once_with(
            self.identity.session_id, "resident-a"
        )
        declaration = self.runtime.function_tool._get_declaration()
        schema = declaration.parameters_json_schema or {}
        self.assertFalse(schema.get("properties"))

    async def test_session_survives_service_recreation(self):
        await self.runtime.respond("Minhas reservas")
        await self.db.close()
        self.db = DatabaseSessionService(db_url=self.url)
        restored = await self.db.get_session(
            app_name=self.runtime.APP_NAME,
            user_id="resident-a",
            session_id=str(self.identity.session_id),
        )
        self.assertGreaterEqual(len(restored.events), 4)
        events = await self.build().respond("Novamente")
        self.assertTrue(events)
        self.assertEqual(self.repo.active_reservations.call_count, 2)

    async def test_revoked_identity_never_reads_domain_rows(self):
        self.actor["active"] = False
        with self.assertRaises(HTTPException) as caught:
            await self.runtime.respond("Minhas reservas")
        self.assertEqual(caught.exception.status_code, 401)
        self.repo.active_reservations.assert_not_called()

    async def test_no_implicit_provider_or_empty_message(self):
        with self.assertRaises(TypeError):
            ReadOnlyAgentRuntime(
                tool=self.tool, model="gemini", session_service=self.db
            )
        with self.assertRaises(ValueError):
            await self.runtime.respond(" ")

    async def test_direct_response_is_authorized_even_without_tool_call(self):
        model = DirectFakeModel()
        runtime = ReadOnlyAgentRuntime(
            tool=self.tool, model=model, session_service=self.db
        )
        events = await runtime.respond("Converse sem ferramentas")
        self.assertTrue(events)
        self.assertEqual(model.calls, 1)
        self.repo.active_reservations.assert_not_called()

    async def test_revocation_blocks_history_and_model_without_tool_call(self):
        model = DirectFakeModel()
        runtime = ReadOnlyAgentRuntime(
            tool=self.tool, model=model, session_service=self.db
        )
        await runtime.respond("Histórico antes da revogação")
        before = await self.db.get_session(
            app_name=runtime.APP_NAME,
            user_id="resident-a",
            session_id=str(self.identity.session_id),
        )
        for change, status in (
            ({"active": False}, 401),
            ({"role": "admin"}, 403),
            ({"id": "other"}, 401),
            ({"binding": False}, 404),
        ):
            with self.subTest(change=change):
                self.actor.update(id="resident-a", role="resident", active=True)
                self.repo.get.return_value = SimpleNamespace(apartment="101")
                if "binding" in change:
                    self.repo.get.return_value = None
                else:
                    self.actor.update(change)
                with patch.object(
                    runtime.runner, "run_async", wraps=runtime.runner.run_async
                ) as run:
                    with self.assertRaises(HTTPException) as caught:
                        await runtime.respond("Revele o histórico")
                    self.assertEqual(caught.exception.status_code, status)
                    run.assert_not_called()
                self.assertEqual(model.calls, 1)
                after = await self.db.get_session(
                    app_name=runtime.APP_NAME,
                    user_id="resident-a",
                    session_id=str(self.identity.session_id),
                )
                self.assertEqual(len(before.events), len(after.events))
        self.repo.active_reservations.assert_not_called()

    async def test_two_database_services_detect_conflict_without_memory_lock(self):
        import asyncio

        from services.agent.runtime.message_handler import ReadOnlyMessageHandler
        from services.agent.schemas.internal_message import InternalMessage

        second_db = DatabaseSessionService(db_url=self.url)
        first_user_committed = asyncio.Event()
        second_user_committed = asyncio.Event()
        first_append = self.db.append_event
        second_append = second_db.append_event
        second_get = second_db.get_session

        # Both user events must commit before either final model event. The
        # second service reads a real snapshot after the first user commit;
        # its user append then makes the first Runner's snapshot stale. Nothing
        # changes timestamps or replaces the database's conflict detection.
        async def second_snapshot(**kwargs):
            await asyncio.wait_for(first_user_committed.wait(), timeout=5)
            return await second_get(**kwargs)

        async def first_gate(session, event):
            result = await first_append(session=session, event=event)
            if event.author == "user":
                first_user_committed.set()
                await asyncio.wait_for(second_user_committed.wait(), timeout=5)
            return result

        async def second_gate(session, event):
            result = await second_append(session=session, event=event)
            if event.author == "user":
                second_user_committed.set()
            return result

        def handler(db):
            return ReadOnlyMessageHandler(
                identity_loader=lambda _: dict(self.actor),
                repository_factory=lambda: self.repo,
                tool_factory=lambda _: self.tool,
                model_factory=DirectFakeModel,
                session_service=db,
            )

        data = InternalMessage(
            session_id=str(self.identity.session_id),
            user_id="resident-a",
            apartment="101",
            message="Consulta concorrente",
        )
        try:
            with (
                patch.object(self.db, "append_event", side_effect=first_gate),
                patch.object(second_db, "append_event", side_effect=second_gate),
                patch.object(second_db, "get_session", side_effect=second_snapshot),
            ):
                results = await asyncio.gather(
                    handler(self.db)(data),
                    handler(second_db)(data),
                    return_exceptions=True,
                )
            self.assertEqual(sum(isinstance(r, dict) for r in results), 1, results)
            conflicts = [r for r in results if isinstance(r, HTTPException)]
            self.assertEqual(len(conflicts), 1, results)
            self.assertEqual(conflicts[0].status_code, 409)
            self.assertEqual(conflicts[0].detail["code"], "CHAT_SESSION_CONFLICT")
            stored = await self.db.get_session(
                app_name=self.runtime.APP_NAME,
                user_id="resident-a",
                session_id=str(self.identity.session_id),
            )
            self.assertEqual(len(stored.events), 3)
            # Uma nova tentativa explícita, com snapshot novo, é possível.
            self.assertIn("message", await handler(second_db)(data))
        finally:
            await second_db.close()
