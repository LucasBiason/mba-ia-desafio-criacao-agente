from typing import Annotated
from fastapi import APIRouter, Depends
from services.authentication.client import authenticated_user, verify_internal

Actor = Annotated[dict, Depends(authenticated_user)]

from services.users.controllers.account_controller import AccountController
from services.users.schemas.account_create import AccountCreate
from services.users.schemas.account_patch import AccountPatch
from services.users.schemas.account_read import AccountRead

router = APIRouter(tags=["Usuários"])
controller = AccountController()

@router.get("/api/admin/users", response_model=list[AccountRead], summary="Listar contas")
def list_users(actor: Actor):
    return controller.list(actor)

@router.get("/api/admin/users/{user_id}", response_model=AccountRead, summary="Consultar uma conta")
def get_user(user_id: str, actor: Actor):
    return controller.get(user_id, actor)

@router.post("/api/admin/users", response_model=AccountRead, status_code=201, summary="Cadastrar uma conta")
def create_user(data: AccountCreate, actor: Actor):
    return controller.create(data, actor)

@router.patch("/api/admin/users/{user_id}", response_model=AccountRead, summary="Atualizar uma conta")
def update_user(user_id: str, data: AccountPatch, actor: Actor):
    return controller.update(user_id, data, actor)

@router.get("/internal/users/{user_id}", response_model=AccountRead, dependencies=[Depends(verify_internal)], summary="Consultar identidade para vínculo de domínio")
def internal_user(user_id: str):
    return controller.get(user_id)
