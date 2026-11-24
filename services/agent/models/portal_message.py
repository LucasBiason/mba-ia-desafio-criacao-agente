from sqlalchemy import Column, DateTime, Index, String, Text
from microservice_toolkit import Base


class PortalMessage(Base):
    __tablename__ = "agent_portal_messages"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_agent_portal_messages_timeline", "session_id", "created_at", "id"),
    )
