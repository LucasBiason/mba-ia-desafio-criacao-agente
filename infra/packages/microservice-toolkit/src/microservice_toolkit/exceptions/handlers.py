"""Contrato de erros compartilhado por rotas e middlewares.

Dados inválidos incluem operação e campos sem valores recebidos. Falhas internas
são correlacionadas e registradas; detalhes públicos dependem da ErrorPolicy.
"""

import re
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .diagnostics import error_context, diagnostics_for, log_failure, policy_for


def error(status: int, code: str, message: str) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return HTTPException(
        status, detail={"code": code, "message": message}, headers=headers
    )


def http_exception_response(scope, exc: HTTPException):
    """Uma única conversão preserva códigos, detalhes e headers de domínio."""
    if exc.status_code >= 500 or policy_for(scope).debug:
        code = (
            exc.detail.get("code", "HTTP_ERROR")
            if isinstance(exc.detail, dict)
            else "HTTP_ERROR"
        )
        code = (
            code
            if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{1,64}", code)
            else "HTTP_ERROR"
        )
        log_failure(scope, exc, exc.status_code, code)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
    )


async def http_error(request: Request, exc: HTTPException):
    return http_exception_response(request.scope, exc)


def failure_response(
    scope,
    exc,
    *,
    status=500,
    code="INTERNAL_ERROR",
    message="Não foi possível concluir a operação.",
):
    diagnostic = diagnostics_for(scope, exc)
    log_failure(scope, exc, status, code, diagnostic=diagnostic)
    detail = {"code": code, "message": message, **error_context(scope)}
    if policy_for(scope).debug:
        detail["debug"] = diagnostic
    return JSONResponse(status_code=status, content={"detail": detail})


async def invalid_input(request: Request, exc: RequestValidationError):
    messages = {
        "missing": "Campo obrigatório.",
        "int_parsing": "Informe um número inteiro.",
        "string_too_short": "Texto abaixo do tamanho mínimo.",
        "extra_forbidden": "Campo não permitido.",
        "string_pattern_mismatch": "Formato inválido.",
        "value_error": "Valor inválido.",
    }
    fields = [
        {
            "field": ".".join(map(str, item["loc"])),
            "code": item["type"],
            "message": messages.get(
                item["type"], "Valor incompatível com o formato esperado."
            ),
        }
        for item in exc.errors()
    ]
    log_failure(request.scope, exc, 422, "INVALID_INPUT")
    context = error_context(request.scope)
    operation = f"{context['method']} {context['route']}"
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "INVALID_INPUT",
                "message": f"Entrada inválida em {operation}.",
                "fields": fields,
                **context,
            }
        },
    )


async def unexpected_error(request: Request, exc: Exception):
    return failure_response(request.scope if request else {}, exc)


async def database_unavailable(request: Request, exc: Exception):
    return failure_response(
        request.scope,
        exc,
        status=503,
        code="DATABASE_UNAVAILABLE",
        message="Banco de dados indisponível.",
    )
