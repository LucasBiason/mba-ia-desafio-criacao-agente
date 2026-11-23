"""Composição da infraestrutura HTTP em fases pequenas e verificáveis."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException
from .middleware import AuthenticationMiddleware
from .middleware import ErrorBoundaryMiddleware
from .exceptions import ErrorPolicy
from .exceptions import invalid_input, database_unavailable, http_error
from .routers import HealthRouter
from .middleware import RequestContextMiddleware
from .logging import configure_logging
from .openapi.custom_openapi import OpenAPIConfiguration
from .configuration.lifespan import toolkit_lifespan


class ApplicationFactory:
    def __init__(
        self,
        *,
        title,
        service_name,
        lifespan=None,
        verifier=None,
        protected_paths=(),
        health_check=None,
        readiness_check=None,
        required_secrets=None,
        service_token_header="X-Service-Token",
        environment=None,
        debug=None,
        **options,
    ):
        self.title, self.service_name = title, service_name
        self.lifespan = toolkit_lifespan(
            required_secrets=required_secrets, lifespan=lifespan
        )
        self.verifier = verifier
        self.protected_paths = tuple(
            path.rstrip("/") or "/" for path in protected_paths
        )
        if readiness_check is not None and health_check is not None:
            raise ValueError("Use apenas readiness_check ou seu alias health_check.")
        self.health_check = (
            readiness_check if readiness_check is not None else health_check
        )
        self.service_token_header = service_token_header
        self.policy = ErrorPolicy.from_settings(environment, debug)
        self.options = options

    def build(self) -> FastAPI:
        """Ordem explícita: contexto externo envolve autenticação e erros."""
        self.validate_configuration()
        app = self.create_application()
        self.register_error_handlers(app)
        self.register_middleware(app)
        self.register_health(app)
        self.register_openapi(app)
        return app

    def validate_configuration(self) -> None:
        """Recusa configurações incompletas antes de registrar infraestrutura."""
        if self.protected_paths and self.verifier is None:
            raise ValueError("Rotas protegidas exigem um verificador de identidade.")
        if self.verifier is not None and not callable(self.verifier):
            raise ValueError("O verificador de identidade precisa ser chamável.")
        if any(not path.startswith("/") for path in self.protected_paths):
            raise ValueError("Rotas protegidas precisam começar com /.")
        if self.health_check is not None and not callable(self.health_check):
            raise ValueError("A checagem de prontidão precisa ser chamável.")

    def create_application(self) -> FastAPI:
        """Cria FastAPI e associa política/identificação sem debug HTML nativo."""
        configure_logging()
        # O modo debug nativo renderiza traceback HTML fora do nosso contrato.
        app = FastAPI(
            title=self.title, lifespan=self.lifespan, debug=False, **self.options
        )
        app.state.error_policy = self.policy
        app.state.service_name = self.service_name
        return app

    def register_error_handlers(self, app) -> None:
        """Traduz validação, dependência e erros HTTP pelo contrato comum."""
        app.add_exception_handler(RequestValidationError, invalid_input)
        app.add_exception_handler(OperationalError, database_unavailable)
        app.add_exception_handler(HTTPException, http_error)

    def register_middleware(self, app) -> None:
        """Contexto envolve a fronteira de erro, que envolve autenticação."""
        if self.verifier is not None:
            app.add_middleware(
                AuthenticationMiddleware,
                verifier=self.verifier,
                protected_paths=self.protected_paths,
            )
        app.add_middleware(ErrorBoundaryMiddleware)
        app.add_middleware(RequestContextMiddleware, service_name=self.service_name)

    def register_health(self, app) -> None:
        """Delega rotas operacionais ao router proprietário do health."""
        HealthRouter(self.health_check).register(app)

    def register_openapi(self, app) -> None:
        """Instala documentação sem descartar metadados nativos da aplicação."""
        OpenAPIConfiguration(
            app,
            protected_paths=self.protected_paths,
            service_token_header=self.service_token_header,
        ).register()


def create_app(
    *,
    title,
    service_name,
    lifespan=None,
    verifier=None,
    protected_paths=(),
    health_check=None,
    readiness_check=None,
    required_secrets=None,
    service_token_header="X-Service-Token",
    environment=None,
    debug=None,
    **options,
):
    """Compõe configuração, erros, middleware, health e OpenAPI em etapas.

    environment aceita production (padrão), development ou test. Em produção,
    debug=True é recusado. As demais opções são encaminhadas ao FastAPI.
    """
    return ApplicationFactory(
        title=title,
        service_name=service_name,
        lifespan=lifespan,
        verifier=verifier,
        protected_paths=protected_paths,
        health_check=health_check,
        readiness_check=readiness_check,
        required_secrets=required_secrets,
        service_token_header=service_token_header,
        environment=environment,
        debug=debug,
        **options,
    ).build()


__all__ = ["ApplicationFactory", "create_app"]
