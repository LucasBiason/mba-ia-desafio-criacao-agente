from pydantic import BaseModel, Field
from services.agent.schemas.pending_confirmation import PendingConfirmation
from services.agent.schemas.action_result import ActionResult


class MessageReply(BaseModel):
    message: str = Field(
        description="Resposta pública em português, sem instruções internas do agente."
    )
    confirmacoes_pendentes: list[PendingConfirmation] | None = Field(
        None, description="Propostas que ainda exigem Aprovar ou Negar no portal."
    )
    resultado: ActionResult | None = Field(
        None, description="Recibo do efeito transacional ou da recusa."
    )
    history_saved: bool | None = Field(
        None,
        description="False indica falha de transcript após resposta; não repita um efeito.",
    )
    pending_refresh_failed: bool | None = Field(
        None, description="True preserva o recibo mas exige atualizar as confirmações."
    )
