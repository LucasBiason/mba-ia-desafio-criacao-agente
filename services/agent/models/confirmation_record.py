"""Registro durável de confirmação; compartilha a transação com o efeito."""

from sqlalchemy import CheckConstraint, Column, DateTime, JSON, String, Index
from services.agent.models.ledger_base import LedgerBase


class ConfirmationRecord(LedgerBase):
    __tablename__ = "agent_confirmation_ledger"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    resident_id = Column(String, nullable=False)
    apartment = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')"),
        Index(
            "ix_agent_confirmation_history",
            "session_id",
            "resident_id",
            "apartment",
            "status",
            "decided_at",
            "id",
        ),
    )
