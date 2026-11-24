from pydantic import JsonValue

from .contract_model import ContractModel


class PendingConfirmation(ContractModel):
    """Fixed envelope with unrestricted JSON keys inside detalhes."""

    id: str
    acao: str
    detalhes: dict[str, JsonValue]
