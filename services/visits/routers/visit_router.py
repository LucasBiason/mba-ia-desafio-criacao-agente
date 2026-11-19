from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query
from services.authentication.client import authenticated_user

Actor = Annotated[dict, Depends(authenticated_user)]

from datetime import date
from services.visits.controllers.visit_controller import VisitController
from services.visits.schemas.visit_read import VisitRead
from services.visits.schemas.visit_hours import VisitHours
from services.http_types import ApartmentNumber

router = APIRouter(tags=["Visitas"])
controller = VisitController()

@router.get("/api/admin/visits", response_model=list[VisitRead], summary="Consultar autorizações de visita")
def list_visits(actor: Actor, apartment: ApartmentNumber | None = None,
               day: Annotated[date | None, Query(alias="date")] = None):
    return controller.list(actor, apartment=apartment, day=day)

@router.patch("/api/admin/visits/{visit_id}/hours", response_model=VisitRead, summary="Registrar entrada ou saída de visitante")
def update_hours(visit_id: Annotated[int, Path(ge=1, le=2**63-1)], data: VisitHours, actor: Actor):
    return controller.update_hours(visit_id, data, actor)

@router.get("/api/resident/visits", response_model=list[VisitRead], summary="Consultar autorizações próprias")
def own_visits(apartment: ApartmentNumber, actor: Actor):
    return controller.list(actor, apartment=apartment, resident_view=True)
