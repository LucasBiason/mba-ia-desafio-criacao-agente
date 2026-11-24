from pydantic import BaseModel, Field
from services.agent.schemas.history_message import HistoryMessage
from services.agent.schemas.pending_confirmation import PendingConfirmation


class HistoryRead(BaseModel):
    messages: list[HistoryMessage] = Field(
        description="Página em ordem cronológica, limitada no banco antes da materialização."
    )
    next_cursor: str | None = Field(
        None,
        description="Cursor opaco para itens anteriores; pode existir em página vazia com eventos internos.",
    )
    confirmacoes_pendentes: list[PendingConfirmation] = Field(
        description="Propostas duráveis pendentes de todas as sessões próprias da unidade."
    )
    actions_enabled: bool = Field(
        False,
        description="Permite decidir propostas somente quando a composição de ações está ativa; pendências continuam visíveis com o modelo desativado.",
    )
    archived: bool = Field(
        description="Há um corte de exibição arquivado; os registros não foram apagados."
    )
