from datetime import date

from pydantic import BaseModel


class VisitRead(BaseModel):
    id: int
    apartment: str
    name: str
    date: date
    entry_time: str | None
    exit_time: str | None
