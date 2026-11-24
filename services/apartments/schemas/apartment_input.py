from pydantic import field_validator
from aurora_toolkit.http_types import AccountId, ApartmentNumber
from microservice_toolkit.schemas import RequestSchema


class ApartmentInput(RequestSchema):
    number: ApartmentNumber
    resident_id: AccountId | None = None

    @field_validator("number")
    @classmethod
    def uppercase_number(cls, value):
        return value.upper()
