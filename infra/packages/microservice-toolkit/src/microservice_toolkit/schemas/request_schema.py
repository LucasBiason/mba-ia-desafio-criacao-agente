"""Base opcional dos DTOs de entrada; não substitui validators de negócio.

Recusa campos extras e NUL em strings; normaliza espaços por padrão. Schemas de
credenciais precisam sobrescrever str_strip_whitespace=False para preservar senhas.
"""

from pydantic import BaseModel, ConfigDict, field_validator


class RequestSchema(BaseModel):
    """Política reutilizada por entradas Pydantic dos serviços consumidores."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def reject_null_bytes(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("O campo contém um caractere inválido.")
        return value
