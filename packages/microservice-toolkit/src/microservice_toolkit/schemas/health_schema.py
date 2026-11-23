"""Contrato público mínimo de prontidão, preservado entre serviços."""

from typing import Literal
from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: Literal["ready"] = "ready"
