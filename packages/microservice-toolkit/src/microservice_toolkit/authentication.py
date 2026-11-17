import hmac
import inspect

from fastapi import Header
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from .errors import error


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 4096 or any(c.isspace() for c in token):
        raise error(401, "AUTH_REQUIRED", "Entre com sua conta para continuar.")
    return token


def internal_guard(secret_provider, *, header_name="X-Service-Token"):
    def verify(credential: str | None = Header(default=None, alias=header_name)):
        secret = secret_provider()
        if credential is None or not hmac.compare_digest(credential.encode(), secret.encode()):
            raise error(403, "INTERNAL_ACCESS_REQUIRED", "Operação reservada para serviços internos.")
    return verify


class AuthenticationMiddleware:
    def __init__(self, app, *, verifier, protected_paths):
        self.app = app
        self.verifier = verifier
        self.protected_paths = tuple(protected_paths)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        root_path = scope.get("root_path", "").rstrip("/")
        if root_path and path.startswith(root_path + "/"):
            path = path[len(root_path):]
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in self.protected_paths):
            return await self.app(scope, receive, send)
        try:
            token = bearer_token(Headers(scope=scope).get("authorization"))
            if inspect.iscoroutinefunction(self.verifier):
                user = await self.verifier(token)
            else:
                user = await run_in_threadpool(self.verifier, token)
            if not isinstance(user, dict) or not user:
                raise error(503, "IDENTITY_UNAVAILABLE", "Identidade temporariamente indisponível.")
        except HTTPException as exc:
            response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail},
                                    headers=exc.headers)
            return await response(scope, receive, send)
        except Exception:
            response = JSONResponse(status_code=503, content={"detail": {
                "code": "AUTH_UNAVAILABLE", "message": "Serviço de autenticação indisponível.",
            }})
            return await response(scope, receive, send)
        scope.setdefault("state", {})["user"] = user
        return await self.app(scope, receive, send)
