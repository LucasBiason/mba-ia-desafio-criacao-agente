"""Adapter de leitura paginada para o schema do ADK fixado no projeto.

get_session materializa todos os eventos antes de filtrar; a consulta ORM neste
adapter aplica o cursor e LIMIT no banco. Não prepara nem altera tabelas.
"""

from datetime import datetime, timezone
from sqlalchemy import cast, exists, func, inspect, or_, select
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.ext.asyncio import AsyncSession
from google.adk.sessions.base_session_service import GetSessionConfig
from services.agent.repositories.portal_history_repository import utc


class AdkHistoryRepository:
    APP_NAMES = ("aurora_read_probe", "aurora_multi_read", "aurora_resident_actions")

    def __init__(self, service):
        self.service = service

    async def events(self, ids, actor_id, limit, cursor=None):
        if self.service is None:
            return [], False, None
        if not hasattr(self.service, "db_engine"):
            # Injectable/in-memory session service: ask its API for a bounded
            # window. Production uses the ORM adapter below, including cursors.
            events = []
            for sid in ids:
                for app in self.APP_NAMES:
                    session = await self.service.get_session(
                        app_name=app,
                        user_id=actor_id,
                        session_id=sid,
                        config=GetSessionConfig(num_recent_events=limit),
                    )
                    if session:
                        events.extend((sid, event) for event in session.events)
            events.sort(key=lambda pair: (pair[1].timestamp, pair[1].id), reverse=True)
            if cursor:
                events = [
                    pair
                    for pair in events
                    if (
                        datetime.fromtimestamp(pair[1].timestamp, timezone.utc),
                        "adk:" + str(pair[1].id),
                    )
                    <= cursor
                ]
            return events[:limit], len(events) >= limit, None
        async with self.service.db_engine.connect() as connection:
            exists = await connection.run_sync(
                lambda conn: inspect(conn).has_table("events")
            )
        if not exists:
            return [], False, None
        # _get_schema_classes follows the SDK's prepared schema version and is
        # confined here; no router or runtime depends on SDK persistence types.
        await self.service.prepare_tables()
        model = self.service._get_schema_classes().StorageEvent
        async with AsyncSession(self.service.db_engine) as session:
            stmt = select(model).where(
                model.app_name.in_(self.APP_NAMES),
                model.user_id == actor_id,
                model.session_id.in_(ids),
            )
            if cursor:
                # Include the boundary event so its receipt parts sharing the
                # timestamp can be filtered by the public id without loss.
                stamp, key = cursor
                raw_key = key.removeprefix("adk:").split(":receipt:")[0]
                stmt = stmt.where(
                    or_(
                        model.timestamp < stamp,
                        (model.timestamp == stamp) & (model.id <= raw_key),
                    )
                )
            rows = list(
                (
                    await session.scalars(
                        stmt.order_by(model.timestamp.desc(), model.id.desc()).limit(
                            limit
                        )
                    )
                ).all()
            )
            events = [(row.session_id, row.to_event()) for row in rows]
            floor = (
                (utc(rows[-1].timestamp), "adk:" + str(rows[-1].id))
                if len(rows) == limit
                else None
            )
            return events, len(rows) == limit, floor

    async def next_receipt(self, receipt, actor_id):
        """Próximo recibo no banco, mesmo fora da página; evita casar outra decisão."""
        if self.service is None or not hasattr(self.service, "db_engine"):
            return None
        model = self.service._get_schema_classes().StorageEvent
        if self.service.db_engine.dialect.name == "postgresql":
            content = (
                cast(model.event_data, JSONB)["content"]
                if hasattr(model, "event_data")
                else cast(model.content, JSONB)
            )
            receipt_condition = func.jsonb_path_exists(
                cast(content, JSONB),
                cast(
                    '$.parts[*].function_response ? ((@.name == "reservar_area" || @.name == "cancelar_reserva" || @.name == "executar_reserva_validada" || @.name == "executar_convivencia_validada") && (@.response.status == "reserved" || @.response.status == "cancelled"))',
                    JSONPATH,
                ),
            )
        else:
            content = (
                func.json_extract(model.event_data, "$.content")
                if hasattr(model, "event_data")
                else model.content
            )
            parts = func.json_each(content, "$.parts").table_valued("value")
            receipt_condition = exists(
                select(1)
                .select_from(parts)
                .where(
                    func.json_extract(parts.c.value, "$.function_response.name").in_(
                        (
                            "reservar_area",
                            "cancelar_reserva",
                            "executar_reserva_validada",
                            "executar_convivencia_validada",
                        )
                    ),
                    func.json_extract(
                        parts.c.value, "$.function_response.response.status"
                    ).in_(("reserved", "cancelled")),
                )
            )
        stamp = datetime.fromisoformat(receipt["created_at"])
        event_id = receipt["id"].removeprefix("adk:").split(":receipt:")[0]
        stmt = (
            select(model.timestamp)
            .where(
                model.app_name.in_(self.APP_NAMES),
                model.user_id == actor_id,
                model.session_id == receipt["session_id"],
                or_(
                    model.timestamp > stamp,
                    (model.timestamp == stamp) & (model.id > event_id),
                ),
                receipt_condition,
            )
            .order_by(model.timestamp, model.id)
            .limit(1)
        )
        async with AsyncSession(self.service.db_engine) as session:
            value = await session.scalar(stmt)
            return utc(value) if value else None
