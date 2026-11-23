"""Separate portal-only decision route, wired solely by explicit test profile."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, StrictBool
from aurora_toolkit.identity import authenticated_user
from services.agent.runtime.resident_actions import ProductActions
from services.agent.tools.reservation_read import SessionIdentity

router = APIRouter(tags=["Confirmações do assistente"])


class ConfirmationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    confirmado: StrictBool


@router.post("/api/resident/chat/sessions/{session_id}/confirmations")
def decide(
    session_id: UUID,
    data: ConfirmationInput,
    actor: Annotated[dict, Depends(authenticated_user)],
    request: Request,
):
    identity = SessionIdentity.from_authenticated_actor(session_id, actor)
    result = ProductActions(identity).decide(data.id, data.confirmado)
    if getattr(request.app.state, "portal_history_enabled", False):
        from services.agent.runtime.portal_history import append_result_safely

        if not append_result_safely(session_id, result["message"]):
            result["history_saved"] = False
    return result
