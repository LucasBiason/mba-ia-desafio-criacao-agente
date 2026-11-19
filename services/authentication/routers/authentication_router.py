from typing import Annotated
from fastapi import APIRouter, Depends, Header, Response
from services.authentication.client import authenticated_user, verify_internal

Actor = Annotated[dict, Depends(authenticated_user)]

from services.authentication.controllers.authentication_controller import AuthenticationController
from services.authentication.schemas.login import Login
from services.authentication.schemas.login_read import LoginRead
from services.users.schemas.account_read import AccountRead

router = APIRouter(tags=["Autenticação"])
controller = AuthenticationController()

@router.post("/api/auth/login", response_model=LoginRead, summary="Autenticar uma conta")
def login(data: Login, response: Response):
    result = controller.login(data)
    response.headers["Cache-Control"] = "no-store"
    return result

@router.get("/api/auth/me", response_model=AccountRead, summary="Consultar a identidade corrente")
def me(authorization: Annotated[str | None, Header()] = None):
    return controller.me(authorization)

@router.get("/internal/identity", response_model=AccountRead, dependencies=[Depends(verify_internal)], summary="Validar a sessão para outro serviço")
def introspect(authorization: Annotated[str | None, Header()] = None):
    return controller.me(authorization)

@router.post("/api/auth/logout", status_code=204, response_model=None, summary="Encerrar a sessão corrente")
def logout(authorization: Annotated[str | None, Header()] = None):
    controller.logout(authorization)
    return Response(status_code=204)
