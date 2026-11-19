from services.http_types import AreaId, AreaName, FeeCents
from microservice_toolkit.schemas import RequestSchema


class AreaInput(RequestSchema):
    id: AreaId
    name: AreaName
    fee_cents: FeeCents
