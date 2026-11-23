from sqlalchemy import BigInteger, Column, ForeignKey, Text

from microservice_toolkit import Base


class ApartmentResident(Base):
    __tablename__ = "apartment_residents"

    apartment_id = Column(
        BigInteger, ForeignKey("apartments.id", ondelete="CASCADE"), primary_key=True
    )
    resident_id = Column(Text, nullable=False, index=True)
