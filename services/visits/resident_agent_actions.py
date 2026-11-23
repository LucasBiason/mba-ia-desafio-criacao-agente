"""Domain-owned visitor authorization for staging resident coordinator.

Caller authorizes the current resident/unit and external confirmation. This
function uses the caller's transaction; the receipt must commit with this effect.
No route, implicit commit, academic data access or physical gate integration.
"""

from datetime import date
import re

from sqlalchemy import insert
from services.visits.models.visit import Visit


def authorize_visit(session, payload):
    """Insert an owner-bound visitor after the coordinator approves access."""
    if not session.in_transaction():
        raise RuntimeError("Caller must open the effect/receipt transaction")
    try:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        for key in ("apartment", "resident_id"):
            value = payload.get(key)
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
            ):
                raise ValueError("trusted identity required")
        raw = payload.get("name")
        if (
            not isinstance(raw, str)
            or not 1 <= len(raw.strip()) <= 160
            or any(not c.isprintable() for c in raw)
        ):
            raise ValueError("name requires 1 to 160 visible characters")
        name = " ".join(raw.split())
        value = payload.get("date")
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
        ):
            raise ValueError("date must be YYYY-MM-DD")
        day = date.fromisoformat(value)
    except (ValueError, TypeError):
        return {"status": "invalid_details"}
    visitor_id = session.execute(
        insert(Visit)
        .values(
            apartment=payload["apartment"],
            resident_id=payload["resident_id"],
            name=name,
            date=day,
        )
        .returning(Visit.id)
    ).scalar_one()
    return {
        "status": "authorized",
        "id": visitor_id,
        "name": name,
        "date": day.isoformat(),
    }
