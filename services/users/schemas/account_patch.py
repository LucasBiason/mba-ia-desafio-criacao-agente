from pydantic import BaseModel, ConfigDict
from services.authentication.schemas.types import Email, Name, Password, Role

class AccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: Name | None = None
    email: Email | None = None
    password: Password | None = None
    role: Role | None = None
    active: bool | None = None
