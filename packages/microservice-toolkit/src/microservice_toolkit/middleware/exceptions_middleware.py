"""Última fronteira ASGI: registra exceções e não duplica resposta iniciada."""


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
        except Exception as exc:
            from ..exceptions.diagnostics import log_failure
            from ..exceptions.handlers import failure_response

            if started:
                log_failure(scope, exc, 500, "RESPONSE_INTERRUPTED")
                raise
            await failure_response(scope, exc)(scope, receive, send)
