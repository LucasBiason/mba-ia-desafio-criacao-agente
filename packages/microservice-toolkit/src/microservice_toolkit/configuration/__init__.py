"""Configuração de infraestrutura injetada pelo ambiente."""

from .secrets import required_secret, validate_required_secrets

__all__ = ["required_secret", "validate_required_secrets"]
