from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    fee_cents: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("fee_cents>=0"),)
