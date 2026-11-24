from pydantic import Field

from .contract_model import ContractModel


class ConfirmationInput(ContractModel):
    """Decision only; operation details are retrieved server-side."""

    id: str = Field(min_length=1, max_length=256)
    confirmado: bool
