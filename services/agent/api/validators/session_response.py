from .contract_model import ContractModel


class SessionResponse(ContractModel):
    """Identifier returned by POST /sessoes."""

    session_id: str
