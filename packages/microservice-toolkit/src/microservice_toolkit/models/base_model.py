"""Base declarativa comum; os modelos pertencem às aplicações consumidoras."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Registro SQLAlchemy vazio, sem tabelas ou domínio predefinidos."""
