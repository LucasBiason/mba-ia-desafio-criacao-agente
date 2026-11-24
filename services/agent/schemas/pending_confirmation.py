from typing import Literal
from pydantic import BaseModel, Field
from services.agent.schemas.confirmation_details import ConfirmationDetails


class PendingConfirmation(BaseModel):
    id: str = Field(description="Identificador durável da confirmação; consumo único.")
    acao: Literal["reservar_area", "autorizar_visitante"] = Field(
        description="Ação proposta pelo servidor."
    )
    detalhes: ConfirmationDetails = Field(
        description="Dados persistidos que o morador deve revisar."
    )
    session_id: str | None = Field(
        None, description="Sessão de origem, inclusive para propostas legadas."
    )
    sourceSessionId: str | None = Field(
        None, description="Sessão original da proposta no histórico contínuo."
    )
