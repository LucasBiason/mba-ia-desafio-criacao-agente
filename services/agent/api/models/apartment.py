from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Apartment(Base):
    __tablename__ = "apartments"
    number: Mapped[str] = mapped_column(Text, primary_key=True)
