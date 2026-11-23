from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class InternalMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    session_id: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    apartment: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    user_id: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
