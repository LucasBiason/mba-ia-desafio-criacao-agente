"""Composição do serviço de agenda."""

from microservice_toolkit import create_app
from aurora_toolkit.configuration import INTERNAL_TOKEN_HEADER

from services.agenda.routers.reservation_router import router
from aurora_toolkit.identity import verify_identity

app = create_app(
    title="Residencial Aurora · Agenda",
    service_name="aurora-agenda",
    version="0.1.0",
    description="API de agenda do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    verifier=verify_identity,
    protected_paths=("/api/admin", "/api/resident"),
    service_token_header=INTERNAL_TOKEN_HEADER,
)
app.include_router(router)
