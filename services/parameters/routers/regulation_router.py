from typing import Annotated
from fastapi import APIRouter, Depends
from aurora_toolkit.identity import authenticated_user

from services.parameters.controllers.regulation_controller import RegulationController
from services.parameters.schemas.regulation_input import RegulationInput
from services.parameters.schemas.regulation_read import RegulationRead

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Regulamento"])
controller = RegulationController()


@router.get(
    "/api/admin/regulation",
    response_model=RegulationRead,
    summary="Consultar regulamento vigente",
)
def current(actor: Actor):
    """Consulta o regulamento vigente para administração, com versão, autoria e instante da publicação."""
    return controller.current(actor)


@router.get(
    "/api/resident/regulation",
    response_model=RegulationRead,
    summary="Consultar regras vigentes para o morador",
)
def resident_current(actor: Actor):
    """Consulta o texto vigente permitido ao morador, sem oferecer edição nem acesso ao histórico administrativo."""
    return controller.current(actor, resident_view=True)


@router.get(
    "/api/admin/regulation/versions",
    response_model=list[RegulationRead],
    summary="Consultar histórico de versões",
)
def history(actor: Actor):
    """Consulta as versões imutáveis do único regulamento; não oferece exclusão de versão."""
    return controller.history(actor)


@router.put(
    "/api/admin/regulation",
    response_model=RegulationRead,
    summary="Publicar nova versão do regulamento",
)
def publish(data: RegulationInput, actor: Actor):
    """Publica uma nova versão imutável usando expected_version. Edições concorrentes são serializadas: uma versão obsoleta recebe 409 e não substitui o texto vigente."""
    return controller.publish(data, actor)
