"""Strict JSON DTOs for the six routes of the official academic contract."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel, field_validator


class ContractModel(BaseModel):
    """Fixed contract fields, without implicit coercion or unknown keys."""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)


class SessionInput(ContractModel):
    """Apartment chosen by the academic evaluator (authentication is out of scope)."""

    apartamento: str = Field(min_length=1, max_length=32)


class MessageInput(ContractModel):
    """Text to submit to the session's agent."""

    texto: str = Field(min_length=1, max_length=4000)


class ConfirmationInput(ContractModel):
    """Decision only; operation details are retrieved server-side."""

    id: str = Field(min_length=1, max_length=256)
    confirmado: bool


class SessionResponse(ContractModel):
    """Identifier returned by POST /sessoes."""

    session_id: str


class PendingConfirmation(ContractModel):
    """Fixed envelope with unrestricted JSON keys inside detalhes."""

    id: str
    acao: str
    detalhes: dict[str, JsonValue]


class MessageResponse(ContractModel):
    """Shared message/confirmation response; empty text is explicitly allowed."""

    resposta: str
    confirmacoes_pendentes: list[PendingConfirmation]


IsoDay = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]


class DatedRecord(ContractModel):
    """Public verification records expose dates as ISO strings, not datetimes."""

    data: IsoDay

    @field_validator("data")
    @classmethod
    def valid_calendar_day(cls, value: str) -> str:
        """Reject impossible calendar dates without altering the wire value."""
        date.fromisoformat(value)
        return value


class ReservationRead(DatedRecord):
    """Direct reservation verification, without owner/internal database fields."""

    codigo: str
    area: str


class VisitorRead(DatedRecord):
    """Direct visitor verification, without owner/internal database fields."""

    nome: str


class EventsResponse(RootModel[list[dict[str, JsonValue]]]):
    """Ordered raw JSON event objects; no filtering or ADK-specific schema."""

    model_config = ConfigDict(strict=True, hide_input_in_errors=True)
