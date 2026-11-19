from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, Index, Integer, Text, Time, text

from services.persistence.base import Base

class Reservation(Base):
    __tablename__ = "reservations"

    code = Column(Text, primary_key=True)
    apartment = Column(Text, ForeignKey("apartments.number", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    resident_id = Column(Text)
    area_id = Column(Text, ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False)
    date = Column(Date, nullable=False)
    fee_cents = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    __table_args__ = (
        Index("reservations_active_slot", "area_id", "date", unique=True, postgresql_where=text("status = 'active'")),
        CheckConstraint("status IN ('active', 'cancelled')"),
        CheckConstraint("(start_time IS NULL AND end_time IS NULL) OR (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time)", name="reservation_hours_valid"),
    )
