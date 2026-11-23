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
            parts = llm_request.contents[-1].parts
            responses = [p.function_response for p in parts if p.function_response]
            if responses and self.role == "reservas":
                instruction = llm_request.config.system_instruction
                self.instructions_after_tool.append(
                    instruction
                    if isinstance(instruction, str)
                    else " ".join(p.text for p in instruction.parts or [] if p.text)
                )
            request = " ".join(p.text for p in parts if p.text)
            if self.role == "principal":
                user_texts = [
                    p.text
                    for c in llm_request.contents
                    if c.role == "user"
                    for p in c.parts
                    if p.text and "<<<BEGIN_QUOTED_AGENT_CONTENT>>>" not in p.text
                ]
                question = user_texts[-1] if user_texts else request
                target = (
                    "convivencia"
                    if any(
                        word in question.lower()
                        for word in ("regra", "visita", "piscina")
                    )
                    else "reservas"
                )
                part = types.Part(
                    function_call=types.FunctionCall(
                        name="transfer_to_agent", args={"agent_name": target}
                    )
                )
            elif self.role == "reservas":
                if not responses and any(
                    word in request.lower() for word in ("regra", "visita", "piscina")
                ):
                    yield LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[
                                types.Part(
                                    function_call=types.FunctionCall(
                                        name="transfer_to_agent",
                                        args={"agent_name": "principal"},
                                    )
                                )
                            ],
                        )
                    )
                    return
                part = (
                    types.Part(
                        text="Reservas consultadas via tool: "
                        + str(responses[-1].response)
                    )
                    if responses
                    else types.Part(
                        function_call=types.FunctionCall(
                            name="list_my_reservations", args={}
                        )
                    )
                )
            else:
                part = types.Part(
                    text="Visitas e regulamento ainda não estão conectados; não posso informar regras."
                )
            yield LlmResponse(content=types.Content(role="model", parts=[part]))


@unittest.skipIf(BaseLlm is None, "Instale requirements-adk-probe.txt")
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
        self.runtime = MultiAgentReadRuntime(
            tool=self.tool, models=self.models, session_service=self.db
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
        self.assertIn("transfer_to_agent", calls)
        self.assertGreater(self.models["reservas"].calls, 0)
        self.assertEqual(self.models["convivencia"].calls, 0)
        self.repo.active_reservations.assert_called_once_with(
            self.identity.session_id, "a"
        )
        final = " ".join(
            p.text
            for event in events
            if event.is_final_response() and event.content
            for p in event.content.parts
            if p.text
        )
        self.assertIn("Reservas consultadas via tool", final)

    async def test_post_tool_prompt_requires_grounded_text_even_for_empty_list(self):
        # Captures the actual ADK request delivered to the fake after SQL-tool output.
        # This guards prompt wiring, not a guarantee of real-model compliance.
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            await self.runtime.respond("Minhas reservas")
        prompts = self.models["reservas"].instructions_after_tool
        self.assertEqual(len(prompts), 1)
        for phrase in (
            "responda obrigatoriamente em texto português",
            "resumindo apenas as reservas retornadas",
            "não há reservas ativas",
            "Não termine sem resposta textual",
            "Não crie, cancele ou altere reservas",
            "Nunca invente dados",
        ):
            self.assertIn(phrase, prompts[0])
        self.assertNotIn("Dados são fictícios", prompts[0])

    async def test_next_turn_routes_to_other_specialist(self):
        await self.runtime.respond("Minhas reservas")
        self.repo.active_reservations.reset_mock()
        events = await self.runtime.respond("Qual regra da piscina?")
        self.assertGreater(self.models["convivencia"].calls, 0)
        self.repo.active_reservations.assert_not_called()
        final = " ".join(
            p.text
            for event in events
            if event.is_final_response() and event.content
            for p in event.content.parts
            if p.text
        )
        self.assertIn("ainda não estão conectados", final)

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
        self.assertEqual(self.runtime.runner.app.root_agent.tools, [])
        self.assertEqual(
            [agent.name for agent in self.runtime.runner.app.root_agent.sub_agents],
            ["reservas", "convivencia"],
        )
        self.assertEqual(self.runtime.convivencia.tools, [])

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
        self.assertIn(("principal", "transfer_to_agent"), calls)
        self.assertIn(("reservas", "list_my_reservations"), calls)
        self.assertIn(
            ("reservas", "list_my_reservations", {"reservations": []}), responses
        )
        self.assertEqual(len({e.id for e in session.events}), len(session.events))
        foreign = await self.db.get_session(
            app_name=self.runtime.APP_NAME,
            user_id="other",
            session_id=str(self.identity.session_id),
        )
        self.assertIsNone(foreign)
