"""Composição do serviço de autenticação."""

from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from microservice_toolkit import create_app, required_secret

from services.persistence.schema_repository import SchemaRepository
from services.persistence.health_repository import HealthRepository
from services.authentication.routers.authentication_router import router
from services.authentication.controllers.authentication_controller import AuthenticationController


def verify_identity(token):
    return AuthenticationController().me("Bearer " + token).model_dump()



@asynccontextmanager
async def lifespan(_app):
    required_secret("AURORA_INTERNAL_TOKEN")
    required_secret("AURORA_JWT_KEY")
    await run_in_threadpool(SchemaRepository().initialize_identity)
    yield


app = create_app(
    title="Residencial Aurora · Autenticação",
    service_name="aurora-auth",
    version="0.1.0",
    description="API de autenticação do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    lifespan=lifespan,
    verifier=verify_identity,
    protected_paths=("/api/auth/me", "/api/auth/logout"),
    health_check=HealthRepository.check,
    service_token_header="X-Aurora-Internal-Token",
)
app.include_router(router)
