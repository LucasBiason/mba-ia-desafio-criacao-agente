"""Validação de segredos injetados pelo ambiente; nunca lê arquivos .env."""

import os
import re


def required_secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) < 32 or not value.isascii():
        raise RuntimeError(f"Configuração obrigatória ausente ou inválida: {name}.")
    return value


def validate_required_secrets(names=None) -> None:
    """Valida a declaração explícita ou REQUIRED_SECRETS (nomes separados por vírgula)."""
    if names is None:
        names = tuple(
            name.strip()
            for name in os.environ.get("REQUIRED_SECRETS", "").split(",")
            if name.strip()
        )
    for name in dict.fromkeys(names):
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", name
        ):
            raise ValueError(
                "Nomes de segredos devem ser variáveis de ambiente válidas."
            )
        required_secret(name)
