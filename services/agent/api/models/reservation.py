from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Reservation(Base):
    __tablename__ = "reservations"
    code: Mapped[str] = mapped_column(Text, primary_key=True)
    apartment: Mapped[str] = mapped_column(
        ForeignKey("apartments.number"), nullable=False
    )
    area: Mapped[str] = mapped_column(ForeignKey("areas.id"), nullable=False)
    day: Mapped[str] = mapped_column(Text)
    active: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __table_args__ = (
        CheckConstraint("active IN (0,1)"),
        Index(
            "one_active_reservation",
            "area",
            "day",
            unique=True,
            sqlite_where=text("active=1"),
            postgresql_where=text("active=1"),
        ),
    )
