from typing import Annotated
from fastapi import APIRouter, Depends, Response
from aurora_toolkit.identity import authenticated_user

from services.apartments.controllers.apartment_controller import ApartmentController
from services.apartments.schemas.apartment_input import ApartmentInput
from services.apartments.schemas.apartment_patch import ApartmentPatch
from services.apartments.schemas.apartment_read import ApartmentRead
from aurora_toolkit.http_types import ApartmentNumber

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Apartamentos"])
controller = ApartmentController()


@router.get(
    "/api/admin/apartments",
    response_model=list[ApartmentRead],
    summary="Listar unidades e responsáveis",
)
def list_apartments(actor: Actor):
    """Lista unidades e vínculos de moradores para a administração; identificadores de unidade permanecem estáveis após renumeração."""
    return controller.list(actor)


@router.get(
    "/api/admin/apartments/{number}",
    response_model=ApartmentRead,
    summary="Consultar uma unidade",
)
def get_apartment(number: ApartmentNumber, actor: Actor):
    """Consulta uma unidade pelo número para um administrador, devolvendo o identificador estável e o vínculo de morador."""
    return controller.get(number, actor)


@router.post(
    "/api/admin/apartments",
    response_model=ApartmentRead,
    status_code=201,
    summary="Cadastrar uma unidade",
)
def create_apartment(data: ApartmentInput, actor: Actor):
    """Cadastra uma unidade e, opcionalmente, uma conta moradora responsável. Número duplicado recebe 409; perfis não moradores não podem ser vinculados."""
    return controller.create(data, actor)


@router.patch(
    "/api/admin/apartments/{number}",
    response_model=ApartmentRead,
    summary="Atualizar número ou responsável",
)
def update_apartment(number: ApartmentNumber, data: ApartmentPatch, actor: Actor):
    """Atualiza número ou responsável preservando o identificador estável da unidade e as referências de histórico. Conflito de número recebe 409."""
    return controller.update(number, data, actor)


@router.delete(
    "/api/admin/apartments/{number}",
    status_code=204,
    response_model=None,
    summary="Excluir unidade sem histórico",
)
def delete_apartment(number: ApartmentNumber, actor: Actor):
    """Remove somente unidade sem dependências de histórico. Reservas ou visitas vinculadas impedem a exclusão; a transação é revertida."""
    controller.delete(number, actor)
    return Response(status_code=204)


@router.get(
    "/api/resident/apartments",
    response_model=list[ApartmentRead],
    summary="Listar unidades vinculadas ao morador",
)
def own_apartments(actor: Actor):
    """Lista apenas as unidades vinculadas à identidade moradora autenticada, sem ampliar o vínculo por parâmetros de entrada."""
    return controller.list(actor, own=True)
