from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    id: str = Field(description="Identificador estável da mensagem pública ou recibo.")
    role: Literal["user", "assistant"] = Field(description="Autor público da mensagem.")
    content: str = Field(
        description="Texto público; exclui pensamentos e argumentos internos de ferramentas."
    )
    created_at: datetime = Field(
        description="Instante UTC persistido, com fuso horário."
    )
    sourceSessionId: str = Field(
        description="Sessão de origem do item no histórico contínuo da unidade."
    )
