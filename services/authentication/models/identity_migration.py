from sqlalchemy import Column, Integer

from services.persistence.base import Base

class IdentityMigration(Base):
    __tablename__ = "identity_migrations"

    version = Column(Integer, primary_key=True)
