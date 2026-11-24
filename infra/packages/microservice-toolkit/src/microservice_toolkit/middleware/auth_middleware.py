"""Autenticação da identidade antes de acessar rotas protegidas."""

import inspect
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from ..exceptions import http_exception_response, failure_response, error
from ..paths import application_path, matches_path
from ..auth.tokens import bearer_token


class AuthenticationMiddleware:
    def __init__(self, app, *, verifier, protected_paths):
        self.app, self.verifier = app, verifier
        self.protected_paths = tuple(protected_paths)

    async def __call__(self, scope, receive, send):
        if not self.requires_identity(scope):
            return await self.app(scope, receive, send)
        response = await self.authenticate(scope)
        if response is not None:
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)

    def requires_identity(self, scope) -> bool:
        return scope["type"] == "http" and matches_path(
            application_path(scope), self.protected_paths
        )

    async def authenticate(self, scope):
        """Resolve uma identidade uma vez e converte recusas pelo contrato comum."""
        try:
            token = bearer_token(Headers(scope=scope).get("authorization"))
            user = await self.resolve_identity(token)
            self.validate_identity(user)
        except HTTPException as exc:
            return http_exception_response(scope, exc)
        except Exception as exc:
            return failure_response(
                scope,
                exc,
                status=503,
                code="AUTH_UNAVAILABLE",
                message="Serviço de autenticação indisponível.",
            )
        scope.setdefault("state", {})["user"] = user
        return None

    async def resolve_identity(self, token):
        """Executa sync em threadpool; também aguarda callables assíncronos."""
        if inspect.iscoroutinefunction(self.verifier):
            result = self.verifier(token)
        else:
            result = await run_in_threadpool(self.verifier, token)
        return await result if inspect.isawaitable(result) else result

    @staticmethod
    def validate_identity(user) -> None:
        """Identidade vazia não equivale a usuário autenticado."""
        if not isinstance(user, dict) or not user:
            raise error(
                503, "IDENTITY_UNAVAILABLE", "Identidade temporariamente indisponível."
            )
