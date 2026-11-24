"""Liveness sem dependências e readiness opcional fornecida pelo consumidor."""

import inspect
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool
from ..schemas.health_schema import HealthStatus


class HealthRouter:
    """/health mede atividade; /ready só existe com um callback explícito."""

    def __init__(self, check=None):
        self.check_dependency = check
        self.router = APIRouter(tags=["Operação"])
        self.router.add_api_route(
            "/health",
            self.liveness,
            methods=["GET"],
            response_model=HealthStatus,
            summary="Verificar atividade do serviço",
        )
        if check is not None:
            self.router.add_api_route(
                "/ready",
                self.readiness,
                methods=["GET"],
                response_model=HealthStatus,
                summary="Verificar prontidão do serviço",
                responses={503: {"description": "Dependência indisponível"}},
            )

    async def liveness(self) -> HealthStatus:
        """Confirma que o processo responde, sem consultar banco ou upstreams."""
        return HealthStatus()

    async def readiness(self) -> HealthStatus:
        """Executa callback sync fora do event loop e aguarda resultado async."""
        if self.check_dependency is not None:
            if inspect.iscoroutinefunction(self.check_dependency):
                result = self.check_dependency()
            else:
                result = await run_in_threadpool(self.check_dependency)
            if inspect.isawaitable(result):
                await result
        return HealthStatus()

    def register(self, app) -> None:
        app.include_router(self.router)
