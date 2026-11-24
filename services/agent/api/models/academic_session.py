from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AcademicSession(Base):
    __tablename__ = "academic_sessions"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    apartment: Mapped[str] = mapped_column(Text)
