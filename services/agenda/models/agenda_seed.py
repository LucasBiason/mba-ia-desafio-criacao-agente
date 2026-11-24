from sqlalchemy import Column, ForeignKey, Text

from microservice_toolkit import Base


class AgendaSeed(Base):
    __tablename__ = "aurora_agenda_seed"
    reservation_code = Column(
        Text, ForeignKey("reservations.code", ondelete="CASCADE"), primary_key=True
    )
