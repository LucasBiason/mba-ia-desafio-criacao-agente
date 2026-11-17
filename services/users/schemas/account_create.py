from pydantic import BaseModel, ConfigDict
from services.authentication.schemas.types import Email, Name, Password, Role

class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: Name
    email: Email
    password: Password
    role: Role = "resident"
