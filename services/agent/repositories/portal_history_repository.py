"""Consultas limitadas do transcript, arquivo reversível e recibos duráveis."""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import and_, func, or_, select
from microservice_toolkit import get_database
from services.agent.models.portal_message import PortalMessage
from services.agent.models.portal_archive import PortalArchive
from services.agent.models.confirmation_record import ConfirmationRecord


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def page_condition(timestamp, key, cursor):
    if cursor is None:
        return True
    stamp, ident = cursor
    return or_(timestamp < stamp, and_(timestamp == stamp, key < ident))


class PortalHistoryRepository:
    def __init__(self, database=None):
        self.database = database or get_database()

    def append(self, session_id, role, content):
        if (
            role not in ("user", "assistant")
            or not isinstance(content, str)
            or not content.strip()
        ):
            return
        with self.database.transaction() as session:
            session.add(
                PortalMessage(
                    id=str(uuid4()),
                    session_id=str(session_id),
                    role=role,
                    content=content,
                    created_at=datetime.now(timezone.utc),
                )
            )

    def archive(self, actor_id, apartment, restore):
        with self.database.transaction() as session:
            # Serialize create/update across processes without holding a lock in HTTP.
            session.execute(select(func.pg_advisory_xact_lock(640245)))
            key = {"resident_id": actor_id, "apartment": apartment}
            row = session.get(PortalArchive, key)
            if row is None:
                row = PortalArchive(**key)
                session.add(row)
            row.hidden_before = None if restore else datetime.now(timezone.utc)

    def hidden_before(self, actor_id, apartment):
        with self.database.transaction() as session:
            row = session.get(
                PortalArchive, {"resident_id": actor_id, "apartment": apartment}
            )
            return utc(row.hidden_before) if row and row.hidden_before else None

    def earliest(self, ids):
        with self.database.transaction() as session:
            return {
                sid: utc(stamp)
                for sid, stamp in session.execute(
                    select(PortalMessage.session_id, func.min(PortalMessage.created_at))
                    .where(PortalMessage.session_id.in_(ids))
                    .group_by(PortalMessage.session_id)
                )
            }

    def cursor_for_message(self, ident, ids):
        with self.database.transaction() as session:
            row = session.scalar(
                select(PortalMessage)
                .where(PortalMessage.id == ident, PortalMessage.session_id.in_(ids))
                .limit(1)
            )
            return (utc(row.created_at), row.id) if row else None

    def messages(self, ids, limit, cursor, cutoff):
        with self.database.transaction() as session:
            statement = select(PortalMessage).where(
                PortalMessage.session_id.in_(ids),
                page_condition(PortalMessage.created_at, PortalMessage.id, cursor),
            )
            if cutoff:
                statement = statement.where(PortalMessage.created_at > cutoff)
            return [
                dict(
                    id=row.id,
                    role=row.role,
                    content=row.content,
                    created_at=utc(row.created_at).isoformat(),
                    session_id=row.session_id,
                )
                for row in session.scalars(
                    statement.order_by(
                        PortalMessage.created_at.desc(), PortalMessage.id.desc()
                    ).limit(limit)
                )
            ]

    def decisions(self, ids, actor_id, apartment, limit, cursor, cutoff):
        with self.database.transaction() as session:
            key = "ledger:" + ConfirmationRecord.id
            statement = select(ConfirmationRecord).where(
                ConfirmationRecord.session_id.in_(ids),
                ConfirmationRecord.resident_id == actor_id,
                ConfirmationRecord.apartment == apartment,
                ConfirmationRecord.status != "pending",
                ConfirmationRecord.decided_at.is_not(None),
                page_condition(ConfirmationRecord.decided_at, key, cursor),
            )
            if cutoff:
                statement = statement.where(ConfirmationRecord.decided_at > cutoff)
            records = session.scalars(
                statement.order_by(
                    ConfirmationRecord.decided_at.desc(), ConfirmationRecord.id.desc()
                ).limit(limit)
            )
            return [
                dict(
                    id="ledger:" + row.id,
                    session_id=row.session_id,
                    created_at=utc(row.decided_at).isoformat(),
                    result={"status": "rejected"}
                    if row.status == "rejected"
                    else row.result,
                )
                for row in records
            ]

    def next_decision(self, decision, ids, actor_id, apartment):
        stamp = datetime.fromisoformat(decision["created_at"])
        with self.database.transaction() as session:
            result = session.scalar(
                select(ConfirmationRecord.decided_at)
                .where(
                    ConfirmationRecord.session_id == decision["session_id"],
                    ConfirmationRecord.session_id.in_(ids),
                    ConfirmationRecord.resident_id == actor_id,
                    ConfirmationRecord.apartment == apartment,
                    ConfirmationRecord.status != "pending",
                    ConfirmationRecord.decided_at > stamp,
                )
                .order_by(ConfirmationRecord.decided_at)
                .limit(1)
            )
            return utc(result) if result else None

    def has_normal_receipt(self, receipt, later=None):
        stamp = datetime.fromisoformat(receipt["created_at"])
        with self.database.transaction() as session:
            statement = select(PortalMessage.id).where(
                PortalMessage.session_id == receipt["session_id"],
                PortalMessage.role == "assistant",
                PortalMessage.content == receipt["content"],
                PortalMessage.created_at >= stamp,
            )
            if later:
                statement = statement.where(PortalMessage.created_at < later)
            return session.scalar(statement.limit(1)) is not None

    def has_ledger_reservation(self, receipt, actor_id, apartment):
        result = receipt.get("_result", {})
        if result.get("status") != "reserved" or not result.get("code"):
            return False
        with self.database.transaction() as session:
            return (
                session.scalar(
                    select(ConfirmationRecord.id)
                    .where(
                        ConfirmationRecord.session_id == receipt["session_id"],
                        ConfirmationRecord.resident_id == actor_id,
                        ConfirmationRecord.apartment == apartment,
                        ConfirmationRecord.status == "approved",
                        ConfirmationRecord.result["status"].as_string() == "reserved",
                        ConfirmationRecord.result["code"].as_string() == result["code"],
                    )
                    .limit(1)
                )
                is not None
            )
