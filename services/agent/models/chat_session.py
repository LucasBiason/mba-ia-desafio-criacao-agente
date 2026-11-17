from sqlalchemy import Column, DateTime, ForeignKey, Text, func

from sqlalchemy.dialects.postgresql import UUID

from services.persistence.base import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    apartment = Column(Text, ForeignKey("apartments.number", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    resident_id = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
