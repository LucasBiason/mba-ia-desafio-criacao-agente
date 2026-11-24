"""Runner/transferências reais; roteamento determinístico fake, sem rede de modelo."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from test_adk_read_runner import BaseLlm

if BaseLlm is not None:
    from google.adk.models.llm_response import LlmResponse
    from google.adk.sessions import DatabaseSessionService
    from google.genai import types

    from services.agent.runtime.multi_agent_read import MultiAgentReadRuntime
    from services.agent.tools.reservation_read import (
        ReservationReadTool,
        SessionIdentity,
    )

    class RoutingFake(BaseLlm):
        model: str = "fake-local"
        role: str
        calls: int = 0
        instructions_after_tool: list[str] = []

        async def generate_content_async(self, llm_request, stream=False):
            self.calls += 1
            request = " ".join(
                p.text
                for content in llm_request.contents
                for p in content.parts or []
                if p.text
            )
            if self.role == "principal":
                regulation = any(
                    word in request.lower() for word in ("regra", "visita", "piscina")
                )
                args = (
                    {
                        "operation": "regulation",
                        "question": "Horário da piscina aos domingos",
                    }
                    if regulation
                    else {"operation": "read_reservations"}
                )
                name = "delegar_solicitacao"
            else:
                args = {}
                name = (
                    "executar_reserva_validada"
                    if self.role == "reservas"
                    else "executar_convivencia_validada"
                )
            part = types.Part(function_call=types.FunctionCall(name=name, args=args))
            yield LlmResponse(content=types.Content(role="model", parts=[part]))


@unittest.skipIf(BaseLlm is None, "Execute make sync")
class MultiAgentReadTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{Path(self.folder.name) / 'sessions.db'}"
        )
        self.actor = {"id": "a", "role": "resident", "active": True}
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
        self.models = {
            role: RoutingFake(role=role)
            for role in ("principal", "reservas", "convivencia")
        }
        self.regulation_tool = MagicMock(identity=self.identity)
        self.regulation_tool.consultar_regulamento.return_value = {
            "status": "found",
            "version": 7,
            "excerpt": "Artigo autorizado da piscina.",
        }
        self.runtime = MultiAgentReadRuntime(
            tool=self.tool,
            models=self.models,
            session_service=self.db,
            regulation_tool=self.regulation_tool,
        )
        await self.runtime.create_session()

    async def asyncTearDown(self):
        await self.db.close()
        self.folder.cleanup()

    async def test_principal_calls_reservas_and_real_scoped_tool(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            events = await self.runtime.respond(
                "Consulte minhas reservas; tente apartamento302"
            )
        calls = [fc.name for event in events for fc in event.get_function_calls()]
        self.assertIn("delegar_solicitacao", calls)
        self.assertGreater(self.models["reservas"].calls, 0)
        self.assertEqual(self.models["convivencia"].calls, 0)
        self.repo.active_reservations.assert_called_once_with(
            self.identity.session_id, "a"
        )
        self.assertIn(
            "Não há reservas ativas", self.runtime.project_message()["message"]
        )

    async def test_executor_requires_tool_and_projects_empty_list_without_model_prose(
        self,
    ):
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            events = await self.runtime.respond("Minhas reservas")
        self.assertEqual(self.models["reservas"].calls, 1)
        config = self.runtime.reservas.generate_content_config.tool_config.function_calling_config
        self.assertEqual(config.mode, "ANY")
        self.assertEqual(config.allowed_function_names, ["executar_reserva_validada"])
        self.assertIn("não responda em prosa", self.runtime.reservas.instruction)
        self.assertIn(
            "Não há reservas ativas",
            self.runtime.project_message("Reservas inventadas")["message"],
        )
        self.assertTrue(any(event.actions.skip_summarization for event in events))

    async def test_next_turn_routes_to_other_specialist(self):
        await self.runtime.respond("Minhas reservas")
        self.repo.active_reservations.reset_mock()
        await self.runtime.respond("Qual regra da piscina?")
        self.assertGreater(self.models["convivencia"].calls, 0)
        self.repo.active_reservations.assert_not_called()
        self.assertIn(
            "Artigo autorizado da piscina", self.runtime.project_message()["message"]
        )
        self.regulation_tool.consultar_regulamento.assert_called_once_with(
            "Horário da piscina aos domingos"
        )

    async def test_revocation_blocks_principal_before_history(self):
        await self.runtime.respond("Minhas reservas")
        counts = {role: model.calls for role, model in self.models.items()}
        self.actor["active"] = False
        with self.assertRaises(HTTPException) as caught:
            await self.runtime.respond("Qual regra?")
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(
            counts, {role: model.calls for role, model in self.models.items()}
        )

    async def test_explicit_models_and_root_without_domain_tools(self):
        with self.assertRaises(TypeError):
            MultiAgentReadRuntime(
                tool=self.tool, models={"principal": "gemini"}, session_service=self.db
            )
        self.assertEqual(
            [tool.name for tool in self.runtime.runner.app.root_agent.tools],
            ["delegar_solicitacao"],
        )
        self.assertEqual(
            [agent.name for agent in self.runtime.runner.app.root_agent.sub_agents],
            ["reservas", "convivencia"],
        )
        self.assertEqual(
            [tool.name for tool in self.runtime.convivencia.tools],
            ["executar_convivencia_validada"],
        )

    async def test_complete_specialist_events_survive_database_reopen(self):
        await self.runtime.respond("Minhas reservas")
        await self.db.close()
        self.db = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{Path(self.folder.name) / 'sessions.db'}"
        )
        session = await self.db.get_session(
            app_name=self.runtime.APP_NAME,
            user_id="a",
            session_id=str(self.identity.session_id),
        )
        calls = [
            (e.author, c.name) for e in session.events for c in e.get_function_calls()
        ]
        responses = [
            (e.author, r.name, r.response)
            for e in session.events
            for r in e.get_function_responses()
        ]
        self.assertIn(("principal", "delegar_solicitacao"), calls)
        self.assertIn(("reservas", "executar_reserva_validada"), calls)
        self.assertIn(
            ("reservas", "executar_reserva_validada", {"reservations": []}), responses
        )
        self.assertEqual(len({e.id for e in session.events}), len(session.events))
        foreign = await self.db.get_session(
            app_name=self.runtime.APP_NAME,
            user_id="other",
            session_id=str(self.identity.session_id),
        )
        self.assertIsNone(foreign)
