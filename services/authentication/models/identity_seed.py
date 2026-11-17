from sqlalchemy import Boolean, Column

from services.persistence.base import Base

class IdentitySeed(Base):
    __tablename__ = "identity_seed"

    only_row = Column(Boolean, primary_key=True, default=True)
