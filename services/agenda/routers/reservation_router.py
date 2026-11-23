from typing import Annotated
from fastapi import APIRouter, Depends, Query
from aurora_toolkit.identity import authenticated_user

from datetime import date
from typing import Literal
from services.agenda.controllers.reservation_controller import ReservationController
from services.agenda.schemas.reservation_admin_read import ReservationAdminRead
from services.agenda.schemas.reservation_read import ReservationRead
from services.agenda.schemas.reservation_hours import ReservationHours
from aurora_toolkit.http_types import ApartmentNumber, AreaId

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Agenda"])
controller = ReservationController()


@router.get(
    "/api/admin/reservations",
    response_model=list[ReservationAdminRead],
    summary="Consultar agenda por área e data",
)
def list_reservations(
    actor: Actor,
    area_id: AreaId | None = None,
    day: Annotated[date | None, Query(alias="date")] = None,
    status: Literal["active", "cancelled"] | None = None,
):
    return controller.list(actor, area_id=area_id, day=day, status=status)


@router.patch(
    "/api/admin/reservations/{code}/hours",
    response_model=ReservationAdminRead,
    summary="Registrar horários de uma reserva",
)
def update_hours(code: str, data: ReservationHours, actor: Actor):
    return controller.update_hours(code, data, actor)


@router.get(
    "/api/resident/reservations",
    response_model=list[ReservationRead],
    summary="Consultar reservas próprias da unidade",
)
def own_reservations(apartment: ApartmentNumber, actor: Actor):
    return controller.list(actor, apartment=apartment.upper())
