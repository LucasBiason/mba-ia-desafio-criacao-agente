"""Engine e sessões SQLAlchemy com configuração explícita ou DATABASE_URL."""

from contextlib import contextmanager
from functools import cached_property, lru_cache
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class Database:
    def __init__(self, url_provider, *, connect_args=None):
        self.url_provider = url_provider
        self.connect_args = dict(connect_args or {})

    @cached_property
    def engine(self):
        return create_engine(
            self.url_provider(), pool_pre_ping=True, connect_args=self.connect_args
        )

    def session(self):
        return Session(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self):
        with self.session() as session, session.begin():
            yield session


@lru_cache(maxsize=1)
def get_database() -> Database:
    """Cria o Database padrão sob demanda, sem conectar ou criar tabelas.

    DATABASE_URL deve incluir o driver SQLAlchemy desejado; seu valor é capturado
    na primeira chamada. Mudanças de configuração exigem reinício do processo.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url.strip():
        raise RuntimeError("Configuração obrigatória ausente: DATABASE_URL.")
    return Database(lambda: url)
