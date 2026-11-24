from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Visitor(Base):
    __tablename__ = "visitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    apartment: Mapped[str] = mapped_column(
        ForeignKey("apartments.number"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text)
    day: Mapped[str] = mapped_column(Text)
