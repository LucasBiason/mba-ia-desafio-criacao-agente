"""Criação explícita das tabelas de sessão e limite de tentativas."""

from aurora_toolkit.data.bootstrap import initialize_tables
from services.authentication.models.login_limit import LoginLimit
from services.authentication.models.login_session import LoginSession
from services.users.models.account import Account  # noqa: F401 - Registra destino da chave estrangeira.


def initialize() -> bool:
    return initialize_tables(
        [LoginSession.__table__, LoginLimit.__table__], lock_key=74109143
    )
