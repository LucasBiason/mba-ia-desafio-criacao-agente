"""Composição do serviço de visitas."""

from microservice_toolkit import create_app
from aurora_toolkit.configuration import INTERNAL_TOKEN_HEADER

from services.visits.routers.visit_router import router
from aurora_toolkit.identity import verify_identity

app = create_app(
    title="Residencial Aurora · Visitas",
    service_name="aurora-visits",
    version="0.1.0",
    description="API de visitas do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    verifier=verify_identity,
    protected_paths=("/api/admin", "/api/resident"),
    service_token_header=INTERNAL_TOKEN_HEADER,
)
app.include_router(router)
