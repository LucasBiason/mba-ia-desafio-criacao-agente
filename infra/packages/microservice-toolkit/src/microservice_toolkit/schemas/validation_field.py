"""Descrição pública de um campo inválido, sem o valor recebido."""

from pydantic import BaseModel, Field


class ValidationField(BaseModel):
    field: str = Field(description="Localização do campo inválido na requisição.")
    code: str = Field(description="Código estável da validação aplicada.")
    message: str = Field(description="Orientação pública para corrigir o campo.")
