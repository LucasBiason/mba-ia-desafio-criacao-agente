from pydantic import ConfigDict
from microservice_toolkit.schemas import RequestSchema
from services.authentication.schemas.types import Email, LoginPassword

class Login(RequestSchema):
    model_config = ConfigDict(str_strip_whitespace=False, hide_input_in_errors=True)
    email: Email
    password: LoginPassword
