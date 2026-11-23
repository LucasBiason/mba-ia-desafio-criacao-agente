"""Composição do serviço de autenticação."""

from microservice_toolkit import create_app
from aurora_toolkit.configuration import INTERNAL_TOKEN_HEADER

from services.authentication.routers.authentication_router import router
from services.authentication.controllers.authentication_controller import (
    AuthenticationController,
)

app = create_app(
    title="Residencial Aurora · Autenticação",
    service_name="aurora-auth",
    version="0.1.0",
    description="API de autenticação do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    verifier=AuthenticationController().verify_identity,
    protected_paths=("/api/auth/me", "/api/auth/logout"),
    service_token_header=INTERNAL_TOKEN_HEADER,
)
app.include_router(router)
