from uuid import uuid4

from microservice_toolkit import error

from services.agent.models.chat_session import ChatSession
from services.agent.repositories.chat_repository import ChatRepository
from services.agent.serializers.chat_serializer import ChatSerializer
from services.agent.validators.chat_validator import ChatValidator
from services.authentication.client import internal_request


class ChatController:
    def create(self, data, actor):
        with ChatRepository() as repository:
            ChatValidator(repository).validate_create(data, actor)
            record = ChatSession(id=uuid4(), apartment=data.apartment, resident_id=actor["id"])
            return ChatSerializer.serialize(repository.create(record))

    def list(self, actor):
        with ChatRepository() as repository:
            ChatValidator(repository).validate_list(actor)
            return [ChatSerializer.serialize(record) for record in repository.list(actor["id"])]

    def get(self, session_id, actor):
        with ChatRepository() as repository:
            return ChatSerializer.serialize(ChatValidator(repository).validate_read(session_id, actor))

    def send(self, session_id, data, actor):
        with ChatRepository() as repository:
            record = ChatValidator(repository).validate_read(session_id, actor)
            apartment = record.apartment
        response = internal_request("agent", "POST", "/internal/chat/messages", payload={
            "session_id": str(session_id), "apartment": apartment, "user_id": actor["id"], "message": data.message,
        })
        try:
            payload = response.json()
        except ValueError:
            raise error(503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento.") from None
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if response.status_code == 503 and isinstance(detail, dict) and detail.get("code") == "AGENT_NOT_CONFIGURED":
            raise error(503, "AGENT_NOT_CONFIGURED", "A consultoria por agentes ainda será implementada.")
        if not response.is_success:
            raise error(503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento.")
        return payload

    def internal_message(self, data):
        raise error(503, "AGENT_NOT_CONFIGURED", "A consultoria por agentes ainda será implementada.")
