"""Guarda de transporte para fronteiras internas de serviços."""

import hmac
from fastapi import Header
from ..exceptions import error


def internal_guard(secret_provider, *, header_name="X-Service-Token"):
    """Dependency para uma fronteira interna; não concede permissão de negócio."""

    def verify(credential: str | None = Header(default=None, alias=header_name)):
        secret = secret_provider()
        if credential is None or not hmac.compare_digest(
            credential.encode(), secret.encode()
        ):
            raise error(
                403,
                "INTERNAL_ACCESS_REQUIRED",
                "Operação reservada para serviços internos.",
            )

    return verify
