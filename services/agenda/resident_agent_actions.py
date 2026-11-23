"""Domain-owned staging commands for the authenticated resident coordinator.

Not routes or model tools. Caller must authorize resident/unit on every action,
validate required external confirmation, and open a transaction containing both
the effect and its durable idempotency receipt. No implicit commit or retry.
Only exact catalog IDs are accepted. No academic fixtures/databases are used.
"""

from datetime import date
import re
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from services.agenda.models.reservation import Reservation
from services.common_areas.models.area import Area


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def _identity(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    for key in ("apartment", "resident_id", "area"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError("trusted identity and catalog ID are required")
    return (
        payload["apartment"],
        payload["resident_id"],
        payload["area"],
        _day(payload.get("date")),
    )


def _transaction(session):
    if not session.in_transaction():
        raise RuntimeError("Caller must open the effect/receipt transaction")


def reserve(session, payload):
    """Reserve one active area/day; fee must match the approved snapshot exactly."""
    _transaction(session)
    try:
        apartment, resident, area_id, day = _identity(payload)
        expected = payload.get("fee_cents")
        if type(expected) is not int or not 0 <= expected <= 100000000:
            raise ValueError("fee_cents must be integer cents")
    except (ValueError, TypeError):
        return {"status": "invalid_details"}
    # Lock the catalog tariff until the caller commits effect + receipt.
    area = session.execute(
        select(Area).where(Area.id == area_id).with_for_update()
    ).scalar_one_or_none()
    if area is None:
        return {"status": "unknown_area"}
    if area.fee_cents != expected:
        return {"status": "fee_changed"}
    code = "RSV-" + uuid4().hex.upper()
    statement = (
        insert(Reservation)
        .values(
            code=code,
            apartment=apartment,
            resident_id=resident,
            area_id=area_id,
            date=day,
            fee_cents=expected,
            status="active",
        )
        .on_conflict_do_nothing(
            index_elements=[Reservation.area_id, Reservation.date],
            index_where=Reservation.status == "active",
        )
        .returning(Reservation.code)
    )
    created = session.execute(statement).scalar_one_or_none()
    if created is None:
        return {"status": "occupied"}
    return {
        "status": "reserved",
        "code": created,
        "area": area_id,
        "date": day.isoformat(),
        "fee_cents": expected,
    }


def cancel(session, payload):
    """Cancel only the authenticated owner's active reservation; never delete."""
    _transaction(session)
    try:
        apartment, resident, area_id, day = _identity(payload)
    except (ValueError, TypeError):
        return {"status": "invalid_details"}
    statement = (
        update(Reservation)
        .where(
            Reservation.apartment == apartment,
            Reservation.resident_id == resident,
            Reservation.area_id == area_id,
            Reservation.date == day,
            Reservation.status == "active",
        )
        .values(status="cancelled")
        .returning(Reservation.code)
    )
    cancelled = session.execute(statement).scalar_one_or_none()
    return {"status": "cancelled" if cancelled is not None else "not_found"}
