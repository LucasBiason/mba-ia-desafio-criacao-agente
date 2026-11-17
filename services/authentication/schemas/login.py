from pydantic import BaseModel, ConfigDict
from services.authentication.schemas.types import Email, LoginPassword

class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: Email
    password: LoginPassword
