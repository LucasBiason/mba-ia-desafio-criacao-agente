import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders

request_id_context = ContextVar("request_id", default=None)
logger = logging.getLogger("microservice_toolkit.http")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # Explicit field allowlist avoids serializing request headers, bodies or exceptions.
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": "http.request",
            "service": record.service,
            "request_id": record.request_id,
            "method": record.method,
            "route": record.route,
            "status": record.status,
            "duration_ms": record.duration_ms,
        }
        return json.dumps(payload, ensure_ascii=False)


def configure_logging():
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


class RequestContextMiddleware:
    def __init__(self, app, *, service_name):
        self.app = app
        self.service_name = service_name

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", incoming) else uuid4().hex
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
            route = scope.get("route")
            logger.info("http.request", extra={
                "service": self.service_name, "request_id": request_id,
                "method": scope["method"], "route": getattr(route, "path", "unmatched"),
                "status": status, "duration_ms": round((perf_counter() - started) * 1000, 2),
            })
            request_id_context.reset(token)
