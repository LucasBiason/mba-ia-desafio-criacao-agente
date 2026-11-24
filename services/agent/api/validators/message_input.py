from pydantic import Field

from .contract_model import ContractModel


class MessageInput(ContractModel):
    """Text to submit to the session's agent."""

    texto: str = Field(min_length=1, max_length=4000)
