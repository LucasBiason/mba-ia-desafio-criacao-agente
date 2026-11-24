"""Composição do serviço de áreas comuns."""

from microservice_toolkit import create_app
from aurora_toolkit.configuration import INTERNAL_TOKEN_HEADER

from services.common_areas.routers.area_router import router
from aurora_toolkit.identity import verify_identity

app = create_app(
    title="Residencial Aurora · Áreas comuns",
    service_name="aurora-common-areas",
    version="0.1.0",
    description="API de áreas comuns do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    verifier=verify_identity,
    protected_paths=("/api/admin", "/api/areas"),
    service_token_header=INTERNAL_TOKEN_HEADER,
)
app.include_router(router)
