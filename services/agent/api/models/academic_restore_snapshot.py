from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AcademicRestoreSnapshot(Base):
    __tablename__ = "academic_restore_snapshots"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text)
