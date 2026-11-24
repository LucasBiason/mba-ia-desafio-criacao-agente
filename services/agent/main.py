"""Composição do serviço de agente."""

import os

from microservice_toolkit import create_app
from aurora_toolkit.configuration import INTERNAL_TOKEN_HEADER

from services.agent.routers.chat_router import router
from aurora_toolkit.identity import verify_identity

app = create_app(
    title="Residencial Aurora · Agente",
    service_name="aurora-agent",
    version="0.1.0",
    description="API de agente do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    verifier=verify_identity,
    protected_paths=("/api/resident",),
    service_token_header=INTERNAL_TOKEN_HEADER,
)
app.include_router(router)
# Transcript/session access is independent of model activation.
app.state.portal_history_enabled = True
app.state.resident_actions_enabled = (
    os.environ.get("AURORA_AGENT_ENABLED", "0") == "1"
    and os.environ.get("AURORA_RESIDENT_ACTIONS", "0") == "1"
)

# O armazenamento legado é legível mesmo sem ativar o modelo/provedor.
if os.environ.get("AURORA_AGENT_ENABLED", "0") == "1" or os.environ.get(
    "AURORA_AGENT_SESSION_DATABASE_URL"
):
    from services.agent.runtime.configuration import configure_from_environment

    configure_from_environment(app, os.environ)

    if (
        os.environ.get("AURORA_AGENT_ENABLED", "0") == "1"
        and os.environ.get("AURORA_RESIDENT_ACTIONS", "0") == "1"
    ):
        from services.agent.routers.resident_action_router import (
            router as action_router,
        )

        app.include_router(action_router)
