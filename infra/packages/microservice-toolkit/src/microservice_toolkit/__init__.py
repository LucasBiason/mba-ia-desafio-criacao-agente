"""Infraestrutura HTTP e ORM compartilhada, sem regras de domínio."""

from .setup_api import ApplicationFactory, create_app
from .middleware import AuthenticationMiddleware
from .auth import bearer_token, internal_guard
from .configuration import required_secret
from .exceptions import ErrorPolicy, error
from .routers import HealthRouter
from .schemas import HealthStatus
from .models import Base
from .database import Database, get_database
from .repository import Repository
from .schemas import RequestSchema
from .services import ServiceClient

__all__ = [
    "ApplicationFactory",
    "AuthenticationMiddleware",
    "Base",
    "Database",
    "ErrorPolicy",
    "HealthRouter",
    "HealthStatus",
    "Repository",
    "RequestSchema",
    "ServiceClient",
    "bearer_token",
    "create_app",
    "error",
    "get_database",
    "internal_guard",
    "required_secret",
]
