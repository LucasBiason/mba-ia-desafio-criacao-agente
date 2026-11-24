from aurora_toolkit.http_types import Hour
from microservice_toolkit.schemas import RequestSchema


class VisitHours(RequestSchema):
    entry_time: Hour | None = None
    exit_time: Hour | None = None
