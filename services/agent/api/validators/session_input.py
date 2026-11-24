from pydantic import Field

from .contract_model import ContractModel


class SessionInput(ContractModel):
    """Apartment chosen by the academic evaluator (authentication is out of scope)."""

    apartamento: str = Field(min_length=1, max_length=32)
