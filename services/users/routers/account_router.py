from typing import Annotated
from fastapi import APIRouter, Depends
from aurora_toolkit.identity import authenticated_user, verify_internal

from services.users.controllers.account_controller import AccountController
from services.users.schemas.account_create import AccountCreate
from services.users.schemas.account_patch import AccountPatch
from services.users.schemas.account_read import AccountRead

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Usuários"])
controller = AccountController()


@router.get(
    "/api/admin/users", response_model=list[AccountRead], summary="Listar contas"
)
def list_users(actor: Actor):
    """Lista as contas para um administrador. A projeção pública omite hashes e credenciais."""
    return controller.list(actor)


@router.get(
    "/api/admin/users/{user_id}",
    response_model=AccountRead,
    summary="Consultar uma conta",
)
def get_user(user_id: str, actor: Actor):
    """Consulta uma conta pelo identificador estável, com autorização administrativa; recurso inexistente recebe 404."""
    return controller.get(user_id, actor)


@router.post(
    "/api/admin/users",
    response_model=AccountRead,
    status_code=201,
    summary="Cadastrar uma conta",
)
def create_user(data: AccountCreate, actor: Actor):
    """Cadastra uma conta e seu perfil autorizado. E-mail já utilizado recebe 409 e nenhuma senha ou hash é retornado."""
    return controller.create(data, actor)


@router.patch(
    "/api/admin/users/{user_id}",
    response_model=AccountRead,
    summary="Atualizar uma conta",
)
def update_user(user_id: str, data: AccountPatch, actor: Actor):
    """Atualiza dados e habilitação de uma conta administrativa. Alteração de senha ou desativação revoga sessões; perfil é imutável e o último administrador ativo é preservado."""
    return controller.update(user_id, data, actor)


@router.get(
    "/internal/users/{user_id}",
    response_model=AccountRead,
    dependencies=[Depends(verify_internal)],
    summary="Consultar identidade para vínculo de domínio",
)
def internal_user(user_id: str):
    """Fornece a identidade pública de uma conta aos serviços do cluster que apresentem o token interno. Não expõe credenciais nem concede autorização ao usuário final."""
    return controller.get(user_id)
