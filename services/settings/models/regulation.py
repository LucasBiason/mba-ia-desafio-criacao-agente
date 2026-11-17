from sqlalchemy import Column, DateTime, Integer, Text, func

from services.persistence.base import Base

class Regulation(Base):
    __tablename__ = "regulations"

    version = Column(Integer, primary_key=True, autoincrement=False)
    content = Column(Text, nullable=False)
    author_id = Column(Text)
    author_name = Column(Text)
    published_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
