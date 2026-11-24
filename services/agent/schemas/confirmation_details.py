from datetime import date
from pydantic import BaseModel, Field


class ConfirmationDetails(BaseModel):
    data: date = Field(description="Data do pedido no formato AAAA-MM-DD.")
    area: str | None = Field(
        None, description="Identificador da área para uma reserva."
    )
    taxa: float | None = Field(
        None, ge=0, description="Taxa em reais apresentada para aprovação."
    )
    nome: str | None = Field(None, description="Nome do visitante proposto.")
    hora_inicio: str | None = Field(
        None, description="Horário inicial, quando informado pelo contrato."
    )
    hora_fim: str | None = Field(
        None, description="Horário final, quando informado pelo contrato."
    )
