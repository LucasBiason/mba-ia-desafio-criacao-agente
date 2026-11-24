from typing import Annotated
from fastapi import APIRouter, Depends, Header, Response
from aurora_toolkit.identity import authenticated_user, verify_internal

from services.authentication.controllers.authentication_controller import (
    AuthenticationController,
)
from services.authentication.schemas.login import Login
from services.authentication.schemas.login_read import LoginRead
from services.users.schemas.account_read import AccountRead

Actor = Annotated[dict, Depends(authenticated_user)]

router = APIRouter(tags=["Autenticação"])
controller = AuthenticationController()


@router.post(
    "/api/auth/login", response_model=LoginRead, summary="Autenticar uma conta"
)
def login(data: Login, response: Response):
    """Autentica uma conta ativa e emite JWT revogável. Senha inválida não identifica a existência da conta; excesso de tentativas recebe 429. A resposta não deve ser armazenada em cache."""
    result = controller.login(data)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get(
    "/api/auth/me",
    response_model=AccountRead,
    summary="Consultar a identidade corrente",
)
def me(authorization: Annotated[str | None, Header()] = None):
    """Consulta a identidade do bearer corrente, incluindo nome, e-mail e perfil, sem senha ou hash. Sessão expirada ou revogada recebe 401."""
    return controller.me(authorization)


@router.get(
    "/internal/identity",
    response_model=AccountRead,
    dependencies=[Depends(verify_internal)],
    summary="Validar a sessão para outro serviço",
    openapi_extra={"security": [{"ServiceToken": [], "BearerAuth": []}]},
)
def introspect(
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
):
    """Verifica conjuntamente o token interno do serviço e o bearer da sessão. A identidade só é retornada quando ambos são válidos; ausência ou revogação da sessão recebe 401."""
    return controller.me(authorization)


@router.post(
    "/api/auth/logout",
    status_code=204,
    response_model=None,
    summary="Encerrar a sessão corrente",
)
def logout(authorization: Annotated[str | None, Header()] = None):
    """Revoga a sessão corrente no servidor. Reutilizar o mesmo bearer em uma operação protegida recebe 401."""
    controller.logout(authorization)
    return Response(status_code=204)
