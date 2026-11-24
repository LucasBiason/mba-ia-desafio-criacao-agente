from pydantic import Field, field_validator
from aurora_toolkit.http_types import ApartmentNumber
from microservice_toolkit.schemas import RequestSchema


class SessionInput(RequestSchema):
    apartment: ApartmentNumber = Field(
        description="Número de uma unidade atualmente vinculada ao morador."
    )

    @field_validator("apartment")
    @classmethod
    def uppercase_apartment(cls, value):
        return value.upper()
