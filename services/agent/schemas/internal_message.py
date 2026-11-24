from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, Field


class InternalMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    session_id: Annotated[
        str,
        StringConstraints(min_length=1, max_length=80),
        Field(description="Identificador atribuído e revalidado pelo servidor."),
    ]
    apartment: Annotated[
        str,
        StringConstraints(min_length=1, max_length=32),
        Field(description="Unidade fixa da sessão, revalidada pelo servidor."),
    ]
    user_id: Annotated[
        str,
        StringConstraints(min_length=1, max_length=80),
        Field(description="Identificador atribuído e revalidado pelo servidor."),
    ]
    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
        Field(
            description="Texto público do morador; não contém identidade de autorização."
        ),
    ]
