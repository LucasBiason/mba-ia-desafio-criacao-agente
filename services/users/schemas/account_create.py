from pydantic import ConfigDict
from microservice_toolkit.schemas import RequestSchema
from services.authentication.schemas.types import Email, Name, Password, Role

class AccountCreate(RequestSchema):
    model_config = ConfigDict(str_strip_whitespace=False, hide_input_in_errors=True)
    name: Name
    email: Email
    password: Password
    role: Role = "resident"
