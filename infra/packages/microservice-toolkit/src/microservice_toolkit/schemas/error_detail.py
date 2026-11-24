"""Detalhes do erro de domínio e de validação compartilhados pelas APIs."""

from pydantic import BaseModel, Field
from .error_diagnostic import ErrorDiagnostic
from .validation_field import ValidationField


class ErrorDetail(BaseModel):
    code: str = Field(
        description="Código de erro estável para tratamento pelo cliente."
    )
    message: str = Field(
        description="Mensagem pública sem credenciais ou dados privados."
    )
    fields: list[ValidationField] | None = Field(
        default=None, description="Campos recusados na validação de entrada."
    )
    request_id: str | None = Field(
        default=None, description="Identificador de correlação com o log do serviço."
    )
    method: str | None = Field(
        default=None, description="Método HTTP da operação que falhou."
    )
    route: str | None = Field(
        default=None, description="Template da rota, sem valores privados da URL."
    )
    debug: ErrorDiagnostic | None = Field(
        default=None, description="Diagnóstico sanitizado; nunca retornado em produção."
    )
