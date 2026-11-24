from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AcademicConfirmation(Base):
    __tablename__ = "academic_confirmations"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(Text)
    invocation: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, default="pending", server_default="pending"
    )
