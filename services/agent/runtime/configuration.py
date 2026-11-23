"""Wiring opt-in. Importar este módulo não lê ambiente, credenciais ou rede."""

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from importlib.metadata import version


@dataclass(frozen=True)
class AgentRuntimeSettings:
    enabled: bool = False
    model: str = ""
    database_url: str = field(default="", repr=False)
    actions_enabled: bool = False
    history_enabled: bool = False

    def validate(self):
        if not self.enabled:
            return
        if not self.model.startswith("gemini-") or "/" in self.model:
            raise ValueError("Selecione explicitamente um modelo Gemini AI Studio.")
        if not self.database_url.startswith(
            ("sqlite+aiosqlite:///", "postgresql+asyncpg://")
        ):
            raise ValueError(
                "Configure persistência SQLite ou PostgreSQL assíncrona dedicada ao ADK."
            )
        if ":memory:" in self.database_url:
            raise ValueError("O runtime configurado exige persistência em disco.")


def configure_read_agent(app, settings, *, credential_provider):
    """Opt-in deliberado na composição; nenhuma ativação automática por .env.

    credential_provider é invocado somente após autorização da primeira mensagem.
    Não passe segredos em settings nem registre seu valor. Em produção, ativar
    esta composição significa permitir envio de conversa/dados ao provedor.
    """
    settings.validate()
    if not settings.enabled:
        return
    if getattr(app.state, "agent_message_handler", None) is not None:
        raise ValueError("Runtime já configurado; não substituir recursos ativos.")
    if version("google-adk") != "2.9.1":
        raise ValueError("Esta composição foi validada somente com google-adk==2.9.1.")
    from google.adk.models.google_llm import Gemini
    from google.adk.sessions import DatabaseSessionService
    from google.genai import types
    from services.agent.runtime.provider_transport import (
        AI_STUDIO_BASE_URL,
        create_provider_clients,
        provider_ssl_context,
    )
    from services.agent.runtime.limits import MODEL_HTTP_TIMEOUT_MS
    from microservice_toolkit import error
    from aurora_toolkit.identity import fetch_user
    from services.agent.repositories.reservation_tool_repository import (
        ReservationToolRepository,
    )
    from services.agent.runtime.message_handler import ReadOnlyMessageHandler
    from services.agent.tools.reservation_read import ReservationReadTool

    db = DatabaseSessionService(db_url=settings.database_url)
    models = []
    transports = []

    def model_factory():
        if not models:
            key = credential_provider()
            if not isinstance(key, str) or not key.strip():
                raise error(
                    503, "AGENT_NOT_CONFIGURED", "Credencial do agente não configurada."
                )
            context = provider_ssl_context()
            sync_client, async_client = create_provider_clients()
            transports.append((sync_client, async_client))
            models.append(
                Gemini(
                    model=settings.model,
                    base_url=AI_STUDIO_BASE_URL,
                    client_kwargs={
                        "api_key": key,
                        "vertexai": False,
                        "http_options": types.HttpOptions(
                            timeout=MODEL_HTTP_TIMEOUT_MS,
                            base_url=AI_STUDIO_BASE_URL,
                            client_args={"verify": context, "trust_env": False},
                            async_client_args={
                                "verify": context,
                                "ssl": context,
                                "trust_env": False,
                            },
                            httpx_client=sync_client,
                            httpx_async_client=async_client,
                            retry_options=types.HttpRetryOptions(attempts=1),
                        ),
                    },
                )
            )
        return models[0]

    from services.agent.runtime.multi_agent_read import MultiAgentReadRuntime
    from services.agent.tools.regulation_read import RegulationReadTool

    def runtime_factory(*, tool, model, session_service):
        runtime_class = MultiAgentReadRuntime
        options = {}
        if settings.actions_enabled:
            from services.agent.runtime.multi_agent_actions import (
                MultiAgentActionRuntime,
            )
            from services.agent.runtime.resident_actions import ProductActions

            runtime_class = MultiAgentActionRuntime
            options["actions"] = ProductActions(tool.identity)
        return runtime_class(
            tool=tool,
            models={role: model for role in ("principal", "reservas", "convivencia")},
            session_service=session_service,
            regulation_tool=RegulationReadTool(tool),
            **options,
        )

    def portal_preflight(identity, apartment, message):
        from services.agent.runtime.portal_intent import portal_reply
        from services.agent.runtime.resident_actions import ProductActions

        actions = ProductActions(identity)
        reply = portal_reply(message, apartment, actions)
        if reply is not None:
            return reply
        from services.agent.tools.regulation_read import is_reservation_notice_question

        if is_reservation_notice_question(message):
            result = RegulationReadTool(
                ReservationReadTool(identity)
            ).consultar_regulamento(message)
            if result.get("status") == "found":
                text = f"Regulamento versão {result['version']}:\n{result['excerpt']}"
            else:
                text = (
                    result.get("message")
                    if result.get("status") == "not_specified"
                    else "Não consegui confirmar uma regra específica de antecedência ou cancelamento na edição vigente. "
                    "Isso não permite concluir que não existe prazo ou multa. Confirme as condições com a administração."
                )
            return {"message": text, "confirmacoes_pendentes": actions.pending()}
        return None

    handler = ReadOnlyMessageHandler(
        identity_loader=fetch_user,
        repository_factory=ReservationToolRepository,
        tool_factory=ReservationReadTool,
        model_factory=model_factory,
        session_service=db,
        runtime_factory=runtime_factory,
        portal_preflight=portal_preflight if settings.actions_enabled else None,
    )
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        try:
            async with original_lifespan(application) as state:
                import asyncio

                if settings.history_enabled:
                    from services.agent.runtime.portal_history import prepare_history

                    await asyncio.to_thread(prepare_history)
                if settings.actions_enabled:
                    from services.agent.runtime.resident_actions import (
                        prepare_product_actions,
                    )

                    await asyncio.to_thread(prepare_product_actions)
                yield state
        finally:
            try:
                await db.close()
            finally:
                for sync_client, async_client in transports:
                    await async_client.aclose()
                    sync_client.close()

    app.router.lifespan_context = lifespan
    app.state.agent_message_handler = handler
    app.state.agent_session_service = db
    app.state.portal_history_enabled = settings.history_enabled
    app.state.resident_actions_enabled = settings.actions_enabled


def configure_from_environment(app, environ):
    """Explicit deployment opt-in; disabled is inert and never reads the key."""
    if environ.get("AURORA_AGENT_ENABLED", "0") != "1":
        return
    settings = AgentRuntimeSettings(
        True,
        environ.get("AURORA_AGENT_MODEL", ""),
        environ.get("AURORA_AGENT_SESSION_DATABASE_URL", ""),
        actions_enabled=environ.get("AURORA_RESIDENT_ACTIONS", "0") == "1",
        history_enabled=True,
    )
    configure_read_agent(
        app, settings, credential_provider=lambda: environ.get("GOOGLE_API_KEY", "")
    )
