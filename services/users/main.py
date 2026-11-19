"""Composição do serviço de usuários."""

from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from microservice_toolkit import create_app, required_secret

from services.persistence.schema_repository import SchemaRepository
from services.persistence.health_repository import HealthRepository
from services.users.routers.account_router import router
from services.authentication.client import verify_identity


@asynccontextmanager
async def lifespan(_app):
    required_secret("AURORA_INTERNAL_TOKEN")
    await run_in_threadpool(SchemaRepository().initialize_identity)
    yield


app = create_app(
    title="Residencial Aurora · Usuários",
    service_name="aurora-users",
    version="0.1.0",
    description="API de usuários do Residencial Aurora. Acesso por identidade autenticada e permissão de domínio.",
    lifespan=lifespan,
    verifier=verify_identity,
    protected_paths=("/api/admin",),
    health_check=HealthRepository.check,
    service_token_header="X-Aurora-Internal-Token",
)
app.include_router(router)
