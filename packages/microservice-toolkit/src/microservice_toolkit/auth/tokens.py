"""Extração do bearer sem verificar identidade ou autorização."""

from ..exceptions import error


def bearer_token(authorization: str | None) -> str:
    """Extrai um bearer bem formado sem verificar assinatura ou privilégio."""
    scheme, _, token = (authorization or "").partition(" ")
    if (
        scheme.lower() != "bearer"
        or not token
        or len(token) > 4096
        or any(c.isspace() for c in token)
    ):
        raise error(401, "AUTH_REQUIRED", "Entre com sua conta para continuar.")
    return token
