from typing import Annotated
from fastapi import APIRouter, Depends
from services.authentication.client import authenticated_user

Actor = Annotated[dict, Depends(authenticated_user)]

from services.settings.controllers.regulation_controller import RegulationController
from services.settings.schemas.regulation_input import RegulationInput
from services.settings.schemas.regulation_read import RegulationRead

router = APIRouter(tags=["Regulamento"])
controller = RegulationController()

@router.get("/api/admin/regulation", response_model=RegulationRead, summary="Consultar regulamento vigente")
def current(actor: Actor):
    return controller.current(actor)

@router.get("/api/resident/regulation", response_model=RegulationRead, summary="Consultar regras vigentes para o morador")
def resident_current(actor: Actor):
    return controller.current(actor, resident_view=True)

@router.get("/api/admin/regulation/versions", response_model=list[RegulationRead], summary="Consultar histórico de versões")
def history(actor: Actor):
    return controller.history(actor)

@router.put("/api/admin/regulation", response_model=RegulationRead, summary="Publicar nova versão do regulamento")
def publish(data: RegulationInput, actor: Actor):
    return controller.publish(data, actor)
