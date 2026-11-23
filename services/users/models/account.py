from sqlalchemy import Boolean, CheckConstraint, Column, Text, true

from microservice_toolkit import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'resident')", name="accounts_role_check"),
    )
