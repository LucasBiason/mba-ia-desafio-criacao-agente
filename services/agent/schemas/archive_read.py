from pydantic import BaseModel, Field


class ArchiveRead(BaseModel):
    archived: bool = Field(
        description="True após arquivar; False após restaurar. Nenhum histórico é excluído."
    )
