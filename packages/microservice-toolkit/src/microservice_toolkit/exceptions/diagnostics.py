"""Diagnósticos correlacionados: quadros completos, sem locals ou linhas de código."""

import logging
import os
import re
from .policy import ErrorPolicy
from ..logging.context import request_id_context
from ..paths import route_template

error_logger = logging.getLogger("microservice_toolkit.errors")


def policy_for(scope):
    state = getattr(scope.get("app"), "state", None)
    return getattr(state, "error_policy", ErrorPolicy())


def error_context(scope):
    return {
        "request_id": scope.get("state", {}).get("request_id")
        or request_id_context.get(),
        "method": scope.get("method", "unknown"),
        "route": route_template(scope),
    }


def redact(text, scope):
    """Remove configurações sensíveis conhecidas e padrões; não lê arquivos."""
    for name, value in os.environ.items():
        if (
            re.search(
                r"PASSWORD|TOKEN|SECRET|KEY|CREDENTIAL|DATABASE_URL|DSN", name, re.I
            )
            and len(value) >= 4
        ):
            text = text.replace(value, "[REDACTED]")
    for key, value in scope.get("headers", []):
        if any(
            word in key.lower()
            for word in (b"authorization", b"cookie", b"token", b"secret", b"api-key")
        ):
            raw = value.decode("latin1")
            scheme, separator, credential = raw.partition(" ")
            candidates = [raw]
            if separator and scheme.lower() == "bearer":
                candidates.append(credential)
            if key.lower() == b"cookie":
                candidates.extend(
                    part.partition("=")[2].strip() for part in raw.split(";")
                )
            for item in candidates:
                if len(item) >= 4:
                    text = text.replace(item, "[REDACTED]")
    text = re.sub(
        r"(?i)([a-z][a-z0-9+.-]*://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", text
    )
    text = re.sub(
        r"(?i)(password|token|secret|authorization|api[_-]?key)([\s:=]+)[^\s,;]+",
        r"\1\2[REDACTED]",
        text,
    )
    text = re.sub(
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED]", text
    )
    return text


def exception_message(exc, scope):
    # Mensagens de drivers/validação podem incorporar parâmetros e payloads.
    from pydantic import ValidationError
    from fastapi.exceptions import RequestValidationError, ResponseValidationError
    from sqlalchemy.exc import SQLAlchemyError
    from starlette.exceptions import HTTPException

    unsafe = isinstance(
        exc,
        (
            ValidationError,
            RequestValidationError,
            ResponseValidationError,
            SQLAlchemyError,
            HTTPException,
        ),
    ) or type(exc).__module__.startswith(("psycopg", "sqlite3"))
    if not policy_for(scope).debug or unsafe:
        return type(exc).__name__
    return redact(str(exc), scope)


def trace_chain(exc, scope, seen=None):
    """Preserva todos os quadros e causas sem serializar seus valores locais."""
    seen = set() if seen is None else seen
    if id(exc) in seen:
        return "[cadeia circular]"
    seen.add(id(exc))
    lines = []
    previous = exc.__cause__ or (
        exc.__context__ if not exc.__suppress_context__ else None
    )
    if previous is not None:
        lines += [trace_chain(previous, scope, seen), "Causada por:"]
    lines.append("Traceback (most recent call last):")
    tb = exc.__traceback__
    while tb is not None:
        code = tb.tb_frame.f_code
        lines.append(
            f'  File "{code.co_filename}", line {tb.tb_lineno}, in {code.co_name}'
        )
        tb = tb.tb_next
    lines.append(type(exc).__name__ + ": " + exception_message(exc, scope))
    if isinstance(exc, BaseExceptionGroup):
        for index, child in enumerate(exc.exceptions, start=1):
            lines += [f"Exceção agrupada {index}:", trace_chain(child, scope, seen)]
    return redact("\n".join(lines), scope)


def diagnostics_for(scope, exc):
    return {
        "exception_type": type(exc).__name__,
        "message": exception_message(exc, scope),
        "traceback": trace_chain(exc, scope),
    }


def log_failure(scope, exc, status, code, *, diagnostic=None):
    diagnostic = diagnostic or diagnostics_for(scope, exc)
    state = getattr(scope.get("app"), "state", None)
    extra = {
        "service": getattr(state, "service_name", "unknown"),
        **error_context(scope),
        "status": status,
        "code": code,
        "exception_type": diagnostic["exception_type"],
        "exception_message": diagnostic["message"],
        "traceback": diagnostic["traceback"],
    }
    write = error_logger.warning if status < 500 else error_logger.error
    write("http.error", extra=extra)
