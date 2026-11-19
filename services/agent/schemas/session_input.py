from pydantic import field_validator
from services.http_types import ApartmentNumber
from microservice_toolkit.schemas import RequestSchema


class SessionInput(RequestSchema):
    apartment: ApartmentNumber

    @field_validator("apartment")
    @classmethod
    def uppercase_apartment(cls, value):
        return value.upper()
