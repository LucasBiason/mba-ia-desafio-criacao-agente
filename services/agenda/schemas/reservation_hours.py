from aurora_toolkit.http_types import Hour
from microservice_toolkit.schemas import RequestSchema


class ReservationHours(RequestSchema):
    start_time: Hour | None
    end_time: Hour | None
