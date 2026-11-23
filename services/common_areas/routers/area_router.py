from typing import Annotated
from fastapi import APIRouter, Depends, Response
from aurora_toolkit.identity import authenticated_user

from services.common_areas.controllers.area_controller import AreaController
from services.common_areas.schemas.area_input import AreaInput
from services.common_areas.schemas.area_patch import AreaPatch
from services.common_areas.schemas.area_read import AreaRead
from aurora_toolkit.http_types import AreaId

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Áreas comuns"])
controller = AreaController()


@router.get(
    "/api/admin/areas",
    response_model=list[AreaRead],
    summary="Listar áreas para administração",
)
def list_admin_areas(actor: Actor):
    return controller.list(actor, administrative=True)


@router.get(
    "/api/areas", response_model=list[AreaRead], summary="Consultar catálogo de áreas"
)
def list_areas(actor: Actor):
    return controller.list(actor)


@router.get(
    "/api/admin/areas/{area_id}", response_model=AreaRead, summary="Consultar uma área"
)
def get_area(area_id: AreaId, actor: Actor):
    return controller.get(area_id, actor)


@router.post(
    "/api/admin/areas",
    response_model=AreaRead,
    status_code=201,
    summary="Cadastrar uma área",
)
def create_area(data: AreaInput, actor: Actor):
    return controller.create(data, actor)


@router.patch(
    "/api/admin/areas/{area_id}",
    response_model=AreaRead,
    summary="Atualizar nome ou taxa",
)
def update_area(area_id: AreaId, data: AreaPatch, actor: Actor):
    return controller.update(area_id, data, actor)


@router.delete(
    "/api/admin/areas/{area_id}",
    status_code=204,
    response_model=None,
    summary="Excluir área sem reservas",
)
def delete_area(area_id: AreaId, actor: Actor):
    controller.delete(area_id, actor)
    return Response(status_code=204)
