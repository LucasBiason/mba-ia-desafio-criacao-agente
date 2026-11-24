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
    """Lista o cadastro de áreas e suas taxas para administração. Taxas são representadas em centavos."""
    return controller.list(actor, administrative=True)


@router.get(
    "/api/areas", response_model=list[AreaRead], summary="Consultar catálogo de áreas"
)
def list_areas(actor: Actor):
    """Consulta as áreas cadastradas e suas taxas para contas autenticadas. A consulta não cria reserva."""
    return controller.list(actor)


@router.get(
    "/api/admin/areas/{area_id}", response_model=AreaRead, summary="Consultar uma área"
)
def get_area(area_id: AreaId, actor: Actor):
    """Consulta uma área administrativa pelo identificador; recurso inexistente recebe 404."""
    return controller.get(area_id, actor)


@router.post(
    "/api/admin/areas",
    response_model=AreaRead,
    status_code=201,
    summary="Cadastrar uma área",
)
def create_area(data: AreaInput, actor: Actor):
    """Cadastra uma área com taxa inteira não negativa em centavos. Identificador já cadastrado recebe 409."""
    return controller.create(data, actor)


@router.patch(
    "/api/admin/areas/{area_id}",
    response_model=AreaRead,
    summary="Atualizar nome ou taxa",
)
def update_area(area_id: AreaId, data: AreaPatch, actor: Actor):
    """Atualiza nome ou taxa por administrador. Não altera o histórico das reservas já registradas e recusa taxa negativa."""
    return controller.update(area_id, data, actor)


@router.delete(
    "/api/admin/areas/{area_id}",
    status_code=204,
    response_model=None,
    summary="Excluir área sem reservas",
)
def delete_area(area_id: AreaId, actor: Actor):
    """Exclui uma área apenas quando não houver referência histórica que deva ser preservada. Conflito de integridade recebe 409."""
    controller.delete(area_id, actor)
    return Response(status_code=204)
