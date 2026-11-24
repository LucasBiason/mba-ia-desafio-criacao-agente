"""Adaptador do ADK que exige schema preparado e nunca executa DDL no HTTP."""

from google.adk.sessions import DatabaseSessionService
from google.adk.sessions.migration import _schema_check_utils
from sqlalchemy import inspect

from .session_store_not_prepared import SessionStoreNotPrepared


class PreparedSessionService(DatabaseSessionService):
    async def prepare_tables(self) -> None:
        if self._tables_created:
            return
        async with self._table_creation_lock:
            if self._tables_created:
                return
            async with self.db_engine.connect() as connection:
                version = await connection.run_sync(
                    _schema_check_utils.get_db_schema_version_from_connection
                )
                self._db_schema_version = version
                schema = self._get_schema_classes()
                required = (
                    schema.StorageSession,
                    schema.StorageEvent,
                    schema.StorageAppState,
                    schema.StorageUserState,
                )

                def verify(raw):
                    inspector = inspect(raw)
                    names = set(inspector.get_table_names())
                    for model in required:
                        table = model.__table__
                        if table.name not in names or not set(table.columns.keys()) <= {
                            column["name"]
                            for column in inspector.get_columns(table.name)
                        }:
                            raise SessionStoreNotPrepared(
                                "Execute init antes de servir HTTP."
                            )

                await connection.run_sync(verify)
            self._tables_created = True
