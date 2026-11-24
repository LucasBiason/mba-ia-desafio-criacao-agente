from sqlalchemy import CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AcademicSeed(Base):
    __tablename__ = "academic_seed"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    __table_args__ = (CheckConstraint("version=1"),)
