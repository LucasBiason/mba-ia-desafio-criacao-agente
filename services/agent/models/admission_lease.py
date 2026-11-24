from sqlalchemy import Column, DateTime, Integer, String, Index
from microservice_toolkit import Base


class AdmissionLease(Base):
    __tablename__ = "agent_admission_leases"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False)
    resident_id = Column(String(80), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True))
    call_budget = Column(Integer, nullable=False)
    __table_args__ = (
        Index("ix_agent_admission_started", "started_at"),
        Index("ix_agent_admission_active", "resident_id", "released_at", "expires_at"),
    )
