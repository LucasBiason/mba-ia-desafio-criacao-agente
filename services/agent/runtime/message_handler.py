"""Adaptador interno de leitura, ativado somente por injeção explícita."""

import asyncio
from uuid import UUID

from google.adk.errors._stale_session_error import StaleSessionError
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.genai.errors import APIError
from microservice_toolkit import error

from services.agent.repositories.session_store_not_prepared import (
    SessionStoreNotPrepared,
)
from services.agent.runtime.limits import AGENT_EXECUTION_TIMEOUT_SECONDS
from services.agent.runtime.read_runner import ReadOnlyAgentRuntime
from services.agent.tools.reservation_read import SessionIdentity
from services.agent.validators.chat_validator import ChatValidator


class ReadOnlyMessageHandler:
    def __init__(
        self,
        *,
        identity_loader,
        repository_factory,
        tool_factory,
        model_factory,
        session_service,
        runtime_factory=None,
        portal_preflight=None,
        admission_repository_factory=None,
    ):
        self.identity_loader = identity_loader
        self.repository_factory = repository_factory
        self.tool_factory = tool_factory
        self.model_factory = model_factory
        self.session_service = session_service
        self.runtime_factory = runtime_factory or ReadOnlyAgentRuntime
        self.portal_preflight = portal_preflight
        self.admission_repository_factory = admission_repository_factory

    def _authorize(self, data):
        actor = self.identity_loader(data.user_id)
        if actor.get("id") != data.user_id:
            raise error(401, "INVALID_SESSION", "Identidade inválida.")
        try:
            session_id = UUID(data.session_id)
        except ValueError:
            raise error(404, "SESSION_NOT_FOUND", "Sessão não encontrada.") from None
        identity = SessionIdentity.from_authenticated_actor(session_id, actor)
        with self.repository_factory() as repository:
            record = ChatValidator(repository).validate_read(session_id, actor)
            if record.apartment != data.apartment:
                raise error(404, "SESSION_NOT_FOUND", "Sessão não encontrada.")
        return identity

    async def __call__(self, data):
        try:
            async with asyncio.timeout(AGENT_EXECUTION_TIMEOUT_SECONDS):
                return await self._respond(data)
        except TimeoutError:
            raise error(
                503,
                "AGENT_UNAVAILABLE",
                "A consultoria excedeu o tempo de resposta. Atualize a sessão antes de tentar novamente.",
            ) from None
        except APIError as exc:
            if getattr(exc, "code", None) == 429:
                raise error(
                    503,
                    "AGENT_QUOTA_EXCEEDED",
                    "A cota gratuita do Gemini foi atingida. Aguarde antes de enviar outra mensagem. "
                    "Não repetimos automaticamente o pedido; confira os registros antes de tentar uma ação novamente.",
                ) from None
            raise error(
                503, "AGENT_UNAVAILABLE", "O provedor do assistente está indisponível."
            ) from None
        except SessionStoreNotPrepared:
            raise error(
                503,
                "AGENT_NOT_PREPARED",
                "O histórico do assistente precisa ser preparado pela administração.",
            ) from None
        except StaleSessionError:
            # O banco detecta disputa inclusive entre processos. Não repetir o
            # Runner automaticamente: já pode haver eventos persistidos.
            raise error(
                409,
                "CHAT_SESSION_CONFLICT",
                "Outra mensagem alterou esta conversa. Atualize a sessão antes de tentar novamente.",
            ) from None

    async def _respond(self, data):
        # Nunca confiar no apartment/user_id encaminhado pela fronteira interna.
        identity = await asyncio.to_thread(self._authorize, data)
        from services.agent.runtime.portal_intent import REFUSAL, scope_change_request

        if scope_change_request(data.message):
            return {"message": REFUSAL}
        if self.portal_preflight is not None:
            reply = await asyncio.to_thread(
                self.portal_preflight, identity, data.apartment, data.message
            )
            if reply is not None:
                return reply
        admission = (
            self.admission_repository_factory()
            if self.admission_repository_factory
            else None
        )
        lease_id = (
            await asyncio.to_thread(admission.acquire, identity) if admission else None
        )
        timed_out = False
        try:
            return await self._run_runtime(data, identity)
        except (asyncio.CancelledError, TimeoutError):
            # A cancelled to_thread effect may still finish. Keep the durable
            # lease until expiry instead of admitting an immediate second turn.
            timed_out = True
            raise
        finally:
            if admission and lease_id and not timed_out:
                try:
                    await asyncio.to_thread(admission.release, lease_id)
                except Exception:
                    # Failure to release fails closed until the durable expiry.
                    pass

    async def _run_runtime(self, data, identity):
        runtime = self.runtime_factory(
            tool=self.tool_factory(identity),
            model=self.model_factory(),
            session_service=self.session_service,
        )
        session = await self.session_service.get_session(
            app_name=runtime.APP_NAME,
            user_id=identity.resident_id,
            session_id=str(identity.session_id),
        )
        if session is None:
            try:
                await runtime.create_session()
            except AlreadyExistsError:
                pass  # Outra requisição criou a mesma sessão; não a sobrescrever.
        try:
            events = await runtime.respond(data.message)
        except APIError:
            # A successful transaction result is stronger evidence than provider
            # failure after a tool. Never replay the mutation to recover prose.
            actions = getattr(runtime, "actions", None)
            if actions is not None and actions.results:
                return await asyncio.to_thread(runtime.project_message, "")
            raise
        # Apenas texto final, sem expor eventos internos ou argumentos de tools.
        text = "\n".join(
            part.text
            for event in events
            if event.is_final_response() and event.content
            for part in event.content.parts or []
            if part.text and not part.thought
        )
        if callable(getattr(runtime, "project_message", None)):
            return await asyncio.to_thread(runtime.project_message, text)
        if not text:
            raise error(
                503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento."
            )
        return {"message": text}
