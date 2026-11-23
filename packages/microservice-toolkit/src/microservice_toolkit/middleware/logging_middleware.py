"""Contexto de correlação isolado por requisição e log final de acesso."""

import re
from time import perf_counter
from uuid import uuid4
from starlette.datastructures import Headers, MutableHeaders
from ..logging.context import logger, request_id_context
from ..paths import route_template


class RequestContextMiddleware:
    def __init__(self, app, *, service_name):
        self.app = app
        self.service_name = service_name

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = (
            incoming if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", incoming) else uuid4().hex
        )
        token = request_id_context.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        status = 500

        async def traced_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, traced_send)
        finally:
            try:
                logger.info(
                    "http.request",
                    extra={
                        "service": self.service_name,
                        "request_id": request_id,
                        "method": scope["method"],
                        "route": route_template(scope),
                        "status": status,
                        "duration_ms": round((perf_counter() - started) * 1000, 2),
                    },
                )
            finally:
                request_id_context.reset(token)
