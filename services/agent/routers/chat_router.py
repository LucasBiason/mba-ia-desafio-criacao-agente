from typing import Annotated
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from aurora_toolkit.identity import authenticated_user, verify_internal

from uuid import UUID
from services.agent.controllers.chat_controller import ChatController
from services.agent.schemas.chat_read import ChatRead
from services.agent.schemas.session_input import SessionInput
from services.agent.schemas.message_input import MessageInput
from services.agent.schemas.internal_message import InternalMessage

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Assistente"])
controller = ChatController()


def message_handler(request: Request):
    """Runtime desativado por padrão; testes podem injetar a composição fake.

    Sem import ADK, flag de ambiente ou provedor implícito no deploy atual.
    """
    return getattr(request.app.state, "agent_message_handler", None)


@router.post(
    "/api/resident/chat/sessions",
    response_model=ChatRead,
    status_code=201,
    summary="Abrir sessão em uma unidade vinculada",
)
def create_session(data: SessionInput, actor: Actor):
    return controller.create(data, actor)


@router.get(
    "/api/resident/chat/sessions",
    response_model=list[ChatRead],
    summary="Listar sessões próprias",
)
def list_sessions(actor: Actor):
    return controller.list(actor)


@router.get(
    "/api/resident/chat/sessions/{session_id}",
    response_model=ChatRead,
    summary="Retomar sessão própria",
)
def get_session(session_id: UUID, actor: Actor):
    return controller.get(session_id, actor)


@router.post(
    "/api/resident/chat/sessions/{session_id}/messages",
    response_model=dict,
    summary="Enviar mensagem à consultoria",
)
def send_message(session_id: UUID, data: MessageInput, actor: Actor, request: Request):
    enabled = getattr(request.app.state, "portal_history_enabled", False)
    if enabled:
        controller.get(session_id, actor)
        from services.agent.runtime.portal_history import append_message

        append_message(session_id, "user", data.message)
    try:
        result = controller.send(session_id, data, actor)
    except HTTPException as exc:
        if (
            enabled
            and isinstance(exc.detail, dict)
            and exc.detail.get("code") == "AGENT_QUOTA_EXCEEDED"
        ):
            from services.agent.runtime.portal_history import append_result_safely

            append_result_safely(
                session_id,
                "A cota gratuita do Gemini foi atingida. Aguarde antes de tentar novamente; confira os registros antes de repetir uma ação.",
            )
        raise
    if enabled:
        from services.agent.runtime.portal_history import append_result_safely

        if not append_result_safely(session_id, result.get("message", "")):
            result["history_saved"] = False
    return result


@router.post(
    "/internal/chat/messages",
    response_model=dict,
    dependencies=[Depends(verify_internal)],
    summary="Executar fronteira interna da consultoria",
)
async def internal_message(data: InternalMessage, handler=Depends(message_handler)):
    if handler is None:
        return controller.internal_message(data)
    return await handler(data)


@router.get("/api/resident/chat/sessions/{session_id}/history")
async def get_history(
    session_id: UUID,
    actor: Actor,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    before: str | None = None,
):
    require_history(request)
    from services.agent.runtime.portal_history import history

    return await history(
        session_id,
        actor,
        getattr(request.app.state, "agent_session_service", None),
        limit=limit,
        before=before,
        include_pending=getattr(request.app.state, "resident_actions_enabled", False),
    )


@router.post("/api/resident/chat/sessions/{session_id}/archive")
def archive_history(session_id: UUID, actor: Actor, request: Request):
    require_history(request)
    from services.agent.runtime.portal_history import archive

    return archive(session_id, actor)


@router.post("/api/resident/chat/sessions/{session_id}/restore")
def restore_history(session_id: UUID, actor: Actor, request: Request):
    require_history(request)
    from services.agent.runtime.portal_history import archive

    return archive(session_id, actor, restore=True)


def require_history(request):
    if not getattr(request.app.state, "portal_history_enabled", False):
        raise HTTPException(404, detail="Histórico não habilitado nesta composição.")
