"""Criação explícita das sessões de conversa do agente."""

from sqlalchemy import Table

from aurora_toolkit.data.bootstrap import initialize_tables
from services.agent.models.chat_session import ChatSession
from services.apartments.models.apartment import Apartment  # noqa: F401 - Registra destino da chave estrangeira.


def initialize() -> bool:
    table = ChatSession.__table__
    if not isinstance(table, Table):
        raise TypeError("ChatSession must map to a concrete SQL table.")
    return initialize_tables([table], lock_key=640206)
