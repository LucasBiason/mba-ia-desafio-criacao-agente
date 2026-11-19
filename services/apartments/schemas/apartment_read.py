from pydantic import BaseModel


class ApartmentRead(BaseModel):
    id: int
    number: str
    resident_id: str | None
