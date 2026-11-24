"""Três agentes ADK, interpretação tipada e execução vinculada ao turno."""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.apps import App
from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from google.genai.errors import APIError
from microservice_toolkit import error
from pydantic import ValidationError

from services.agent.models.delegation_envelope import DelegationEnvelope
from services.agent.runtime.read_runner import ReadOnlyAgentRuntime
from services.agent.runtime.result_projection import project_reads
from services.agent.schemas.delegated_request import DelegatedRequest
from services.agent.schemas.delegation_operation import DelegationOperation

logger = logging.getLogger(__name__)

RESERVATION_OPERATIONS = frozenset(
    ("read_reservations", "availability", "reserve", "cancel")
)
READ_OPERATIONS = frozenset(("read_reservations", "regulation", "clarify"))
EXECUTORS = {
    "reservas": "executar_reserva_validada",
    "convivencia": "executar_convivencia_validada",
}


def protocol_error():
    return error(
        503,
        "AGENT_UNAVAILABLE",
        "Não foi possível validar o pedido do assistente. Consulte o histórico antes de reenviar.",
    )


def calling_config(name):
    return types.GenerateContentConfig(
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="ANY", allowed_function_names=[name]
            )
        )
    )


class MultiAgentReadRuntime(ReadOnlyAgentRuntime):
    APP_NAME = "aurora_multi_read"
    MAX_LLM_CALLS = 6

    def __init__(self, *, tool, models, session_service, regulation_tool=None):
        if set(models) != {"principal", "reservas", "convivencia"} or not all(
            isinstance(model, BaseLlm) for model in models.values()
        ):
            raise TypeError(
                "Injete um BaseLlm por papel: principal, reservas e convivencia."
            )
        if regulation_tool is not None and regulation_tool.identity != tool.identity:
            raise ValueError(
                "A tool de regulamento deve usar a mesma identidade da sessão."
            )
        self.identity = tool.identity
        self._validate_access = tool.validate_access
        self.session_service = session_service
        self._reservation_tool = tool
        self._regulation_tool = regulation_tool
        self.read_results = []
        self._busy = False
        self._envelope = None
        self._result = None
        self._clarification = None

        async def delegar_solicitacao(
            operation: DelegationOperation,
            tool_context: ToolContext,
            area: str | None = None,
            date: str | None = None,
            name: str | None = None,
            question: str | None = None,
        ) -> dict:
            """Extrai uma solicitação atual, sem identidade ou aprovação.

            Args:
                operation: read_reservations/read_visitors listam dados; availability
                    consulta área/data; reserve reserva; cancel cancela; propose_visit
                    propõe visita; regulation consulta regulamento; clarify pede dados.
                area: Somente availability, reserve e cancel. Omitir nas demais.
                date: Data ISO AAAA-MM-DD somente em availability, reserve, cancel
                    e propose_visit. Omitir em regulation e nas listagens.
                name: Nome do visitante somente em propose_visit.
                question: Dúvida específica somente em regulation ou clarify.

            Envie somente os campos pertinentes à operação. Nunca envie papel,
            unidade, identidade, handler, destino ou confirmação.
            """
            return await self._delegate(
                {
                    "operation": operation,
                    "area": area,
                    "date": date,
                    "name": name,
                    "question": question,
                },
                tool_context,
            )

        async def executar_reserva_validada(tool_context: ToolContext) -> dict:
            """Executa o envelope de reservas validado pelo servidor, sem argumentos."""
            return await self._execute("reservas", tool_context)

        async def executar_convivencia_validada(tool_context: ToolContext) -> dict:
            """Executa o envelope de convivência validado pelo servidor, sem argumentos."""
            return await self._execute("convivencia", tool_context)

        def child(name, function):
            return LlmAgent(
                name=name,
                model=models[name],
                description=f"Executor de pedidos validados de {name}.",
                instruction="Chame imediatamente sua única ferramenta sem argumentos. O servidor já validou os dados e permissões. Não interprete novamente, não transfira e não responda em prosa.",
                tools=[FunctionTool(function)],
                generate_content_config=calling_config(EXECUTORS[name]),
                disallow_transfer_to_parent=True,
                disallow_transfer_to_peers=True,
                before_model_callback=self._before_model,
                after_model_callback=self._after_model,
                before_tool_callback=self._before_tool,
            )

        self.reservas = child("reservas", executar_reserva_validada)
        self.convivencia = child("convivencia", executar_convivencia_validada)
        principal = LlmAgent(
            name="principal",
            model=models["principal"],
            description="Extrai o pedido atual para validação pelo servidor.",
            instruction="Use delegar_solicitacao exatamente uma vez para interpretar apenas a mensagem atual. O morador está autenticado na unidade fixa; nunca peça papel, identidade ou apartamento. Reservar área usa reserve; cancelar usa cancel; disponibilidade de data usa availability; listar reservas usa read_reservations; autorizar visita de pessoa usa propose_visit; listar visitantes usa read_visitors; regras e horários do regulamento usam regulation. Extraia nomes, áreas e datas e converta datas explícitas para ISO. Envie somente area/date para availability, reserve ou cancel; name/date para propose_visit; question para regulation ou clarify; nenhum campo de negócio para listagens. Sem dados suficientes ou diante de ambiguidade use clarify. Um sim no chat nunca aprova uma pendência. Não invente dados nem regras. Não responda em texto nem use transfer_to_agent: o servidor calcula o destino.",
            tools=[FunctionTool(delegar_solicitacao)],
            generate_content_config=calling_config("delegar_solicitacao"),
            sub_agents=[self.reservas, self.convivencia],
            before_model_callback=self._before_model,
            after_model_callback=self._after_model,
            before_tool_callback=self._before_tool,
        )
        self.runner = Runner(
            app=App(name=self.APP_NAME, root_agent=principal),
            session_service=session_service,
        )

    def _check_context(self, context):
        if (
            not self._busy
            or context.user_id != self.identity.resident_id
            or context.session.id != str(self.identity.session_id)
            or context.invocation_id != self._invocation_id
        ):
            raise protocol_error()

    def _check_envelope(self, specialist, context):
        self._check_context(context)
        envelope = self._envelope
        if (
            envelope is None
            or envelope.turn_id != self._turn_id
            or envelope.invocation_id != context.invocation_id
            or envelope.session_id != str(self.identity.session_id)
            or envelope.resident_id != self.identity.resident_id
            or envelope.specialist != specialist
            or context.agent_name != specialist
        ):
            raise protocol_error()
        return envelope

    def _before_model(self, callback_context, llm_request):
        if self._invocation_id is None and callback_context.agent_name == "principal":
            self._invocation_id = callback_context.invocation_id
        self._check_context(callback_context)
        if callback_context.agent_name == "principal":
            if self._envelope is not None or self._clarification is not None:
                raise protocol_error()
            today = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
            contents = [
                types.Content(role="user", parts=[types.Part(text=self._current_text)])
            ]
            llm_request.config.system_instruction += f" Contexto do servidor: morador autenticado, unidade fixa, hoje {today}."
        else:
            envelope = self._check_envelope(
                callback_context.agent_name, callback_context
            )
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            text="Execute o pedido validado pelo servidor: "
                            + envelope.request.model_dump_json(exclude_none=True)
                        )
                    ],
                )
            ]
        llm_request.contents = contents
        # ADK anuncia transferência na raiz. Omitir a declaração reduz escolhas;
        # guardas de argumentos e de callbacks continuam sendo a fronteira real.
        llm_request.tools_dict.pop("transfer_to_agent", None)
        for tool in llm_request.config.tools or []:
            if tool.function_declarations:
                tool.function_declarations = [
                    declaration
                    for declaration in tool.function_declarations
                    if declaration.name != "transfer_to_agent"
                ]

    def _after_model(self, callback_context, llm_response):
        self._check_context(callback_context)
        parts = llm_response.content.parts if llm_response.content else []
        calls = [part.function_call for part in parts or [] if part.function_call]
        expected = (
            "delegar_solicitacao"
            if callback_context.agent_name == "principal"
            else EXECUTORS.get(callback_context.agent_name)
        )
        if (
            not calls
            or any(call.name != expected for call in calls)
            or (callback_context.agent_name == "principal" and len(calls) != 1)
        ):
            raise protocol_error()
        for call in calls:
            self._validate_arguments(callback_context.agent_name, call.args or {})

    def _validate_arguments(self, agent_name, args):
        if agent_name == "principal":
            try:
                return DelegatedRequest.model_validate(args)
            except ValidationError as exc:
                # Nunca registrar input, mensagens Pydantic, contexto, valores
                # nem nomes de chaves desconhecidas (podem conter segredos).
                failures = exc.errors(
                    include_url=False, include_context=False, include_input=False
                )
                fields = {"operation", "area", "date", "name", "question"}
                logger.warning(
                    "agent_delegation_schema_invalid schema_error_types=%s schema_fields=%s",
                    sorted({failure["type"] for failure in failures}),
                    sorted(
                        {
                            failure["loc"][0]
                            if failure["loc"] and failure["loc"][0] in fields
                            else "unknown"
                            for failure in failures
                        }
                    ),
                )
                raise protocol_error() from None
            except (TypeError, ValueError):
                logger.warning(
                    "agent_delegation_schema_invalid schema_error_types=['invalid_input'] schema_fields=[]"
                )
                raise protocol_error() from None
        if agent_name not in EXECUTORS or args:
            raise protocol_error()
        return None

    def _before_tool(self, tool, args, tool_context):
        self._check_context(tool_context)
        expected = (
            "delegar_solicitacao"
            if tool_context.agent_name == "principal"
            else EXECUTORS.get(tool_context.agent_name)
        )
        if tool.name != expected:
            raise protocol_error()
        self._validate_arguments(tool_context.agent_name, args)
        if tool_context.agent_name != "principal":
            self._check_envelope(tool_context.agent_name, tool_context)

    async def _delegate(self, args, context):
        self._check_context(context)
        if (
            context.agent_name != "principal"
            or self._envelope is not None
            or self._clarification is not None
        ):
            raise protocol_error()
        request = self._validate_arguments("principal", args)
        if request is None or request.operation.value not in self.allowed_operations():
            raise protocol_error()
        await asyncio.to_thread(self._validate_access)
        if request.operation == DelegationOperation.CLARIFY or request.missing_fields():
            self._clarification = "Informe a operação desejada e os dados necessários: área e data da reserva, ou nome e data da visita. Para consultar o regulamento, especifique a dúvida."
            context.actions.skip_summarization = True
            return {"status": "clarification_required"}
        target = (
            "reservas"
            if request.operation.value in RESERVATION_OPERATIONS
            else "convivencia"
        )
        self._envelope = DelegationEnvelope(
            self._turn_id,
            context.invocation_id,
            str(self.identity.session_id),
            self.identity.resident_id,
            target,
            request,
        )
        context.actions.transfer_to_agent = target
        return {"status": "delegated"}

    async def _execute(self, specialist, context):
        async with self._execution_lock:
            envelope = self._check_envelope(specialist, context)
            await asyncio.to_thread(self._validate_access)
            if self._result is None:
                result = await asyncio.to_thread(self._dispatch, envelope.request)
                if not isinstance(result, dict):
                    raise protocol_error()
                self._result = result
            context.actions.skip_summarization = True
            return self._result

    def allowed_operations(self):
        return READ_OPERATIONS

    def _dispatch(self, request):
        if request.operation == DelegationOperation.READ_RESERVATIONS:
            result = self._reservation_tool.list_my_reservations()
            self.read_results.append(("reservations", result))
        elif (
            request.operation == DelegationOperation.REGULATION
            and self._regulation_tool is not None
        ):
            result = self._regulation_tool.consultar_regulamento(request.question)
            self.read_results.append(("regulation", result))
        else:
            raise protocol_error()
        return result

    async def respond(self, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("A mensagem deve conter texto.")
        if self._busy:
            raise protocol_error()
        self._busy = True
        self._turn_id = str(uuid4())
        self._invocation_id = None
        self._current_text = text
        self._envelope = None
        self._result = None
        self._clarification = None
        self._execution_lock = asyncio.Lock()
        self._start_turn()
        events = []
        try:
            await asyncio.to_thread(self._validate_access)
            async for event in self.runner.run_async(
                user_id=self.identity.resident_id,
                session_id=str(self.identity.session_id),
                new_message=types.Content(role="user", parts=[types.Part(text=text)]),
                run_config=RunConfig(max_llm_calls=self.MAX_LLM_CALLS),
            ):
                events.append(event)
            if self._result is None and self._clarification is None:
                raise protocol_error()
        except Exception as exc:
            # Recibo concluído prevalece sobre geração/persistência ADK posterior.
            # Não repetimos a porta para tentar recuperar texto do provedor.
            if self._result is None:
                if isinstance(exc, (HTTPException, APIError)):
                    raise
                cause = exc.__cause__
                while cause is not None:
                    if isinstance(cause, (HTTPException, APIError)):
                        raise cause from None
                    cause = cause.__cause__
                raise protocol_error() from None
        finally:
            self._busy = False
        return events

    def _start_turn(self):
        self.read_results.clear()

    def project_message(self, text=""):
        if self._clarification is not None:
            return {"message": self._clarification}
        grounded = project_reads(self.read_results)
        if not grounded:
            raise protocol_error()
        return {"message": grounded}
