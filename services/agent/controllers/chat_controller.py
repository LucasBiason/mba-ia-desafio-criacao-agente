from uuid import uuid4
from fastapi import HTTPException
import httpx
from services.agent.runtime.limits import AGENT_UPSTREAM_READ_TIMEOUT_SECONDS

from microservice_toolkit import error

from services.agent.models.chat_session import ChatSession
from services.agent.repositories.chat_repository import ChatRepository
from services.agent.serializers.chat_serializer import ChatSerializer
from services.agent.validators.chat_validator import ChatValidator
from aurora_toolkit.identity import internal_request


class ChatController:
    def create(self, data, actor):
        with ChatRepository() as repository:
            ChatValidator(repository).validate_create(data, actor)
            # validate_create holds the apartment row lock, serializing concurrent
            # get-or-create across workers. Legacy rows are preserved untouched.
            existing = [
                item
                for item in repository.list(actor["id"])
                if item.apartment == data.apartment
            ]
            if existing:
                return ChatSerializer.serialize(
                    min(existing, key=lambda item: (item.created_at, str(item.id)))
                )
            record = ChatSession(
                id=uuid4(), apartment=data.apartment, resident_id=actor["id"]
            )
            return ChatSerializer.serialize(repository.create(record))

    def list(self, actor):
        with ChatRepository() as repository:
            ChatValidator(repository).validate_list(actor)
            return [
                ChatSerializer.serialize(record)
                for record in repository.list(actor["id"])
            ]

    def get(self, session_id, actor):
        with ChatRepository() as repository:
            return ChatSerializer.serialize(
                ChatValidator(repository).validate_read(session_id, actor)
            )

    def send(self, session_id, data, actor):
        with ChatRepository() as repository:
            record = ChatValidator(repository).validate_read(session_id, actor)
            apartment = record.apartment
        response = internal_request(
            "agent",
            "POST",
            "/internal/chat/messages",
            timeout=httpx.Timeout(3, read=AGENT_UPSTREAM_READ_TIMEOUT_SECONDS),
            payload={
                "session_id": str(session_id),
                "apartment": apartment,
                "user_id": actor["id"],
                "message": data.message,
            },
        )
        try:
            payload = response.json()
        except ValueError:
            raise error(
                503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento."
            ) from None
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if (
            response.status_code == 429
            and isinstance(detail, dict)
            and detail.get("code") in ("AGENT_RATE_LIMITED", "AGENT_CAPACITY_EXCEEDED")
        ):
            raise error(
                429,
                detail["code"],
                "O limite de mensagens ou de atendimentos simultâneos foi atingido. Aguarde antes de tentar novamente.",
            )
        if (
            response.status_code == 503
            and isinstance(detail, dict)
            and detail.get("code") == "AGENT_NOT_PREPARED"
        ):
            raise error(
                503,
                "AGENT_NOT_PREPARED",
                "O assistente precisa ser preparado pela administração.",
            )
        if (
            response.status_code == 409
            and isinstance(detail, dict)
            and detail.get("code") == "CHAT_SESSION_CONFLICT"
        ):
            raise error(
                409,
                "CHAT_SESSION_CONFLICT",
                "Outra mensagem alterou esta conversa. Atualize a sessão antes de tentar novamente.",
            )
        if (
            response.status_code == 503
            and isinstance(detail, dict)
            and detail.get("code") == "AGENT_NOT_CONFIGURED"
        ):
            raise error(
                503,
                "AGENT_NOT_CONFIGURED",
                "A consultoria por agentes ainda será implementada.",
            )
        if (
            response.status_code == 503
            and isinstance(detail, dict)
            and detail.get("code") == "AGENT_QUOTA_EXCEEDED"
        ):
            raise error(
                503,
                "AGENT_QUOTA_EXCEEDED",
                "A cota gratuita do Gemini foi atingida. Aguarde antes de enviar outra mensagem. "
                "Confira os registros antes de repetir uma ação; não houve tentativa automática.",
            )
        if not response.is_success:
            raise error(
                503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento."
            )
        return payload

    def internal_message(self, data):
        raise error(
            503,
            "AGENT_NOT_CONFIGURED",
            "A consultoria por agentes ainda será implementada.",
        )

    def send_recorded(self, session_id, data, actor, *, history_enabled):
        from services.agent.runtime.portal_history import (
            append_message,
            append_result_safely,
        )

        if history_enabled:
            self.get(session_id, actor)
            append_message(session_id, "user", data.message)
        try:
            result = self.send(session_id, data, actor)
        except HTTPException as exc:
            if history_enabled and isinstance(exc.detail, dict):
                public_failures = {
                    "AGENT_NOT_CONFIGURED": "O assistente está indisponível no momento. Sua conversa foi preservada; tente novamente mais tarde.",
                    "AGENT_QUOTA_EXCEEDED": "A cota gratuita do Gemini foi atingida. Aguarde antes de tentar novamente; confira os registros antes de repetir uma ação.",
                }
                if exc.detail.get("code") in public_failures:
                    append_result_safely(
                        session_id, public_failures[exc.detail["code"]]
                    )
            raise
        if history_enabled and not append_result_safely(
            session_id, result.get("message", "")
        ):
            result["history_saved"] = False
        return result

    async def history(self, session_id, actor, service, **options):
        from services.agent.runtime.portal_history import history

        return await history(session_id, actor, service, **options)

    def archive(self, session_id, actor, *, restore=False):
        from services.agent.runtime.portal_history import archive

        return archive(session_id, actor, restore=restore)

    def decide(self, session_id, data, actor, *, history_enabled):
        from services.agent.models.session_identity import SessionIdentity
        from services.agent.runtime.resident_actions import ProductActions
        from services.agent.runtime.portal_history import append_result_safely

        result = ProductActions(
            SessionIdentity.from_authenticated_actor(session_id, actor)
        ).decide(data.id, data.confirmado)
        if history_enabled and not append_result_safely(session_id, result["message"]):
            result["history_saved"] = False
        return result
