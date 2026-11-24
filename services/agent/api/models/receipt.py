from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Receipt(Base):
    __tablename__ = "receipts"
    operation_id: Mapped[str] = mapped_column(Text, primary_key=True)
    apartment: Mapped[str] = mapped_column(
        ForeignKey("apartments.number"), nullable=False
    )
    action: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text)
