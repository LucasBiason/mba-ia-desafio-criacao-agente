from sqlalchemy import Column, DateTime, Text
from microservice_toolkit import Base


class PortalArchive(Base):
    __tablename__ = "agent_portal_archives"
    resident_id = Column(Text, primary_key=True)
    apartment = Column(Text, primary_key=True)
    hidden_before = Column(DateTime(timezone=True), nullable=True)
