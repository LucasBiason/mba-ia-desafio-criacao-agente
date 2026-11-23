"""Ciclo de vida de infraestrutura com extensão opcional do consumidor."""

from contextlib import asynccontextmanager
from .secrets import validate_required_secrets


def toolkit_lifespan(*, required_secrets=None, lifespan=None):
    """Valida segredos antes de iniciar o consumidor; não abre conexões ORM."""

    @asynccontextmanager
    async def startup(app):
        validate_required_secrets(required_secrets)
        if lifespan is None:
            yield
        else:
            async with lifespan(app) as state:
                yield state

    return startup
