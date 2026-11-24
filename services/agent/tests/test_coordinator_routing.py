"""Regressão da recusa direta do coordenador em um pedido válido de visita."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from google.adk.events import Event
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import Field

from services.agent.runtime.multi_agent_actions import MultiAgentActionRuntime
from services.agent.tools.reservation_read import SessionIdentity


class RoutingContractModel(BaseLlm):
    model: str = "offline-routing-contract"
    role: str
    requests: list[dict] = Field(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        config = llm_request.config.tool_config
        calling = config.function_calling_config if config else None
        self.requests.append(
            {
                "mode": calling.mode if calling else None,
                "allowed": calling.allowed_function_names if calling else None,
                "tools": sorted(llm_request.tools_dict),
            }
        )
        if self.role == "principal":
            # AUTO permite a recusa textual observada no provedor. ANY exige
            # escolher a transferência, mantendo a decisão do especialista.
            if calling and calling.mode == "ANY":
                part = types.Part(
                    function_call=types.FunctionCall(
                        name="delegar_solicitacao",
                        args={
                            "operation": "propose_visit",
                            "name": "Visitante QA",
                            "date": "2030-06-02",
                        },
                    )
                )
            else:
                part = types.Part(text="Não posso ajudar com essa visita.")
        elif self.role == "convivencia":
            part = types.Part(
                function_call=types.FunctionCall(
                    name="executar_convivencia_validada",
                    args={},
                )
            )
        else:
            part = types.Part(text="Este especialista trata apenas de reservas.")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


class CoordinatorRoutingTest(unittest.IsolatedAsyncioTestCase):
    async def test_valid_visit_reaches_specialist_and_requests_confirmation(self):
        await self._exercise_visit()

    async def test_existing_reservations_conversation_returns_to_coordinator(self):
        await self._exercise_visit(prior_reservas=True)

    async def _exercise_visit(self, *, prior_reservas=False):
        actor = {"id": "qa-owner", "role": "resident", "active": True}
        identity = SessionIdentity.from_authenticated_actor(uuid4(), actor)
        tool = MagicMock()
        tool.identity = identity
        models = {
            role: RoutingContractModel(role=role)
            for role in ("principal", "reservas", "convivencia")
        }
        actions = MagicMock()
        actions.authorize_visit.return_value = {
            "status": "pending_confirmation",
            "id": "qa-confirmation",
        }
        service = InMemorySessionService()
        runtime = MultiAgentActionRuntime(
            tool=tool,
            models=models,
            session_service=service,
            regulation_tool=None,
            actions=actions,
        )
        session = await runtime.create_session()
        previous = None
        if prior_reservas:
            previous = Event(
                invocation_id="previous-turn",
                author="reservas",
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Conversa anterior de reservas.")],
                ),
            )
            await service.append_event(session=session, event=previous)
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            events = await runtime.respond(
                "Autorize Visitante QA em 02/06/2030 no meu apartamento."
            )
        self.assertEqual(
            actions.authorize_visit.call_args.args, ("Visitante QA", "2030-06-02")
        )
        self.assertTrue(actions.authorize_visit.call_args.kwargs["proposal_id"])
        self.assertEqual(actions.authorize_visit.call_count, 1)
        actions.reserve.assert_not_called()
        actions.cancel.assert_not_called()
        self.assertEqual(runtime.identity, identity)
        request = models["principal"].requests[0]
        self.assertEqual(request["mode"], "ANY")
        self.assertEqual(request["allowed"], ["delegar_solicitacao"])
        self.assertEqual(request["tools"], ["delegar_solicitacao"])
        specialist = models["convivencia"].requests[0]
        self.assertEqual(specialist["mode"], "ANY")
        self.assertEqual(specialist["tools"], ["executar_convivencia_validada"])
        self.assertNotIn("transfer_to_agent", specialist["tools"])
        self.assertEqual(models["reservas"].requests, [])
        preserved = await service.get_session(
            app_name=runtime.APP_NAME,
            user_id=identity.resident_id,
            session_id=str(identity.session_id),
        )
        if previous is not None:
            self.assertIn(previous.id, [event.id for event in preserved.events])
        calls = [call.name for event in events for call in event.get_function_calls()]
        self.assertEqual(
            calls, ["delegar_solicitacao", "executar_convivencia_validada"]
        )
        responses = [
            response
            for event in events
            for response in event.get_function_responses()
            if response.name == "executar_convivencia_validada"
        ]
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].response["status"], "pending_confirmation")
