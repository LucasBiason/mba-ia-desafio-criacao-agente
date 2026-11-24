"""Histórico privado contínuo; paginação aplicada em cada origem persistida."""

import asyncio
import base64
import json
from datetime import datetime, timezone

from microservice_toolkit import error, get_database

from services.agent.models.portal_archive import (
    PortalArchive,  # noqa: F401 - Export compatível.
)
from services.agent.models.portal_message import (
    PortalMessage,  # noqa: F401 - Export compatível.
)
from services.agent.repositories.adk_history_repository import AdkHistoryRepository
from services.agent.repositories.chat_repository import ChatRepository
from services.agent.repositories.portal_history_repository import (
    PortalHistoryRepository,
)
from services.agent.validators.chat_validator import ChatValidator


def prepare_history():
    """Compatibilidade da preparação explícita; nunca chamada pelo servidor HTTP."""
    from services.agent.bootstrap import initialize

    return initialize()


def append_message(session_id, role, content):
    return PortalHistoryRepository(get_database()).append(session_id, role, content)


def scope(session_id, actor):
    with ChatRepository() as repository:
        record = ChatValidator(repository).validate_read(session_id, actor)
        return record.apartment, [
            str(item.id)
            for item in repository.list(actor["id"])
            if item.apartment == record.apartment
        ]


def archive(session_id, actor, *, restore=False):
    apartment, _ = scope(session_id, actor)
    PortalHistoryRepository(get_database()).archive(actor["id"], apartment, restore)
    return {"archived": not restore}


def encode_cursor(position):
    return "v1." + base64.urlsafe_b64encode(
        json.dumps(
            [position[0].isoformat(), position[1]], separators=(",", ":")
        ).encode()
    ).decode().rstrip("=")


def decode_cursor(value):
    try:
        stamp, key = json.loads(
            base64.urlsafe_b64decode(value[3:] + "=" * (-len(value[3:]) % 4))
        )
        timestamp = datetime.fromisoformat(stamp)
        if not timestamp.tzinfo or not isinstance(key, str) or not 1 <= len(key) <= 200:
            raise ValueError
        return timestamp.astimezone(timezone.utc), key
    except (TypeError, ValueError, UnicodeError, json.JSONDecodeError):
        raise error(
            422, "INVALID_HISTORY_CURSOR", "O cursor de histórico é inválido."
        ) from None


def position(row):
    return datetime.fromisoformat(row["created_at"]), row["id"]


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
                    "executar_reserva_validada",
                    "executar_convivencia_validada",
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
                                "_result": {
                                    key: response.response[key]
                                    for key in ("status", "code")
                                    if key in response.response
                                },
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
    session_id,
    actor,
    service,
    *,
    limit=50,
    before=None,
    include_pending=False,
    include_archived=False,
):
    apartment, ids = await asyncio.to_thread(scope, session_id, actor)
    repository = PortalHistoryRepository(get_database())
    cursor = decode_cursor(before) if before and before.startswith("v1.") else None
    if before and cursor is None:
        cursor = await asyncio.to_thread(repository.cursor_for_message, before, ids)
        if cursor is None:
            raise error(
                422,
                "INVALID_HISTORY_CURSOR",
                "O cursor não pertence ao histórico desta unidade.",
            )
    hidden = await asyncio.to_thread(repository.hidden_before, actor["id"], apartment)
    cutoff = hidden if not include_archived else None
    rows = await asyncio.to_thread(repository.messages, ids, limit + 1, cursor, cutoff)
    earliest = await asyncio.to_thread(repository.earliest, ids)
    ledger_floor = None
    ledger_more = False
    if include_pending:
        decisions = await asyncio.to_thread(
            repository.decisions, ids, actor["id"], apartment, limit + 1, cursor, cutoff
        )
        if len(decisions) == limit + 1:
            ledger_floor = position(decisions[-1])
            ledger_more = True
        for decision in decisions:
            text = receipt_text(decision.pop("result"))
            if not text:
                continue
            decision.update(role="assistant", content=text)
            later = await asyncio.to_thread(
                repository.next_decision, decision, ids, actor["id"], apartment
            )
            if not await asyncio.to_thread(
                repository.has_normal_receipt, decision, later
            ):
                rows.append(decision)
    adk_repository = AdkHistoryRepository(service)
    adk_rows, adk_more, floor = await adk_repository.events(
        ids, actor["id"], 4 * (limit + 1), cursor
    )
    receipts = []
    for sid, event in adk_rows:
        for row in public_events([event]):
            row["session_id"] = sid
            if cursor and position(row) >= cursor:
                continue
            if cutoff and position(row)[0] <= cutoff:
                continue
            if row.get("_receipt_status") in ("reserved", "cancelled"):
                receipts.append(row)
            elif sid not in earliest or position(row)[0] < earliest[sid]:
                rows.append(row)
    receipts.sort(key=position)
    for index, receipt in enumerate(receipts):
        later = next(
            (
                position(row)[0]
                for row in receipts[index + 1 :]
                if row["session_id"] == receipt["session_id"]
            ),
            None,
        )
        if service is not None and hasattr(service, "db_engine"):
            later = await adk_repository.next_receipt(receipt, actor["id"])
        if await asyncio.to_thread(repository.has_normal_receipt, receipt, later):
            continue
        if include_pending and await asyncio.to_thread(
            repository.has_ledger_reservation, receipt, actor["id"], apartment
        ):
            continue
        rows.append(receipt)
    # If a bounded ADK window contains mostly internal events, stop at its
    # watermark and return a cursor even for an empty page. Older public text
    # remains reachable without loading the remaining events in this request.
    floors = [item for item in (floor, ledger_floor) if item is not None]
    floor = max(floors) if floors else None
    if floor:
        rows = [row for row in rows if position(row) >= floor]
    rows.sort(key=position)
    page = rows[-limit:]
    more = len(rows) > limit or adk_more or ledger_more
    next_position = position(page[0]) if len(rows) > limit else floor
    if more and next_position is None and page:
        next_position = position(page[0])
    pending = []
    if include_pending:
        from services.agent.models.session_identity import SessionIdentity
        from services.agent.runtime.resident_actions import ProductActions

        for sid in ids:
            items = await asyncio.to_thread(
                ProductActions(
                    SessionIdentity.from_authenticated_actor(sid, actor)
                ).pending
            )
            pending.extend(
                {**item, "session_id": sid, "sourceSessionId": sid} for item in items
            )
    await asyncio.to_thread(scope, session_id, actor)
    return {
        "messages": [
            {
                **{
                    k: v
                    for k, v in row.items()
                    if not k.startswith("_") and k != "session_id"
                },
                "sourceSessionId": row["session_id"],
            }
            for row in page
        ],
        "next_cursor": encode_cursor(next_position) if more and next_position else None,
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
