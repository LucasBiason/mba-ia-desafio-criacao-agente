"""Configuração explícita dos diagnósticos; produção nunca expõe traceback."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ErrorPolicy:
    environment: str = "production"
    debug: bool = False

    def __post_init__(self):
        if self.environment not in {"production", "development", "test"}:
            raise ValueError("environment deve ser production, development ou test.")
        if self.environment == "production" and self.debug:
            raise ValueError(
                "Diagnósticos públicos não podem ser habilitados em produção."
            )

    @classmethod
    def from_settings(cls, environment=None, debug=None):
        selected = environment or os.environ.get("SERVICE_ENVIRONMENT", "production")
        enabled = selected != "production" if debug is None else debug
        if not isinstance(enabled, bool):
            raise ValueError("debug deve ser booleano.")
        return cls(selected, enabled)
