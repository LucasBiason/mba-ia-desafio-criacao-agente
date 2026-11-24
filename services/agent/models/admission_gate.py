"""Verrou transacional compartilhado entre processos e réplicas."""

from sqlalchemy import Column, Integer
from microservice_toolkit import Base


class AdmissionGate(Base):
    __tablename__ = "agent_admission_gate"
    id = Column(Integer, primary_key=True)
    revision = Column(Integer, nullable=False, default=0)
