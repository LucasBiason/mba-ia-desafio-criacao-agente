"""Criação explícita do regulamento original do condomínio."""

from sqlalchemy.orm import Session

from aurora_toolkit.data.bootstrap import initialize_tables
from aurora_toolkit.data.fixtures import read_text
from services.parameters.models.regulation import Regulation


def seed_regulation(session: Session) -> None:
    session.add(Regulation(version=0, content=read_text("regulamento.md")))


def initialize() -> bool:
    return initialize_tables([Regulation.__table__], seed_regulation, lock_key=640205)
