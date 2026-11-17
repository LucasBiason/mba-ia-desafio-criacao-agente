from sqlalchemy import Column, Integer

from services.persistence.base import Base

class DomainMigration(Base):
    __tablename__ = "domain_migrations"

    version = Column(Integer, primary_key=True)
