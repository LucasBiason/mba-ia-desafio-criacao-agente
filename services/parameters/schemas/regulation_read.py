from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class RegulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int
    content: str
    author_id: str | None
    author_name: str | None
    published_at: datetime

    @field_serializer("published_at")
    def serialize_timestamp(self, value):
        return value.isoformat()
