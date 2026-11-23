"""Contrato HTTP e política de diagnóstico de falhas."""

from .handlers import (
    database_unavailable,
    error,
    failure_response,
    http_error,
    http_exception_response,
    invalid_input,
    unexpected_error,
)
from .policy import ErrorPolicy

__all__ = [
    "database_unavailable",
    "error",
    "failure_response",
    "http_error",
    "http_exception_response",
    "invalid_input",
    "unexpected_error",
    "ErrorPolicy",
]
