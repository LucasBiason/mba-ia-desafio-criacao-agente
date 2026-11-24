"""Rotas privadas da conversa e fronteira interna autenticada do agente."""

from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from aurora_toolkit.identity import authenticated_user, verify_internal
from services.agent.controllers.chat_controller import ChatController
from services.agent.schemas.chat_read import ChatRead
from services.agent.schemas.session_input import SessionInput
from services.agent.schemas.message_input import MessageInput
from services.agent.schemas.internal_message import InternalMessage
from services.agent.schemas.message_reply import MessageReply
from services.agent.schemas.history_read import HistoryRead
from services.agent.schemas.archive_read import ArchiveRead

Actor = Annotated[dict, Depends(authenticated_user)]
router = APIRouter(tags=["Assistente"])
controller = ChatController()
PRIVATE_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Sessão inválida ou expirada (INVALID_SESSION)."},
    403: {"description": "Somente moradores vinculados podem acessar a conversa."},
    404: {
        "description": "Sessão não encontrada ou não pertencente ao morador (SESSION_NOT_FOUND)."
    },
    422: {
        "description": "Corpo, UUID, tamanho da página ou cursor inválido (INVALID_HISTORY_CURSOR)."
    },
}
MESSAGE_ERRORS: dict[int | str, dict[str, Any]] = {
    **PRIVATE_ERRORS,
    409: {
        "description": "Mensagem concorrente na sessão (CHAT_SESSION_CONFLICT). Atualize o histórico; não há repetição automática."
    },
    429: {
        "description": "Admissão recusada por taxa ou concorrência: AGENT_RATE_LIMITED ou AGENT_CAPACITY_EXCEEDED."
    },
    503: {
        "description": "Agente desativado, banco sem preparo explícito, provedor indisponível ou cota excedida: AGENT_NOT_CONFIGURED, AGENT_NOT_PREPARED, AGENT_UNAVAILABLE ou AGENT_QUOTA_EXCEEDED."
    },
}


def message_handler(request: Request):
    """Obtém o runtime configurado explicitamente na composição do serviço."""
    return getattr(request.app.state, "agent_message_handler", None)


@router.post(
    "/api/resident/chat/sessions",
    response_model=ChatRead,
    status_code=201,
    summary="Abrir sessão em uma unidade vinculada",
    responses=PRIVATE_ERRORS,
)
def create_session(data: SessionInput, actor: Actor):
    """Abre ou retoma a sessão própria mais antiga, preservando sessões legadas."""
    return controller.create(data, actor)


@router.get(
    "/api/resident/chat/sessions",
    response_model=list[ChatRead],
    summary="Listar sessões próprias",
    responses=PRIVATE_ERRORS,
)
def list_sessions(actor: Actor):
    """Lista apenas sessões ainda autorizadas para os vínculos atuais do morador."""
    return controller.list(actor)


@router.get(
    "/api/resident/chat/sessions/{session_id}",
    response_model=ChatRead,
    summary="Retomar sessão própria",
    responses=PRIVATE_ERRORS,
)
def get_session(session_id: UUID, actor: Actor):
    """Revalida a propriedade e o vínculo antes de devolver a sessão solicitada."""
    return controller.get(session_id, actor)


@router.post(
    "/api/resident/chat/sessions/{session_id}/messages",
    response_model=MessageReply,
    response_model_exclude_none=True,
    summary="Enviar mensagem à consultoria",
    responses=MESSAGE_ERRORS,
)
def send_message(session_id: UUID, data: MessageInput, actor: Actor, request: Request):
    """Envia uma mensagem da unidade fixa; resultados não são repetidos após falha."""
    return controller.send_recorded(
        session_id,
        data,
        actor,
        history_enabled=getattr(request.app.state, "portal_history_enabled", False),
    )


@router.post(
    "/internal/chat/messages",
    response_model=MessageReply,
    response_model_exclude_none=True,
    dependencies=[Depends(verify_internal)],
    summary="Executar fronteira interna da consultoria",
    responses=MESSAGE_ERRORS,
)
async def internal_message(data: InternalMessage, handler=Depends(message_handler)):
    """Exige X-Aurora-Internal-Token e revalida identidade, unidade e admissão."""
    if handler is None:
        return controller.internal_message(data)
    return await handler(data)


@router.get(
    "/api/resident/chat/sessions/{session_id}/history",
    response_model=HistoryRead,
    response_model_exclude_none=True,
    summary="Ler página do histórico contínuo da unidade",
    responses=PRIVATE_ERRORS,
)
async def get_history(
    session_id: UUID,
    actor: Actor,
    request: Request,
    limit: int = Query(
        50, ge=1, le=100, description="Número máximo de mensagens públicas por página."
    ),
    before: str | None = Query(
        None, max_length=512, description="Cursor opaco next_cursor da página anterior."
    ),
    include_archived: bool = Query(
        False, description="Inclui os itens arquivados sem apagar ou restaurar dados."
    ),
):
    """Pagina no banco antes de materializar mensagens e eventos; funciona sem modelo."""
    require_history(request)
    result = await controller.history(
        session_id,
        actor,
        getattr(request.app.state, "agent_session_service", None),
        limit=limit,
        before=before,
        include_archived=include_archived,
        include_pending=True,
    )
    result["actions_enabled"] = getattr(
        request.app.state, "resident_actions_enabled", False
    )
    return result


@router.post(
    "/api/resident/chat/sessions/{session_id}/archive",
    response_model=ArchiveRead,
    summary="Arquivar a exibição das mensagens anteriores",
    responses=PRIVATE_ERRORS,
)
def archive_history(session_id: UUID, actor: Actor, request: Request):
    """Oculta mensagens anteriores por um corte reversível, sem excluir registros."""
    require_history(request)
    return controller.archive(session_id, actor)


@router.post(
    "/api/resident/chat/sessions/{session_id}/restore",
    response_model=ArchiveRead,
    summary="Restaurar a exibição do histórico",
    responses=PRIVATE_ERRORS,
)
def restore_history(session_id: UUID, actor: Actor, request: Request):
    """Remove o corte de exibição e preserva o transcript e recibos originais."""
    require_history(request)
    return controller.archive(session_id, actor, restore=True)


def require_history(request):
    if not getattr(request.app.state, "portal_history_enabled", False):
        raise HTTPException(404, detail="Histórico não habilitado nesta composição.")
