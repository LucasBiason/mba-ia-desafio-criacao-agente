"""Resident-scoped transcript and reversible display archive; never deletes ADK data."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, select, func
from microservice_toolkit import Base, get_database
from aurora_toolkit.data.bootstrap import initialize_tables
from services.agent.repositories.chat_repository import ChatRepository
from services.agent.validators.chat_validator import ChatValidator


class PortalMessage(Base):
    __tablename__ = "agent_portal_messages"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class PortalArchive(Base):
    __tablename__ = "agent_portal_archives"
    resident_id = Column(Text, primary_key=True)
    apartment = Column(Text, primary_key=True)
    hidden_before = Column(DateTime(timezone=True), nullable=True)


def prepare_history():
    initialize_tables(
        [PortalMessage.__table__, PortalArchive.__table__], lock_key=640244
    )


def append_message(session_id, role, content):
    if (
        role not in ("user", "assistant")
        or not isinstance(content, str)
        or not content.strip()
    ):
        return
    with get_database().transaction() as session:
        session.add(
            PortalMessage(
                id=str(uuid4()),
                session_id=str(session_id),
                role=role,
                content=content,
                created_at=datetime.now(timezone.utc),
            )
        )


def scope(session_id, actor):
    with ChatRepository() as repository:
        record = ChatValidator(repository).validate_read(session_id, actor)
        records = [
            item
            for item in repository.list(actor["id"])
            if item.apartment == record.apartment
        ]
        return record.apartment, [str(item.id) for item in records]


def archive(session_id, actor, *, restore=False):
    apartment, _ = scope(session_id, actor)
    with get_database().transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(640245)))
        key = {"resident_id": actor["id"], "apartment": apartment}
        row = session.get(PortalArchive, key)
        if row is None:
            row = PortalArchive(**key)
            session.add(row)
        row.hidden_before = None if restore else datetime.now(timezone.utc)
    return {"archived": not restore}


def public_events(events):
    """No function args/results, system instructions or thinking are public history."""
    rows = []
    for event in events:
        if not event.content:
            continue
        timestamp = datetime.fromtimestamp(event.timestamp, timezone.utc).isoformat()
        if event.content.role == "user" and event.author != "user":
            for index, part in enumerate(event.content.parts or []):
                response = part.function_response
                if response and response.name in (
                    "reservar_area",
                    "cancelar_reserva",
                    "autorizar_visita",
                ):
                    text = receipt_text(response.response)
                    if text:
                        rows.append(
                            {
                                "id": f"adk:{event.id}:receipt:{index}",
                                "role": "assistant",
                                "content": text,
                                "created_at": timestamp,
                                "_receipt_status": response.response.get("status"),
                            }
                        )
        if event.author != "user" and not event.is_final_response():
            continue
        content = "\n".join(
            p.text for p in event.content.parts or [] if p.text and not p.thought
        )
        if content.strip():
            rows.append(
                {
                    "id": "adk:" + str(event.id),
                    "role": "user" if event.author == "user" else "assistant",
                    "content": content,
                    "created_at": timestamp,
                }
            )
    return rows


async def history(
    session_id, actor, service, *, limit=50, before=None, include_pending=False
):
    import asyncio

    apartment, ids = await asyncio.to_thread(scope, session_id, actor)

    def persisted():
        with get_database().transaction() as session:
            rows = session.scalars(
                select(PortalMessage).where(PortalMessage.session_id.in_(ids))
            ).all()
            archive_row = session.get(
                PortalArchive, {"resident_id": actor["id"], "apartment": apartment}
            )
            hidden = archive_row.hidden_before if archive_row else None
            return [
                {
                    "id": row.id,
                    "role": row.role,
                    "content": row.content,
                    "created_at": row.created_at.replace(
                        tzinfo=timezone.utc
                    ).isoformat(),
                    "session_id": row.session_id,
                }
                for row in rows
            ], hidden

    rows, hidden = await asyncio.to_thread(persisted)
    earliest = {
        sid: min(
            (r["created_at"] for r in rows if r["session_id"] == sid), default=None
        )
        for sid in ids
    }
    if include_pending:

        def prior_decisions():
            from services.agent.confirmations.ledger import ConfirmationRecord

            with get_database().transaction() as session:
                records = session.scalars(
                    select(ConfirmationRecord)
                    .where(
                        ConfirmationRecord.session_id.in_(ids),
                        ConfirmationRecord.resident_id == actor["id"],
                        ConfirmationRecord.apartment == apartment,
                        ConfirmationRecord.status != "pending",
                    )
                    .order_by(ConfirmationRecord.decided_at, ConfirmationRecord.id)
                )
                result = []
                for record in records:
                    stamp = (
                        record.decided_at.replace(tzinfo=timezone.utc).isoformat()
                        if record.decided_at
                        else None
                    )
                    text = receipt_text(
                        {"status": "rejected"}
                        if record.status == "rejected"
                        else record.result
                    )
                    if text and stamp:
                        result.append(
                            {
                                "id": "ledger:" + record.id,
                                "role": "assistant",
                                "content": text,
                                "created_at": stamp,
                                "session_id": record.session_id,
                            }
                        )
                return result

        decisions = await asyncio.to_thread(prior_decisions)
        # Match each normal persisted receipt at most once, within its own
        # decision interval. A later successful identical decision cannot hide
        # an earlier failed append. Never use the first-message cutoff for ledger.
        matched = set()
        for index, decision in enumerate(decisions):
            later = next(
                (
                    item["created_at"]
                    for item in decisions[index + 1 :]
                    if item["session_id"] == decision["session_id"]
                ),
                None,
            )
            candidate = next(
                (
                    row
                    for row in sorted(
                        rows, key=lambda item: (item["created_at"], item["id"])
                    )
                    if row["id"] not in matched
                    and row.get("session_id") == decision["session_id"]
                    and row["role"] == "assistant"
                    and row["content"] == decision["content"]
                    and row["created_at"] >= decision["created_at"]
                    and (later is None or row["created_at"] < later)
                ),
                None,
            )
            if candidate:
                matched.add(candidate["id"])
            else:
                rows.append(decision)
    adk_receipts = []
    if service is not None:
        for sid in ids:
            for app_name in (
                "aurora_read_probe",
                "aurora_multi_read",
                "aurora_resident_actions",
            ):
                session = await service.get_session(
                    app_name=app_name, user_id=actor["id"], session_id=sid
                )
                if session:
                    for row in public_events(session.events):
                        row["session_id"] = sid
                        if row.get("_receipt_status") in ("reserved", "cancelled"):
                            adk_receipts.append(row)
                        elif earliest[sid] is None or row["created_at"] < earliest[sid]:
                            rows.append(row)
    # Post-transcript free/cancel receipts are durable ADK evidence, not legacy
    # prose. Recover them regardless of the first transcript timestamp.
    adk_receipts.sort(key=lambda row: (row["created_at"], row["id"]))
    consumed = set()
    for index, receipt in enumerate(adk_receipts):
        later = next(
            (
                row["created_at"]
                for row in adk_receipts[index + 1 :]
                if row["session_id"] == receipt["session_id"]
            ),
            None,
        )
        candidate = next(
            (
                row
                for row in sorted(rows, key=lambda r: (r["created_at"], r["id"]))
                if row["id"] not in consumed
                and row.get("session_id") == receipt["session_id"]
                and row["role"] == "assistant"
                and row["content"] == receipt["content"]
                and (
                    (
                        row["id"].startswith("ledger:")
                        and receipt["_receipt_status"] == "reserved"
                    )
                    or (
                        row["created_at"] >= receipt["created_at"]
                        and (later is None or row["created_at"] < later)
                    )
                )
            ),
            None,
        )
        if candidate is not None:
            consumed.add(candidate["id"])
        else:
            rows.append(receipt)
    cutoff = hidden.replace(tzinfo=timezone.utc).isoformat() if hidden else None
    rows = [
        {k: v for k, v in row.items() if k != "session_id" and not k.startswith("_")}
        for row in rows
        if (not cutoff or row["created_at"] > cutoff)
    ]
    rows.sort(key=lambda row: (row["created_at"], row["id"]))
    if before:
        positions = [i for i, row in enumerate(rows) if row["id"] == before]
        rows = rows[: positions[0]] if positions else []
    page = rows[-limit:]
    pending = []
    if include_pending:
        from services.agent.runtime.resident_actions import ProductActions
        from services.agent.tools.reservation_read import SessionIdentity

        for sid in ids:
            items = await asyncio.to_thread(
                ProductActions(
                    SessionIdentity.from_authenticated_actor(sid, actor)
                ).pending
            )
            pending.extend({**item, "session_id": sid} for item in items)
    await asyncio.to_thread(
        scope, session_id, actor
    )  # Recheck ownership before disclosure.
    return {
        "messages": page,
        "next_cursor": page[0]["id"] if len(rows) > limit else None,
        "confirmacoes_pendentes": pending,
        "archived": bool(hidden),
    }


def append_result_safely(session_id, content):
    """A transcript failure must never turn a committed effect into retry advice."""
    try:
        append_message(session_id, "assistant", content)
        return True
    except Exception:
        import logging

        logging.getLogger(__name__).error(
            "Portal transcript persistence failed; effect is not replayed."
        )
        return False


def receipt_text(result):
    """Small allowlist for past committed receipts, not arbitrary tool payloads."""
    if not isinstance(result, dict):
        return None
    status = result.get("status")
    if status == "reserved":
        import re

        code = result.get("code", "")
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", code):
            return f"Reserva gravada. Código: {code}."
        return "Reserva gravada."
    return {
        "cancelled": "Sua reserva foi cancelada.",
        "authorized": "A autorização do visitante foi gravada.",
        "rejected": "Pedido negado. Nenhuma alteração foi feita.",
        "occupied": "A área já está ocupada nessa data. Nenhuma reserva foi criada.",
        "pending": "Pedido enviado para confirmação no portal.",
        "policy_changed": "Regulamento alterado. Nenhuma alteração foi feita.",
    }.get(status)
