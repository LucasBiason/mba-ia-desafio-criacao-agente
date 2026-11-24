from .contract_model import ContractModel
from .pending_confirmation import PendingConfirmation


class MessageResponse(ContractModel):
    """Shared message/confirmation response; empty text is explicitly allowed."""

    resposta: str
    confirmacoes_pendentes: list[PendingConfirmation]
