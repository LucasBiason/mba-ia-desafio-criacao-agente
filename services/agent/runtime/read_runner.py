"""Composição de leitura ADK com dependências explícitas e identidade fixa.

Não cria cliente Gemini, não lê segredos e não oferece operações de escrita.
O chamador autentica o morador e constrói uma instância por sessão autorizada.
"""

import asyncio

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.apps import App
from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.adk.tools import FunctionTool
from google.genai import types


class ReadOnlyAgentRuntime:
    APP_NAME = "aurora_read_probe"
    MAX_LLM_CALLS = 4

    def __init__(self, *, tool, model, session_service):
        if not isinstance(model, BaseLlm):
            raise TypeError(
                "Injete um BaseLlm explícito; nomes de modelos não são aceitos."
            )
        self._validate_access = tool.validate_access
        self.identity = tool.identity
        self.session_service = session_service

        async def list_my_reservations() -> dict:
            """Lista as reservas ativas do morador e da unidade fixa desta sessão."""
            # Repositório e identidade HTTP síncronos são criados/usados na mesma
            # thread, sem bloquear o event loop do Runner.
            return await asyncio.to_thread(tool.list_my_reservations)

        self.function_tool = FunctionTool(list_my_reservations)
        specialist = LlmAgent(
            name="reservas",
            model=model,
            instruction="Consulte reservas com a ferramenta. Não invente dados nem realize alterações.",
            tools=[self.function_tool],
        )
        self.runner = Runner(
            app=App(name=self.APP_NAME, root_agent=specialist),
            session_service=session_service,
        )

    async def create_session(self):
        """Criação explícita: duplicatas são erro; não substitui a sessão de domínio."""
        await asyncio.to_thread(self._validate_access)
        return await self.session_service.create_session(
            app_name=self.APP_NAME,
            user_id=self.identity.resident_id,
            session_id=str(self.identity.session_id),
        )

    async def respond(self, text: str):
        """Retorna eventos ADK internos; não define/altera contrato HTTP acadêmico."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("A mensagem deve conter texto.")
        # O modelo pode responder diretamente do histórico sem invocar tools.
        # Autorize ANTES de Runner acessar esse histórico ou produzir eventos.
        await asyncio.to_thread(self._validate_access)
        return [
            event
            async for event in self.runner.run_async(
                user_id=self.identity.resident_id,
                session_id=str(self.identity.session_id),
                new_message=types.Content(role="user", parts=[types.Part(text=text)]),
                run_config=RunConfig(max_llm_calls=self.MAX_LLM_CALLS),
            )
        ]
