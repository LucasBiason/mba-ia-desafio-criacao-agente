from pydantic import ConfigDict
from microservice_toolkit.schemas import RequestSchema
from services.authentication.schemas.types import Email, Name, Password, Role

class AccountPatch(RequestSchema):
    model_config = ConfigDict(str_strip_whitespace=False, hide_input_in_errors=True)
    name: Name | None = None
    email: Email | None = None
    password: Password | None = None
    role: Role | None = None
    active: bool | None = None
