"""Diagnóstico público disponível somente fora de produção."""

from pydantic import BaseModel, Field


class ErrorDiagnostic(BaseModel):
    exception_type: str = Field(description="Tipo da exceção, sem valores locais.")
    message: str = Field(description="Mensagem sanitizada da falha.")
    traceback: str = Field(description="Quadros e causas sanitizados para depuração.")
