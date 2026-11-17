from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from .health import HealthStatus

from .authentication import AuthenticationMiddleware
from .errors import ErrorBoundaryMiddleware, invalid_input, database_unavailable
from sqlalchemy.exc import OperationalError
from .observability import RequestContextMiddleware, configure_logging


def create_app(*, title, service_name, lifespan=None, verifier=None, protected_paths=(),
               health_check=None, service_token_header="X-Service-Token", **options):
    if protected_paths and verifier is None:
        raise ValueError("Rotas protegidas exigem um verificador de identidade.")
    configure_logging()
    app = FastAPI(title=title, lifespan=lifespan, **options)
    app.add_exception_handler(RequestValidationError, invalid_input)
    app.add_exception_handler(OperationalError, database_unavailable)
    if verifier is not None:
        app.add_middleware(AuthenticationMiddleware, verifier=verifier, protected_paths=protected_paths)
    app.add_middleware(ErrorBoundaryMiddleware)
    app.add_middleware(RequestContextMiddleware, service_name=service_name)

    @app.get("/health", tags=["Operação"], response_model=HealthStatus,
             summary="Verificar prontidão do serviço",
             responses={503: {"description": "Dependência indisponível"}})
    def health():
        if health_check is not None:
            health_check()
        return HealthStatus()

    def openapi():
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version,
                                 description=app.description, routes=app.routes, servers=app.servers)
            security = schema.setdefault("components", {}).setdefault("securitySchemes", {})
            security["BearerAuth"] = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            security["ServiceToken"] = {"type": "apiKey", "in": "header", "name": service_token_header}
            for path, operations in schema["paths"].items():
                for method, operation in operations.items():
                    if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                        continue
                    if path.startswith("/internal/"):
                        operation["security"] = [{"ServiceToken": []}]
                    elif any(path == prefix or path.startswith(prefix + "/") for prefix in protected_paths):
                        operation["security"] = [{"BearerAuth": []}]
                    if path != "/health":
                        for status, description in {
                            "401": "Sessão inválida", "403": "Sem permissão",
                            "404": "Recurso inexistente", "409": "Conflito de estado",
                            "422": "Entrada inválida", "503": "Dependência indisponível",
                        }.items():
                            operation.setdefault("responses", {}).setdefault(status, {"description": description})
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi
    return app
