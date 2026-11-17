from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error(status: int, code: str, message: str) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return HTTPException(status, detail={"code": code, "message": message}, headers=headers)


async def invalid_input(_request: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(map(str, item["loc"])), "code": item["type"]}
              for item in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": {
        "code": "INVALID_INPUT", "message": "Revise os campos do formulário.", "fields": fields,
    }})


async def unexpected_error(_request: Request, _exc: Exception):
    return JSONResponse(status_code=500, content={"detail": {
        "code": "INTERNAL_ERROR", "message": "Não foi possível concluir a operação.",
    }})


class ErrorBoundaryMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False

        async def guarded_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, guarded_send)
        except Exception:
            if started:
                raise
            response = await unexpected_error(None, None)
            await response(scope, receive, send)


async def database_unavailable(_request: Request, _exc: Exception):
    return JSONResponse(status_code=503, content={"detail": {
        "code": "DATABASE_UNAVAILABLE", "message": "Banco de dados indisponível.",
    }})
