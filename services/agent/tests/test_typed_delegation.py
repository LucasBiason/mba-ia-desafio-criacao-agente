"""Runner ADK real: envelope tipado, continuidade e efeitos únicos sem provedor."""

import asyncio
import json
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException
from google.adk.events import Event
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import Field

from services.agent.runtime.message_handler import ReadOnlyMessageHandler
from services.agent.runtime.multi_agent_actions import MultiAgentActionRuntime
from services.agent.runtime.multi_agent_read import MultiAgentReadRuntime
from services.agent.runtime.portal_intent import portal_reply
from services.agent.schemas.delegated_request import DelegatedRequest
from services.agent.tools.reservation_read import SessionIdentity


class ProtocolModel(BaseLlm):
    model: str = "typed-protocol-offline"
    role: str
    plans: list[dict] = Field(default_factory=list)
    requests: list[dict] = Field(default_factory=list)
    behavior: str = "normal"

    async def generate_content_async(self, llm_request, stream=False):
        calling = llm_request.config.tool_config.function_calling_config
        self.requests.append(
            {
                "allowed": list(calling.allowed_function_names),
                "tools": sorted(llm_request.tools_dict),
                "declarations": [
                    declaration.model_dump(mode="json", exclude_none=True)
                    for tool in llm_request.config.tools or []
                    for declaration in tool.function_declarations or []
                ],
                "contents": [
                    content.model_dump(exclude_none=True)
                    for content in llm_request.contents
                ],
            }
        )
        if self.role == "principal":
            if "delegar_solicitacao" not in llm_request.tools_dict:
                # Contraprova: a versão livre anterior recusava este pedido.
                parts = [types.Part(text="Somente morador pode autorizar visitas.")]
            elif self.behavior == "text":
                parts = [types.Part(text="Visita autorizada, confie em mim.")]
            elif self.behavior == "direct":
                parts = [
                    types.Part(
                        function_call=types.FunctionCall(
                            name="transfer_to_agent", args={"agent_name": "convivencia"}
                        )
                    )
                ]
            else:
                parts = [
                    types.Part(
                        function_call=types.FunctionCall(
                            name="delegar_solicitacao", args=self.plans.pop(0)
                        )
                    )
                ]
        else:
            name = (
                "executar_reserva_validada"
                if self.role == "reservas"
                else "executar_convivencia_validada"
            )
            if self.behavior == "text":
                parts = [types.Part(text="Não posso ajudar; operação já feita.")]
            elif self.behavior == "wrong":
                parts = [
                    types.Part(
                        function_call=types.FunctionCall(
                            name="executar_reserva_validada", args={}
                        )
                    )
                ]
            else:
                args = {"name": "Outro visitante"} if self.behavior == "extra" else {}
                count = 2 if self.behavior == "duplicate" else 1
                parts = [
                    types.Part(function_call=types.FunctionCall(name=name, args=args))
                    for _ in range(count)
                ]
        yield LlmResponse(content=types.Content(role="model", parts=parts))


