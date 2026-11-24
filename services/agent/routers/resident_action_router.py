"""Decisão externa do morador; o corpo nunca contém argumentos da operação."""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from aurora_toolkit.identity import authenticated_user
from services.agent.controllers.chat_controller import ChatController
from services.agent.schemas.confirmation_input import ConfirmationInput
from services.agent.schemas.message_reply import MessageReply
from services.agent.routers.chat_router import PRIVATE_ERRORS

router = APIRouter(tags=["Confirmações do assistente"])
controller = ChatController()


@router.post(
    "/api/resident/chat/sessions/{session_id}/confirmations",
    response_model=MessageReply,
    response_model_exclude_none=True,
    summary="Aprovar ou negar proposta persistida",
    responses={
        **PRIVATE_ERRORS,
        409: {
            "description": "Proposta inexistente, de outra sessão ou já consumida (CONFIRMATION_INVALID)."
        },
        503: {
            "description": "Serviço indisponível; confira o histórico e os registros antes de repetir uma decisão."
        },
    },
)
def decide(
    session_id: UUID,
    data: ConfirmationInput,
    actor: Annotated[dict, Depends(authenticated_user)],
    request: Request,
):
    """Consome uma única vez a proposta da sessão de origem, na transação do efeito."""
    return controller.decide(
        session_id,
        data,
        actor,
        history_enabled=getattr(request.app.state, "portal_history_enabled", False),
    )
