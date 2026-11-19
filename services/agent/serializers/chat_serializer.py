from services.agent.schemas.chat_read import ChatRead


class ChatSerializer:
    @staticmethod
    def serialize(record):
        return ChatRead.model_validate(record)
