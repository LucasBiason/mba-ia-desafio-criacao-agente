"""Unidade transacional e operações ORM comuns, sem commits por operação."""

from ..database import get_database


class Repository:
    def __init__(self, database=None):
        self.database = database if database is not None else get_database()
        self.session = None

    def __enter__(self):
        if self.session is not None:
            raise RuntimeError("O repository já está em uma transação.")
        session = self.database.session()
        try:
            session.begin()
        except Exception:
            session.close()
            raise
        self.session = session
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            if exception_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        except Exception:
            self.session.rollback()
            raise
        finally:
            self.session.close()
            self.session = None

    def require_session(self):
        if self.session is None:
            raise RuntimeError("Use o repository dentro de um bloco with.")
        return self.session

    def get(self, model, identity, **options):
        """Consulta pela chave primária real, inclusive composta, sem presumir id."""
        return self.require_session().get(model, identity, **options)

    def add(self, entity):
        """Inclui a entidade e faz flush; o commit pertence ao contexto."""
        session = self.require_session()
        session.add(entity)
        session.flush()
        return entity

    def delete(self, entity) -> None:
        """Exclui via ORM; constraints e rollback continuam na transação."""
        session = self.require_session()
        session.delete(entity)
        session.flush()

    def list(self, statement):
        """Executa um SELECT ORM cuja autorização e filtros vêm do domínio."""
        return list(self.require_session().scalars(statement).all())

    def first(self, statement):
        """Retorna a primeira entidade da seleção, ou None."""
        return self.require_session().scalars(statement.limit(1)).first()

    def flush(self) -> None:
        """Sincroniza alterações sem confirmar a unidade de trabalho."""
        self.require_session().flush()

    def refresh(self, entity):
        """Recarrega valores persistidos na sessão ativa e devolve a entidade."""
        self.require_session().refresh(entity)
        return entity
