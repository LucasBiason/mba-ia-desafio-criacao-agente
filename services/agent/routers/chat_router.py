from typing import Annotated
from fastapi import APIRouter, Depends
from services.authentication.client import authenticated_user, verify_internal

Actor = Annotated[dict, Depends(authenticated_user)]

from uuid import UUID
from services.agent.controllers.chat_controller import ChatController
from services.agent.schemas.chat_read import ChatRead
from services.agent.schemas.session_input import SessionInput
from services.agent.schemas.message_input import MessageInput
from services.agent.schemas.internal_message import InternalMessage

router = APIRouter(tags=["Assistente"])
controller = ChatController()

@router.post("/api/resident/chat/sessions", response_model=ChatRead, status_code=201, summary="Abrir sessão em uma unidade vinculada")
def create_session(data: SessionInput, actor: Actor):
    return controller.create(data, actor)

@router.get("/api/resident/chat/sessions", response_model=list[ChatRead], summary="Listar sessões próprias")
def list_sessions(actor: Actor):
    return controller.list(actor)

@router.get("/api/resident/chat/sessions/{session_id}", response_model=ChatRead, summary="Retomar sessão própria")
def get_session(session_id: UUID, actor: Actor):
    return controller.get(session_id, actor)

@router.post("/api/resident/chat/sessions/{session_id}/messages", response_model=dict, summary="Enviar mensagem à consultoria")
def send_message(session_id: UUID, data: MessageInput, actor: Actor):
    return controller.send(session_id, data, actor)

@router.post("/internal/chat/messages", response_model=dict, dependencies=[Depends(verify_internal)], summary="Executar fronteira interna da consultoria")
def internal_message(data: InternalMessage):
    return controller.internal_message(data)
