from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    apartment: str
    created_at: datetime
    status: str = "awaiting_agent"

    @field_serializer("created_at")
    def serialize_timestamp(self, value):
        return value.isoformat()
