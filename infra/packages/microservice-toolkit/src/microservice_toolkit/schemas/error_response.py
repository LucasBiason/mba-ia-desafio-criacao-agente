"""Envelope de erro HTTP sem alterar o contrato das exceções existentes."""

from pydantic import BaseModel, Field
from .error_detail import ErrorDetail


class ErrorResponse(BaseModel):
    detail: ErrorDetail | str = Field(
        description="Erro estruturado do domínio ou mensagem textual de protocolo."
    )
