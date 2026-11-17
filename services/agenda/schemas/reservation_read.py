from datetime import date

from pydantic import BaseModel


class ReservationRead(BaseModel):
    code: str
    apartment: str
    area_id: str
    area_name: str
    date: date
    fee_cents: int
    status: str
    start_time: str | None
    end_time: str | None
