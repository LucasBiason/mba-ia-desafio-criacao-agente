from typing import Annotated
from fastapi import APIRouter, Depends, Response
from services.authentication.client import authenticated_user

Actor = Annotated[dict, Depends(authenticated_user)]

from services.apartments.controllers.apartment_controller import ApartmentController
from services.apartments.schemas.apartment_input import ApartmentInput
from services.apartments.schemas.apartment_patch import ApartmentPatch
from services.apartments.schemas.apartment_read import ApartmentRead
from services.http_types import ApartmentNumber

router = APIRouter(tags=["Apartamentos"])
controller = ApartmentController()

@router.get("/api/admin/apartments", response_model=list[ApartmentRead], summary="Listar unidades e responsáveis")
def list_apartments(actor: Actor):
    return controller.list(actor)

@router.get("/api/admin/apartments/{number}", response_model=ApartmentRead, summary="Consultar uma unidade")
def get_apartment(number: ApartmentNumber, actor: Actor):
    return controller.get(number, actor)

@router.post("/api/admin/apartments", response_model=ApartmentRead, status_code=201, summary="Cadastrar uma unidade")
def create_apartment(data: ApartmentInput, actor: Actor):
    return controller.create(data, actor)

@router.patch("/api/admin/apartments/{number}", response_model=ApartmentRead, summary="Atualizar número ou responsável")
def update_apartment(number: ApartmentNumber, data: ApartmentPatch, actor: Actor):
    return controller.update(number, data, actor)

@router.delete("/api/admin/apartments/{number}", status_code=204, response_model=None, summary="Excluir unidade sem histórico")
def delete_apartment(number: ApartmentNumber, actor: Actor):
    controller.delete(number, actor)
    return Response(status_code=204)

@router.get("/api/resident/apartments", response_model=list[ApartmentRead], summary="Listar unidades vinculadas ao morador")
def own_apartments(actor: Actor):
    return controller.list(actor, own=True)
