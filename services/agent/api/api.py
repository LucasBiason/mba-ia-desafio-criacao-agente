"""Composição HTTP do protocolo acadêmico; bootstrap é uma operação explícita."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from microservice_toolkit.routers import HealthRouter
from sqlalchemy.exc import SQLAlchemyError

from services.agent.repositories.prepared_session_service import PreparedSessionService
from services.agent.repositories.session_store_not_prepared import (
    SessionStoreNotPrepared,
)

from .controllers.academic_controller import AcademicController
from .routers.academic_router import create_router


def prepare_domain_tables(domain):
    """Prepara tabelas da API durante init, antes de iniciar réplicas HTTP."""
    domain.prepare_api_tables()


def create_app(*, domain, session_url, models, regulation, replica_id=None):
    """Compõe dependências, sem consultar ou alterar schema no startup HTTP."""
    postgres = getattr(domain, "is_postgres", False)
    prefix = "postgresql+psycopg://" if postgres else "sqlite+aiosqlite:///"
    if ":memory:" in session_url or not session_url.startswith(prefix):
        raise ValueError(
            "Academic sessions require a persistent store matching the domain backend."
        )
    sessions = PreparedSessionService(db_url=session_url)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            await sessions.close()

    app = FastAPI(
        title="Aurora · assistente dos moradores",
        description="API acadêmica de sessões, mensagens e confirmações externas. Execute init antes de servir HTTP.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(SQLAlchemyError)
    @app.exception_handler(SessionStoreNotPrepared)
    async def store_unavailable(request, exc):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Persistência indisponível; execute init antes de servir HTTP."
            },
        )

    app.state.session_service = sessions
    HealthRouter().register(app)
    controller = AcademicController(
        domain=domain,
        repository=domain,
        session_url=session_url,
        models=models,
        regulation=regulation,
        sessions=sessions,
    )
    app.include_router(create_router(controller))
    if replica_id:

        @app.middleware("http")
        async def identify_replica(request, call_next):
            response = await call_next(request)
            response.headers["X-Aurora-Replica"] = replica_id
            return response

    return app
