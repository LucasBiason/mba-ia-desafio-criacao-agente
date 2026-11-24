"""Fachada pública do domínio acadêmico isolado."""

from .repositories.academic_repository import AcademicRepository
from .repositories.bound_domain_repository import BoundDomain as BoundDomain


class AcademicDomain(AcademicRepository):
    """Domínio acadêmico com persistência ORM e perfil SQLite explícito."""
