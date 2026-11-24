"""Transporte do protocolo público do assistente, com seis operações estáveis."""

from fastapi import APIRouter

from ..schemas import (
    ConfirmationInput,
    EventsResponse,
    MessageInput,
    MessageResponse,
    ReservationRead,
    SessionInput,
    SessionResponse,
    VisitorRead,
)
from ..validators.error_response import ErrorResponse

ERRORS = {
    404: {"model": ErrorResponse, "description": "Sessão não encontrada."},
    409: {
        "model": ErrorResponse,
        "description": "Turno concorrente, confirmação consumida ou evidência divergente.",
    },
    429: {"model": ErrorResponse, "description": "Quota do modelo esgotada."},
    503: {
        "model": ErrorResponse,
        "description": "Execução ou resultado comprovado indisponível.",
    },
}


def create_router(controller):
    router = APIRouter(tags=["Assistente do condomínio"])

    @router.post(
        "/sessoes",
        status_code=201,
        response_model=SessionResponse,
        summary="Criar sessão em um apartamento",
        responses={503: ERRORS[503]},
    )
    async def create_session(data: SessionInput):
        """Fixa o apartamento na sessão; mensagens posteriores não alteram essa identidade."""
        return await controller.create_session(data)

    @router.post(
        "/sessoes/{session_id}/mensagens",
        response_model=MessageResponse,
        summary="Enviar mensagem ao assistente",
        responses=ERRORS,
    )
    async def message(session_id: str, data: MessageInput):
        """Executa o turno e devolve texto e propostas; dizer sim no texto não confirma uma ação sensível."""
        return await controller.message(session_id, data)

    @router.post(
        "/sessoes/{session_id}/confirmacoes",
        response_model=MessageResponse,
        summary="Aprovar ou negar confirmação pendente",
        responses=ERRORS,
    )
    async def confirm(session_id: str, data: ConfirmationInput):
        """Consome a proposta original uma vez. ID inexistente ou já consumido recebe 409; negar não grava efeito."""
        return await controller.confirm(session_id, data)

    @router.get(
        "/sessoes/{session_id}/eventos",
        response_model=EventsResponse,
        summary="Consultar eventos persistidos da sessão",
        responses={404: ERRORS[404], 503: ERRORS[503]},
    )
    async def events(session_id: str):
        """Lista os eventos ADK persistidos, em ordem; sessão inexistente recebe 404."""
        return await controller.events(session_id)

    @router.get(
        "/apartamentos/{numero}/reservas",
        response_model=list[ReservationRead],
        summary="Consultar reservas do apartamento",
        responses={503: ERRORS[503]},
    )
    async def reservations(numero: str):
        """Lista reservas ativas com código, área e data. Esta rota local de verificação não muda registros."""
        return await controller.reservations(numero)

    @router.get(
        "/apartamentos/{numero}/visitantes",
        response_model=list[VisitorRead],
        summary="Consultar visitantes do apartamento",
        responses={503: ERRORS[503]},
    )
    async def visitors(numero: str):
        """Lista nomes e datas das autorizações do apartamento, sem alterar os dados do portal autenticado."""
        return await controller.visitors(numero)

    return router
