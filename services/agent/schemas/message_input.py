from pydantic import Field
from microservice_toolkit.schemas import RequestSchema


class MessageInput(RequestSchema):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="Mensagem do morador para a unidade fixa da sessão.",
    )
