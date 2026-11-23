"""Schemas compartilhados de entrada e operação."""

from .request_schema import RequestSchema
from .health_schema import HealthStatus

__all__ = ["RequestSchema", "HealthStatus"]
