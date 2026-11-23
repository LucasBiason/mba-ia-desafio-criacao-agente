"""Documentação de autenticação e erros sem regras de negócio no factory."""

from ..paths import matches_path


class OpenAPIConfiguration:
    METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
    ERRORS = {
        "401": "Sessão inválida",
        "403": "Sem permissão",
        "404": "Recurso inexistente",
        "409": "Conflito de estado",
        "422": "Entrada inválida",
        "503": "Dependência indisponível",
    }

    def __init__(
        self, app, *, protected_paths=(), service_token_header="X-Service-Token"
    ):
        self.app = app
        self.protected_paths = protected_paths
        self.service_token_header = service_token_header
        self.original_openapi = app.openapi

    def register(self) -> None:
        self.app.openapi = self.schema

    def schema(self):
        """Usa o gerador nativo para preservar metadados, servers e cache."""
        if self.app.openapi_schema is not None:
            return self.app.openapi_schema
        schema = self.original_openapi()
        self.configure_security_schemes(schema)
        self.configure_operations(schema)
        self.app.openapi_schema = schema
        return schema

    def configure_security_schemes(self, schema) -> None:
        schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schemes.setdefault(
            "BearerAuth", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        )
        schemes.setdefault(
            "ServiceToken",
            {"type": "apiKey", "in": "header", "name": self.service_token_header},
        )

    def configure_operations(self, schema) -> None:
        for path, methods in schema.get("paths", {}).items():
            for method, operation in methods.items():
                if method not in self.METHODS:
                    continue
                self.configure_operation_security(path, operation)
                if path != "/health":
                    for status, description in self.ERRORS.items():
                        operation.setdefault("responses", {}).setdefault(
                            status, {"description": description}
                        )

    def configure_operation_security(self, path, operation) -> None:
        if "security" in operation:
            return
        if path.startswith("/internal/"):
            operation["security"] = [{"ServiceToken": []}]
        elif matches_path(path, self.protected_paths):
            operation["security"] = [{"BearerAuth": []}]
