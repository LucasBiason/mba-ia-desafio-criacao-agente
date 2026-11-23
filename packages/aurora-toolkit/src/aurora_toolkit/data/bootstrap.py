"""Criação explícita das tabelas que pertencem a cada componente Aurora."""

from collections.abc import Callable, Sequence

from sqlalchemy import Table, func, inspect, select
from sqlalchemy.orm import Session

from microservice_toolkit import Base, get_database


def initialize_tables(
    tables: Sequence[Table],
    seed_callable: Callable[[Session], None] | None = None,
    *,
    lock_key: int,
) -> bool:
    """Cria tabelas e semeia apenas uma tabela primária ainda inexistente.

    A primeira tabela é a primária do componente. Tabelas já existentes,
    inclusive vazias, conservam seus dados. Toda a operação usa a mesma
    transação, inclusive a criação das tabelas e a leitura das fontes.
    """
    if not tables:
        raise ValueError("Informe ao menos uma tabela do componente.")
    primary_table = tables[0]
    with get_database().transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(lock_key)))
        connection = session.connection()
        existed = inspect(connection).has_table(
            primary_table.name, schema=primary_table.schema
        )
        Base.metadata.create_all(connection, tables=list(tables))
        if not existed and seed_callable is not None:
            seed_callable(session)
    return not existed
