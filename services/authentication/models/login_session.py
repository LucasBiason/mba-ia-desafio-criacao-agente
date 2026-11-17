from sqlalchemy import Column, DateTime, ForeignKey, Text

from services.persistence.base import Base

class LoginSession(Base):
    __tablename__ = "sessions"

    id = Column(Text, primary_key=True)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
