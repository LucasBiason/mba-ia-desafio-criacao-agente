from sqlalchemy.orm import Session

from .result import Result


class UnitOfWork:
    """Session ORM ligada à transação externa, sem commits parciais."""

    def __init__(self, connection):
        self.connection = connection
        self.orm = Session(
            bind=connection,
            join_transaction_mode="rollback_only",
            expire_on_commit=False,
        )

    @property
    def in_transaction(self):
        return self.connection.in_transaction()

    def execute(self, statement, parameters=None):
        # Compatibilidade de inspeção operacional/testes; repositórios escrevem via ORM.
        if self.connection.dialect.name == "postgresql":
            statement = statement.replace("?", "%s")
        self.orm.flush()
        return Result(self.connection.exec_driver_sql(statement, parameters or ()))

    def executemany(self, statement, parameters):
        if self.connection.dialect.name == "postgresql":
            statement = statement.replace("?", "%s")
        self.orm.flush()
        return Result(self.connection.exec_driver_sql(statement, list(parameters)))