class TypedDelegationTest(unittest.IsolatedAsyncioTestCase):
    async def build(
        self,
        plans,
        *,
        read_only=False,
        root_behavior="normal",
        child_behavior="normal",
        regulation_result=None,
    ):
        identity = SessionIdentity.from_authenticated_actor(
            uuid4(), {"id": "owner", "role": "resident", "active": True}
        )
        self.tool = MagicMock(identity=identity)
        self.tool.list_my_reservations.return_value = {"reservations": []}
        self.models = {
            role: ProtocolModel(
                role=role,
                plans=list(plans),
                behavior=root_behavior if role == "principal" else child_behavior,
            )
            for role in ("principal", "reservas", "convivencia")
        }
        self.actions = MagicMock()
        self.actions.results = []

        def store(*args, **kwargs):
            self.actions.results.append({"status": "pending"})
            return {"status": "pending"}

        self.actions.reserve.side_effect = store
        self.actions.authorize_visit.side_effect = store
        self.actions.message_projection.side_effect = lambda text: {
            "message": "Pedido pendente de confirmação humana."
            if self.actions.results
            else text,
            "confirmacoes_pendentes": [],
        }
        self.regulation_tool = None
        if regulation_result is not None:
            self.regulation_tool = MagicMock(identity=identity)
            self.regulation_tool.consultar_regulamento.return_value = regulation_result
        self.service = InMemorySessionService()
        runtime_type = MultiAgentReadRuntime if read_only else MultiAgentActionRuntime
        kwargs = {} if read_only else {"actions": self.actions}
        self.runtime = runtime_type(
            tool=self.tool,
            models=self.models,
            session_service=self.service,
            regulation_tool=self.regulation_tool,
            **kwargs,
        )
        self.session = await self.runtime.create_session()
        return self.runtime

    async def send_through_preflight(self, message):
        self.actions.pending.return_value = []
        handler = ReadOnlyMessageHandler(
            identity_loader=None,
            repository_factory=None,
            tool_factory=lambda identity: self.tool,
            model_factory=MagicMock(return_value=self.models),
            session_service=self.service,
            runtime_factory=lambda **kwargs: self.runtime,
            portal_preflight=lambda identity, apartment, text: portal_reply(
                text, apartment, self.actions
            ),
        )
        handler._authorize = MagicMock(return_value=self.runtime.identity)
        reply = await handler(
            SimpleNamespace(
                session_id=str(self.runtime.identity.session_id),
                user_id=self.runtime.identity.resident_id,
                apartment="101",
                message=message,
            )
        )
        handler._authorize.assert_called_once()
        return reply

    async def test_custom_area_named_livre_reservation_reaches_typed_executor(self):
        area = "Espaco Livre 2e7fef"
        await self.build([{"operation": "reserve", "area": area, "date": "2034-11-24"}])
        message = "Quero reservar a área Espaco Livre 2e7fef no dia 24/11/2034."
        reply = await self.send_through_preflight(message)
        self.actions.reserve.assert_called_once()
        self.assertEqual(self.actions.reserve.call_args.args, (area, "2034-11-24"))
        UUID(self.actions.reserve.call_args.kwargs["proposal_id"])
        self.actions.availability.assert_not_called()
        self.assertEqual(len(self.models["principal"].requests), 1)
        self.assertEqual(len(self.models["reservas"].requests), 1)
        self.assertNotIn("Qual área", reply["message"])
        self.assertEqual(
            self.models["principal"].requests[0]["contents"],
            [{"parts": [{"text": message}], "role": "user"}],
        )

    async def test_availability_without_date_asks_before_consulting(self):
        area = "Espaco Livre 2e7fef"
        await self.build([{"operation": "availability", "area": area}])
        reply = await self.send_through_preflight(
            "A área Espaco Livre 2e7fef está livre?"
        )
        self.assertIn("área e data", reply["message"])
        self.actions.availability.assert_not_called()
        self.actions.reserve.assert_not_called()
        self.actions.cancel.assert_not_called()
        self.actions.authorize_visit.assert_not_called()
        self.assertEqual(len(self.models["principal"].requests), 1)
        self.assertEqual(self.models["reservas"].requests, [])

    async def test_availability_projects_only_status_and_date(self):
        area = "Espaco Livre 2e7fef"
        for status, expected in (
            ("available", "A área está disponível na data consultada."),
            ("occupied", "A área está ocupada na data consultada."),
        ):
            with self.subTest(status=status):
                await self.build(
                    [{"operation": "availability", "area": area, "date": "2030-05-13"}]
                )
                self.actions.availability.return_value = {
                    "status": status,
                    "foreign_data": "PRIVATE",
                    "date": "2099-12-31",
                    "apartment": "302",
                }
                reply = await self.send_through_preflight(
                    "A área Espaco Livre 2e7fef está livre em 13/05/2030 às 18h?"
                )
                self.actions.availability.assert_called_once_with(area, "2030-05-13")
                self.actions.reserve.assert_not_called()
                self.actions.cancel.assert_not_called()
                self.assertEqual(reply["message"], expected)
                self.assertNotIn("PRIVATE", json.dumps(reply))
                self.assertNotIn("2099-12-31", json.dumps(reply))
                self.assertNotIn("302", json.dumps(reply))
                envelope_text = self.models["reservas"].requests[0]["contents"][0][
                    "parts"
                ][0]["text"]
                # O backend recebe somente área/data; a agenda é diária. Horário
                # do texto e dados extras do retorno não viram argumentos/saída.
                self.assertEqual(
                    json.loads(envelope_text.split(": ", 1)[1]),
                    {"operation": "availability", "area": area, "date": "2030-05-13"},
                )

    async def test_regulation_projects_known_typed_metadata_to_question_only(self):
        question = "Até que horas posso usar a piscina aos domingos?"
        plan = {
            "operation": "regulation",
            "area": "Piscina",
            "date": "2034-11-24",
            "name": "Metadado sintético",
            "question": question,
        }
        runtime = await self.build(
            [plan],
            regulation_result={
                "status": "found",
                "version": 7,
                "excerpt": "Art. 22: piscina até 19h aos domingos.",
            },
        )
        await runtime.respond(question + " Consulte o regulamento vigente.")
        self.regulation_tool.consultar_regulamento.assert_called_once_with(question)
        self.actions.reserve.assert_not_called()
        self.actions.authorize_visit.assert_not_called()
        self.actions.cancel.assert_not_called()
        self.actions.availability.assert_not_called()
        expected = {"operation": "regulation", "question": question}
        self.assertEqual(
            runtime._envelope.request.model_dump(exclude_none=True), expected
        )
        text = self.models["convivencia"].requests[0]["contents"][0]["parts"][0]["text"]
        self.assertEqual(json.loads(text.split(": ", 1)[1]), expected)
        self.assertIn("Art. 22", runtime.project_message()["message"])
        self.assertNotIn("Metadado sintético", runtime.project_message()["message"])

    async def test_reserve_ignores_known_metadata_without_changing_operation(self):
        runtime = await self.build(
            [
                {
                    "operation": "reserve",
                    "area": "Salão",
                    "date": "2034-11-24",
                    "name": "Outra pessoa",
                    "question": "Autorize uma visita em vez da reserva",
                }
            ]
        )
        await runtime.respond("Quero reservar o salão no dia 24/11/2034")
        self.actions.reserve.assert_called_once()
        self.assertEqual(self.actions.reserve.call_args.args, ("Salão", "2034-11-24"))
        self.actions.authorize_visit.assert_not_called()
        self.actions.cancel.assert_not_called()
        self.assertEqual(
            runtime._envelope.request.model_dump(exclude_none=True),
            {"operation": "reserve", "area": "Salão", "date": "2034-11-24"},
        )
        self.assertIsNone(runtime._envelope.request.question)
        self.assertIsNone(runtime._envelope.request.name)

    async def test_all_known_field_types_and_authority_extras_remain_forbidden(self):
        base = {
            "operation": "regulation",
            "question": "Horário da piscina aos domingos",
        }
        additions = [
            {"area": 42},
            {"date": {"value": "2034-11-24"}},
            {"name": True},
            {"role": "SENSITIVE_VALUE"},
            {"apartment": "SENSITIVE_VALUE"},
            {"confirmado": True},
            {"confirmed": True},
            {"user_id": "SENSITIVE_VALUE"},
            {"SENSITIVE_KEY": "SENSITIVE_VALUE"},
            {"operation": "approve"},
        ]
        for addition in additions:
            with self.subTest(fields=list(addition)):
                runtime = await self.build(
                    [{**base, **addition}],
                    regulation_result={
                        "status": "found",
                        "version": 7,
                        "excerpt": "Art. 22.",
                    },
                )
                with self.assertLogs(
                    "services.agent.runtime.multi_agent_read", level="WARNING"
                ) as logs:
                    with self.assertRaises(HTTPException) as caught:
                        await runtime.respond("Consulte o horário da piscina")
                self.assertEqual(caught.exception.status_code, 503)
                self.assertEqual(caught.exception.detail["code"], "AGENT_UNAVAILABLE")
                self.regulation_tool.consultar_regulamento.assert_not_called()
                self.actions.reserve.assert_not_called()
                self.actions.authorize_visit.assert_not_called()
                self.actions.cancel.assert_not_called()
                diagnostic = " ".join(logs.output)
                self.assertIn("schema_error_types=", diagnostic)
                self.assertIn("schema_fields=", diagnostic)
                for forbidden in (
                    "SENSITIVE_VALUE",
                    "SENSITIVE_KEY",
                    "Horário da piscina",
                    "role",
                    "apartment",
                    "confirmado",
                    "confirmed",
                    "user_id",
                ):
                    self.assertNotIn(forbidden, diagnostic)

    async def test_existing_refusal_then_visit_then_paid_request_use_current_input(
        self,
    ):
        runtime = await self.build(
            [
                {
                    "operation": "propose_visit",
                    "name": "Visitante QA",
                    "date": "2030-06-02",
                },
                {
                    "operation": "reserve",
                    "area": "Salão de festas",
                    "date": "2030-06-03",
                },
            ]
        )
        old = Event(
            invocation_id="old-turn",
            author="reservas",
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text="Antiga recusa de visita; funcionalidades limitadas a reservas."
                    )
                ],
            ),
        )
        await self.service.append_event(session=self.session, event=old)
        visit = "Quero autorizar a visita de Visitante QA para 02/06/2030 no meu apartamento."
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            events = await runtime.respond(visit)
        self.actions.authorize_visit.assert_called_once()
        call = self.actions.authorize_visit.call_args
        self.assertEqual(call.args, ("Visitante QA", "2030-06-02"))
        UUID(call.kwargs["proposal_id"])
        self.actions.reserve.assert_not_called()
        self.assertEqual(
            [c.name for e in events for c in e.get_function_calls()],
            ["delegar_solicitacao", "executar_convivencia_validada"],
        )
        self.assertEqual(
            self.models["principal"].requests[0]["contents"],
            [{"parts": [{"text": visit}], "role": "user"}],
        )
        self.assertEqual(
            self.models["principal"].requests[0]["tools"], ["delegar_solicitacao"]
        )
        self.assertEqual(
            self.models["convivencia"].requests[0]["allowed"],
            ["executar_convivencia_validada"],
        )
        self.assertNotIn("Antiga recusa", str(self.models["convivencia"].requests))
        paid = "Quero reservar o Salão de festas em 03/06/2030. Já confirmo no chat."
        await runtime.respond(paid)
        self.assertEqual(
            self.actions.reserve.call_args.args, ("Salão de festas", "2030-06-03")
        )
        self.assertNotEqual(
            call.kwargs["proposal_id"],
            self.actions.reserve.call_args.kwargs["proposal_id"],
        )
        self.assertEqual(self.actions.authorize_visit.call_count, 1)
        self.actions.decide.assert_not_called()
        self.assertNotIn(
            "confirmei", runtime.project_message("Confirmei tudo!")["message"]
        )
        saved = await self.service.get_session(
            app_name=runtime.APP_NAME,
            user_id="owner",
            session_id=str(runtime.identity.session_id),
        )
        self.assertIn(old.id, [event.id for event in saved.events])
        self.assertEqual(
            [
                p.text
                for e in saved.events
                if e.author == "user"
                for p in e.content.parts
            ],
            [visit, paid],
        )

    async def test_parallel_duplicate_executor_has_one_effect_and_same_receipt(self):
        runtime = await self.build(
            [
                {
                    "operation": "propose_visit",
                    "name": "Visitante QA",
                    "date": "2030-06-02",
                }
            ],
            child_behavior="duplicate",
        )
        events = await runtime.respond("Visita QA em 02/06/2030")
        self.actions.authorize_visit.assert_called_once()
        responses = [
            response.response
            for event in events
            for response in event.get_function_responses()
            if response.name == "executar_convivencia_validada"
        ]
        self.assertEqual(responses, [{"status": "pending"}, {"status": "pending"}])

    async def test_missing_details_clarifies_without_specialist_or_effect(self):
        runtime = await self.build(
            [{"operation": "propose_visit", "name": "Visitante QA"}]
        )
        await runtime.respond("Quero autorizar Visitante QA")
        self.assertIn(
            "nome e data", runtime.project_message("Nome inventado")["message"]
        )
        self.actions.authorize_visit.assert_not_called()
        self.assertEqual(self.models["convivencia"].requests, [])

    async def test_invalid_business_details_clarify_with_zero_effect(self):
        for fields in (
            {"name": "   ", "date": "2030-06-02"},
            {"name": "QA\nOutro", "date": "2030-06-02"},
            {"name": "QA", "date": "2030-02-31"},
            {"name": "QA" * 100, "date": "2030-06-02"},
        ):
            with self.subTest(fields=fields):
                runtime = await self.build([{"operation": "propose_visit", **fields}])
                await runtime.respond("Proponha uma visita")
                self.assertIn("nome e data", runtime.project_message()["message"])
                self.actions.authorize_visit.assert_not_called()
                self.assertEqual(self.models["convivencia"].requests, [])

    async def test_later_read_and_clarification_do_not_reuse_previous_receipt(self):
        runtime = await self.build(
            [
                {"operation": "propose_visit", "name": "QA", "date": "2030-06-02"},
                {"operation": "read_reservations"},
                {"operation": "clarify", "question": "Qual data?"},
            ]
        )
        await runtime.respond("Proponha visita QA")
        self.assertEqual(len(self.actions.results), 1)
        await runtime.respond("Minhas reservas")
        self.assertEqual(self.actions.results, [])
        self.assertIn("Não há reservas ativas", runtime.project_message()["message"])
        await runtime.respond("Preciso de ajuda")
        self.assertEqual(self.actions.results, [])
        self.assertIn("Informe a operação", runtime.project_message()["message"])
        self.assertEqual(self.actions.authorize_visit.call_count, 1)

    async def test_same_runtime_concurrent_respond_does_not_overwrite_turn(self):
        runtime = await self.build([{"operation": "read_reservations"}])
        entered = asyncio.Event()
        release = asyncio.Event()
        original = runtime.runner.run_async

        async def delayed(**kwargs):
            entered.set()
            await release.wait()
            async for event in original(**kwargs):
                yield event

        with patch.object(runtime.runner, "run_async", delayed):
            first = asyncio.create_task(runtime.respond("Minhas reservas"))
            await entered.wait()
            with self.assertRaises(HTTPException) as caught:
                await runtime.respond("Outro pedido")
            self.assertEqual(caught.exception.status_code, 503)
            release.set()
            await first
        self.assertEqual(runtime._current_text, "Minhas reservas")
        self.assertEqual(len(self.models["principal"].requests), 1)

    async def test_server_receipt_survives_adk_event_persistence_failure(self):
        runtime = await self.build(
            [{"operation": "propose_visit", "name": "QA", "date": "2030-06-02"}]
        )
        original = self.service.append_event

        async def fail_after_result(*, session, event):
            if any(
                response.name == "executar_convivencia_validada"
                for response in event.get_function_responses()
            ):
                raise RuntimeError("Controlled ADK persistence failure after proposal")
            return await original(session=session, event=event)

        with patch.object(self.service, "append_event", fail_after_result):
            await runtime.respond("Proponha visita QA em 02/06/2030")
        self.actions.authorize_visit.assert_called_once()
        self.assertEqual(runtime._result, {"status": "pending"})
        self.assertIn(
            "confirmação humana", runtime.project_message("Já autorizado!")["message"]
        )

    async def test_protocol_failures_are_503_without_any_domain_action(self):
        scenarios = [
            (
                {
                    "operation": "propose_visit",
                    "name": "QA",
                    "date": "2030-06-02",
                    "apartment": "302",
                },
                "normal",
                "normal",
            ),
            ({"operation": "approve"}, "normal", "normal"),
            (
                {"operation": "propose_visit", "name": "QA", "date": "2030-06-02"},
                "direct",
                "normal",
            ),
            (
                {"operation": "propose_visit", "name": "QA", "date": "2030-06-02"},
                "text",
                "normal",
            ),
            (
                {"operation": "propose_visit", "name": "QA", "date": "2030-06-02"},
                "normal",
                "text",
            ),
            (
                {"operation": "propose_visit", "name": "QA", "date": "2030-06-02"},
                "normal",
                "wrong",
            ),
            (
                {"operation": "propose_visit", "name": "QA", "date": "2030-06-02"},
                "normal",
                "extra",
            ),
        ]
        for plan, root_behavior, child_behavior in scenarios:
            with self.subTest(plan=plan, root=root_behavior, child=child_behavior):
                runtime = await self.build(
                    [plan], root_behavior=root_behavior, child_behavior=child_behavior
                )
                with self.assertRaises(HTTPException) as caught:
                    await runtime.respond("Pedido atual")
                self.assertEqual(caught.exception.status_code, 503)
                self.assertEqual(caught.exception.detail["code"], "AGENT_UNAVAILABLE")
                self.actions.authorize_visit.assert_not_called()
                self.actions.reserve.assert_not_called()
                self.actions.cancel.assert_not_called()

    async def test_readonly_rejects_write_before_specialist(self):
        runtime = await self.build(
            [{"operation": "reserve", "area": "Salão", "date": "2030-06-02"}],
            read_only=True,
        )
        with self.assertRaises(HTTPException) as caught:
            await runtime.respond("Reserve o salão")
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(self.models["reservas"].requests, [])

    async def test_missing_wrong_scope_and_stale_envelope_cannot_execute(self):
        runtime = await self.build([])
        runtime._busy = True
        runtime._turn_id = "new-turn"
        runtime._invocation_id = "new-invocation"
        runtime._execution_lock = asyncio.Lock()
        context = SimpleNamespace(
            user_id="owner",
            session=SimpleNamespace(id=str(runtime.identity.session_id)),
            invocation_id="new-invocation",
            agent_name="convivencia",
            actions=SimpleNamespace(),
        )
        with self.assertRaises(HTTPException):
            await runtime._execute("convivencia", context)
        from services.agent.models.delegation_envelope import DelegationEnvelope

        envelope = DelegationEnvelope(
            "new-turn",
            "new-invocation",
            str(runtime.identity.session_id),
            "owner",
            "convivencia",
            DelegatedRequest(operation="propose_visit", name="QA", date="2030-06-02"),
        )
        for changes in (
            {"turn_id": "old-turn"},
            {"invocation_id": "old-invocation"},
            {"session_id": str(uuid4())},
            {"resident_id": "foreign"},
            {"specialist": "reservas"},
        ):
            runtime._envelope = replace(envelope, **changes)
            with self.assertRaises(HTTPException):
                await runtime._execute("convivencia", context)
        self.actions.authorize_visit.assert_not_called()
