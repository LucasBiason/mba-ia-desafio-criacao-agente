"""Actual Runner, fake model and action service; no provider/domain writes."""

import unittest
from unittest.mock import MagicMock
from uuid import UUID

import test_multi_agent_read as fixtures
from fastapi import HTTPException
from test_multi_agent_read import LlmResponse, RoutingFake, types

from services.agent.runtime.multi_agent_actions import MultiAgentActionRuntime


class ActionFake(RoutingFake):
    async def generate_content_async(self, llm_request, stream=False):
        if self.role == "principal":
            part = types.Part(
                function_call=types.FunctionCall(
                    name="delegar_solicitacao",
                    args={
                        "operation": "reserve",
                        "area": "Salão de Festas",
                        "date": "2030-04-09",
                    },
                )
            )
        else:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="executar_reserva_validada", args={}
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
        actions.reserve.return_value = {"status": "pending"}
        actions.results = []
        runtime = MultiAgentActionRuntime(
            tool=self.tool,
            models=models,
            session_service=self.db,
            regulation_tool=None,
            actions=actions,
        )
        await runtime.create_session()
        events = await runtime.respond("Reserve salão para2030-04-09")
        actions.reserve.assert_called_once()
        self.assertEqual(
            actions.reserve.call_args.args, ("Salão de Festas", "2030-04-09")
        )
        proposal_id = actions.reserve.call_args.kwargs["proposal_id"]
        self.assertEqual(str(UUID(proposal_id)), proposal_id)
        self.assertEqual(runtime.identity, self.identity)
        self.assertIn(
            "executar_reserva_validada",
            [fc.name for e in events for fc in e.get_function_calls()],
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
        with self.assertRaises(HTTPException) as caught:
            runtime.project_message("")
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.detail["code"], "AGENT_UNAVAILABLE")

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
