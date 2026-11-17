from sqlalchemy import CheckConstraint, Column, Index, Integer, Text, func

from services.persistence.base import Base

class Area(Base):
    __tablename__ = "areas"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    fee_cents = Column(Integer, nullable=False)
    __table_args__ = (
        CheckConstraint("fee_cents BETWEEN 0 AND 100000000"),
        CheckConstraint("id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'"),
        Index("areas_distinct_name", func.lower(name), unique=True),
    )
