from pydantic import BaseModel, ConfigDict


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    fee_cents: int
