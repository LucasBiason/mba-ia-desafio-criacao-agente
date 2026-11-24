from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Literal


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(description="Identificador durável da sessão privada.")
    apartment: str = Field(
        description="Unidade vinculada, fixada pelo servidor ao abrir a sessão."
    )
    created_at: datetime = Field(
        description="Data e hora de criação da sessão com fuso."
    )
    status: Literal["awaiting_agent"] = Field(
        "awaiting_agent",
        description="Sessão pronta para a fronteira do agente; não indica disponibilidade do provedor.",
    )

    @field_serializer("created_at")
    def serialize_timestamp(self, value):
        return value.isoformat()
