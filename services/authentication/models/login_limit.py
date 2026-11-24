from sqlalchemy import Column, DateTime, Integer, Text

from microservice_toolkit import Base


class LoginLimit(Base):
    __tablename__ = "login_limits"

    key = Column(Text, primary_key=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False)
