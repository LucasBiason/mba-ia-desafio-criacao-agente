from pydantic import field_validator
from services.http_types import AreaName, FeeCents
from microservice_toolkit.schemas import RequestSchema


class AreaPatch(RequestSchema):
    name: AreaName | None = None
    fee_cents: FeeCents | None = None

    @field_validator("name", "fee_cents")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Informe o valor do campo.")
        return value
