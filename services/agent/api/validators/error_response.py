from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Erro HTTP de domínio, concorrência ou disponibilidade."""

    detail: str
