from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AcademicConfirmationOutcome(Base):
    __tablename__ = "academic_confirmation_outcomes"
    confirmation_id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(Text)
    apartment: Mapped[str] = mapped_column(Text)
    operation_id: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
