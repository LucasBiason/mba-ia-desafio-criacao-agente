from datetime import date as CalendarDate
from typing import Literal
from pydantic import BaseModel, Field


class ActionResult(BaseModel):
    status: Literal[
        "reserved",
        "cancelled",
        "authorized",
        "rejected",
        "occupied",
        "pending",
        "policy_changed",
        "policy_review_required",
        "invalid_details",
        "unknown_area",
        "not_found",
        "fee_changed",
    ] = Field(description="Resultado efetivamente confirmado pelo domínio.")
    code: str | None = Field(None, description="Código da reserva criada.")
    id: int | None = Field(None, description="Identificador da visita criada.")
    name: str | None = Field(None, description="Nome do visitante autorizado.")
    area: str | None = Field(None, description="Identificador da área reservada.")
    date: CalendarDate | None = Field(None, description="Data do efeito confirmado.")
    fee_cents: int | None = Field(
        None, ge=0, description="Taxa da reserva, em centavos."
    )
