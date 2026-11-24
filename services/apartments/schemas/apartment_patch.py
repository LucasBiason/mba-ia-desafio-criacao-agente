from pydantic import field_validator
from aurora_toolkit.http_types import ApartmentNumber
from .apartment_input import ApartmentInput


class ApartmentPatch(ApartmentInput):
    number: ApartmentNumber | None = None

    @field_validator("number")
    @classmethod
    def uppercase_number(cls, value):
        if value is None:
            raise ValueError("Informe o número do apartamento.")
        return value.upper()
