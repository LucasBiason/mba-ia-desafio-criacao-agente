from sqlalchemy import BigInteger, CheckConstraint, Column, Date, ForeignKey, Identity, Text, Time

from services.persistence.base import Base

class Visit(Base):
    __tablename__ = "visits"

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    apartment = Column(Text, ForeignKey("apartments.number", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    resident_id = Column(Text)
    name = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    entry_time = Column(Time)
    exit_time = Column(Time)
    __table_args__ = (CheckConstraint("exit_time IS NULL OR (entry_time IS NOT NULL AND entry_time < exit_time)", name="visit_hours_valid"),)
