from sqlalchemy import BigInteger, CheckConstraint, Column, Identity, Text

from services.persistence.base import Base

class Apartment(Base):
    __tablename__ = "apartments"

    number = Column(Text, primary_key=True)
    id = Column(BigInteger, Identity(always=True), nullable=False, unique=True)
    __table_args__ = (CheckConstraint("number ~ '^[0-9]{1,10}[A-Z]?$'"),)
