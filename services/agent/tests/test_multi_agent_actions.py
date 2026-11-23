"""Actual Runner, fake model and action service; no provider/domain writes."""

from unittest.mock import MagicMock
import unittest
import test_multi_agent_read as fixtures
from test_multi_agent_read import RoutingFake, LlmResponse, types
from services.agent.runtime.multi_agent_actions import MultiAgentActionRuntime


class ActionFake(RoutingFake):
    async def generate_content_async(self, llm_request, stream=False):
        if self.role != "reservas":
            async for event in super().generate_content_async(llm_request, stream):
                yield event
            return
        responses = [
            p.function_response
            for p in llm_request.contents[-1].parts
            if p.function_response
        ]
        part = (
            types.Part(text="Confirme no portal.")
            if responses
            else types.Part(
                function_call=types.FunctionCall(
                    name="reservar_area",
                    args={"area": "Salão de Festas", "data": "2030-04-09"},
                )
            )
        )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


class ActionCompositionTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.MultiAgentReadTest.asyncSetUp
    asyncTearDown = fixtures.MultiAgentReadTest.asyncTearDown

    async def test_action_dispatch_preserves_server_identity(self):
        models = {
            role: ActionFake(role=role)
            for role in ("principal", "reservas", "convivencia")
        }
        actions = MagicMock()
        actions.reserve.return_value = {"status": "pending_confirmation"}
        runtime = MultiAgentActionRuntime(
            tool=self.tool,
            models=models,
            session_service=self.db,
            regulation_tool=None,
            actions=actions,
        )
        await runtime.create_session()
        events = await runtime.respond("Reserve salão para2030-04-09")
        actions.reserve.assert_called_once_with("Salão de Festas", "2030-04-09")
        self.assertEqual(runtime.identity, self.identity)
        self.assertIn(
            "reservar_area", [fc.name for e in events for fc in e.get_function_calls()]
        )

    async def test_blank_model_uses_exact_authorized_excerpt(self):
        actions = MagicMock()
        actions.results = []
        actions.message_projection.side_effect = lambda text: {
            "message": text,
            "confirmacoes_pendentes": [],
        }
        runtime = MultiAgentActionRuntime(
            tool=self.tool,
            models=self.models,
            session_service=self.db,
            regulation_tool=None,
            actions=actions,
        )
        runtime.read_results.append(
            (
                "regulation",
                {"status": "found", "version": 7, "excerpt": "Art. 3: texto exato."},
            )
        )
        self.assertEqual(
            runtime.project_message("")["message"],
            "Regulamento versão 7:\nArt. 3: texto exato.",
        )
        runtime.read_results.clear()
        self.assertIn("Não consegui concluir", runtime.project_message("")["message"])

    async def test_retrieval_misses_consolidated_positive_citations_preserved(self):
        actions = MagicMock()
        actions.results = []
        actions.message_projection.side_effect = lambda text: {"message": text}
        runtime = MultiAgentActionRuntime(
            tool=self.tool,
            models=self.models,
            session_service=self.db,
            regulation_tool=None,
            actions=actions,
        )
        runtime.read_results = [
            ("regulation", {"status": "not_found", "message": "Refine"}),
            ("regulation", {"status": "ambiguous", "message": "Outro erro"}),
            (
                "regulation",
                {
                    "status": "not_specified",
                    "message": "Ausência auditada, não implica gratuidade.",
                },
            ),
        ]
        self.assertEqual(
            runtime.project_message("")["message"],
            "Ausência auditada, não implica gratuidade.",
        )
        runtime.read_results.append(
            (
                "regulation",
                {"status": "found", "version": 0, "excerpt": "Artigo pertinente."},
            )
        )
        answer = runtime.project_message("")["message"]
        self.assertIn("Artigo pertinente.", answer)
        self.assertNotIn("Refine", answer)
        self.assertEqual(answer.count("Ausência auditada"), 1)
