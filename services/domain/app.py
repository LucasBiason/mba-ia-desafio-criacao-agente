"""API administrativa e de leitura dos moradores do Residencial Aurora."""
from contextlib import asynccontextmanager
from datetime import date, time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Path, Query, Response
from fastapi.responses import JSONResponse
import psycopg
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from pydantic import ValidationError

from services.common import authenticated_user, error, fetch_user, internal_request, required_secret
from services.domain.database import LATEST_MIGRATION, connect, initialize
from services.domain.schemas import (
    ApartmentInput, ApartmentNumber, ApartmentPatch, AreaId, AreaInput, AreaPatch, MessageInput,
    RegulationInput, ReservationHours, SessionInput, VisitHours,
)


APARTMENT_VIEW = """SELECT p.id, p.number, ar.resident_id FROM apartments p
                    LEFT JOIN apartment_residents ar ON ar.apartment_id = p.id"""
RESERVATION_FIELDS = """r.code, r.apartment, r.area_id, a.name AS area_name, r.date, r.fee_cents, r.status,
                        to_char(r.start_time, 'HH24:MI') AS start_time, to_char(r.end_time, 'HH24:MI') AS end_time"""
VISIT_FIELDS = """v.id, v.apartment, v.name, v.date,
                  to_char(v.entry_time, 'HH24:MI') AS entry_time, to_char(v.exit_time, 'HH24:MI') AS exit_time"""


def _clock(value):
    return time.fromisoformat(value) if value is not None else None


def admin(user=Depends(authenticated_user)):
    if user["role"] not in {"admin", "superuser"}:
        raise error(403, "FORBIDDEN", "Seu perfil não pode gerenciar cadastros.")
    return user


def resident(user=Depends(authenticated_user)):
    if user["role"] != "resident":
        raise error(403, "FORBIDDEN", "Esta operação é exclusiva do morador.")
    return user


def _resident_account(resident_id):
    if resident_id is not None:
        account = fetch_user(resident_id)
        if account["role"] != "resident":
            raise error(422, "INVALID_RESIDENT", "Selecione uma conta de morador.")


def _apartment(connection, number):
    row = connection.execute(
        f"{APARTMENT_VIEW} WHERE p.number = %s",
        (number,),
    ).fetchone()
    if row is None:
        raise error(404, "APARTMENT_NOT_FOUND", "Apartamento não encontrado.")
    return row


def _set_apartment_resident(connection, apartment_id, resident_id):
    if resident_id is None:
        connection.execute("DELETE FROM apartment_residents WHERE apartment_id = %s", (apartment_id,))
        return
    connection.execute(
        """INSERT INTO apartment_residents (apartment_id, resident_id) VALUES (%s, %s)
           ON CONFLICT (apartment_id) DO UPDATE SET resident_id = EXCLUDED.resident_id""",
        (apartment_id, resident_id),
    )


def _require_unit(connection, number, resident_id):
    if connection.execute(
        """SELECT 1 FROM apartments p
           JOIN apartment_residents ar ON ar.apartment_id = p.id
           WHERE p.number = %s AND ar.resident_id = %s""",
        (number, resident_id),
    ).fetchone() is None:
        raise error(403, "APARTMENT_FORBIDDEN", "O apartamento não está vinculado à sua conta.")


def _area(connection, area_id):
    row = connection.execute("SELECT id, name, fee_cents FROM areas WHERE id = %s", (area_id,)).fetchone()
    if row is None:
        raise error(404, "AREA_NOT_FOUND", "Área não encontrada.")
    return row


def _current_regulation(connection):
    return connection.execute("SELECT * FROM regulations ORDER BY version DESC LIMIT 1").fetchone()


@asynccontextmanager
async def lifespan(_app):
    required_secret("AURORA_INTERNAL_TOKEN")
    initialize()
    yield


app = FastAPI(title="Residencial Aurora · Condomínio", lifespan=lifespan)


@app.exception_handler(psycopg.OperationalError)
async def database_unavailable(_request, _exc):
    detail = {"code": "DATABASE_UNAVAILABLE", "message": "A base do condomínio está indisponível."}
    return JSONResponse(status_code=503, content={"detail": detail})


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health():
    try:
        with connect() as connection:
            initialized = connection.execute(
                "SELECT 1 FROM domain_migrations WHERE version = %s", (LATEST_MIGRATION,),
            ).fetchone()
            if initialized is None:
                raise error(503, "DATABASE_UNAVAILABLE", "A base do condomínio está indisponível.")
    except psycopg.Error:
        raise error(503, "DATABASE_UNAVAILABLE", "A base do condomínio está indisponível.") from None
    return {"status": "ready"}


@app.get("/api/admin/apartments")
def list_apartments(_user=Depends(admin)):
    with connect() as connection:
        return connection.execute(
            f"{APARTMENT_VIEW} ORDER BY p.number"
        ).fetchall()


@app.get("/api/admin/apartments/{number}")
def get_apartment(number: ApartmentNumber, _user=Depends(admin)):
    with connect() as connection:
        return _apartment(connection, number.upper())


@app.post("/api/admin/apartments", status_code=201)
def create_apartment(data: ApartmentInput, _user=Depends(admin)):
    _resident_account(data.resident_id)
    try:
        with connect() as connection:
            apartment = connection.execute(
                "INSERT INTO apartments (number) VALUES (%s) RETURNING id, number", (data.number,),
            ).fetchone()
            if data.resident_id is not None:
                _set_apartment_resident(connection, apartment["id"], data.resident_id)
            return {**apartment, "resident_id": data.resident_id}
    except UniqueViolation:
        raise error(409, "APARTMENT_EXISTS", "Já existe um apartamento com esse número.") from None


@app.patch("/api/admin/apartments/{number}")
def update_apartment(number: ApartmentNumber, data: ApartmentPatch, _user=Depends(admin)):
    if "resident_id" in data.model_fields_set:
        _resident_account(data.resident_id)
    number = number.upper()
    try:
        with connect() as connection:
            current = connection.execute(
                "SELECT id FROM apartments WHERE number = %s FOR UPDATE", (number,),
            ).fetchone()
            if current is None:
                raise error(404, "APARTMENT_NOT_FOUND", "Apartamento não encontrado.")
            if data.number is not None and data.number != number:
                connection.execute("UPDATE apartments SET number = %s WHERE id = %s", (data.number, current["id"]))
            if "resident_id" in data.model_fields_set:
                _set_apartment_resident(connection, current["id"], data.resident_id)
            return _apartment(connection, data.number or number)
    except UniqueViolation:
        raise error(409, "APARTMENT_EXISTS", "Já existe um apartamento com esse número.") from None
    except ForeignKeyViolation:
        raise error(409, "APARTMENT_IN_USE", "O número é preservado porque o apartamento tem histórico.") from None


@app.delete("/api/admin/apartments/{number}", status_code=204)
def delete_apartment(number: ApartmentNumber, _user=Depends(admin)):
    try:
        with connect() as connection:
            result = connection.execute("DELETE FROM apartments WHERE number = %s", (number.upper(),))
            if result.rowcount == 0:
                raise error(404, "APARTMENT_NOT_FOUND", "Apartamento não encontrado.")
    except ForeignKeyViolation:
        raise error(409, "APARTMENT_IN_USE", "O apartamento tem histórico e não pode ser excluído.") from None
    return Response(status_code=204)


def _list_areas():
    with connect() as connection:
        return connection.execute("SELECT id, name, fee_cents FROM areas ORDER BY name, id").fetchall()


@app.get("/api/admin/areas")
def list_admin_areas(_user=Depends(admin)):
    return _list_areas()


@app.get("/api/areas")
def list_areas(_user=Depends(authenticated_user)):
    return _list_areas()


@app.get("/api/admin/areas/{area_id}")
def get_area(area_id: AreaId, _user=Depends(admin)):
    with connect() as connection:
        return _area(connection, area_id)


@app.post("/api/admin/areas", status_code=201)
def create_area(data: AreaInput, _user=Depends(admin)):
    try:
        with connect() as connection:
            return connection.execute(
                "INSERT INTO areas VALUES (%s, %s, %s) RETURNING id, name, fee_cents",
                (data.id, data.name, data.fee_cents),
            ).fetchone()
    except UniqueViolation:
        raise error(409, "AREA_EXISTS", "Já existe uma área com esse identificador ou nome.") from None


@app.patch("/api/admin/areas/{area_id}")
def update_area(area_id: AreaId, data: AreaPatch, _user=Depends(admin)):
    try:
        with connect() as connection:
            row = connection.execute(
                """UPDATE areas SET name = COALESCE(%s, name), fee_cents = COALESCE(%s, fee_cents)
                   WHERE id = %s RETURNING id, name, fee_cents""",
                (data.name, data.fee_cents, area_id),
            ).fetchone()
            if row is None:
                raise error(404, "AREA_NOT_FOUND", "Área não encontrada.")
            return row
    except UniqueViolation:
        raise error(409, "AREA_EXISTS", "Já existe uma área com esse nome.") from None


@app.delete("/api/admin/areas/{area_id}", status_code=204)
def delete_area(area_id: AreaId, _user=Depends(admin)):
    try:
        with connect() as connection:
            result = connection.execute("DELETE FROM areas WHERE id = %s", (area_id,))
            if result.rowcount == 0:
                raise error(404, "AREA_NOT_FOUND", "Área não encontrada.")
    except ForeignKeyViolation:
        raise error(409, "AREA_IN_USE", "A área tem reservas no histórico e não pode ser excluída.") from None
    return Response(status_code=204)


@app.get("/api/admin/regulation")
def get_admin_regulation(_user=Depends(admin)):
    with connect() as connection:
        return _current_regulation(connection)


@app.get("/api/resident/regulation")
def get_resident_regulation(_user=Depends(resident)):
    with connect() as connection:
        return _current_regulation(connection)


@app.get("/api/admin/regulation/versions")
def regulation_history(_user=Depends(admin)):
    with connect() as connection:
        return connection.execute("SELECT * FROM regulations ORDER BY version DESC").fetchall()


@app.put("/api/admin/regulation")
def publish_regulation(data: RegulationInput, user=Depends(admin)):
    with connect() as connection:
        connection.execute("LOCK TABLE regulations IN SHARE ROW EXCLUSIVE MODE")
        current = _current_regulation(connection)
        if current["version"] != data.base_version:
            raise error(409, "REGULATION_CHANGED", "A versão vigente mudou. Recarregue o regulamento.")
        if current["content"] == data.content:
            raise error(422, "REGULATION_UNCHANGED", "Altere o conteúdo antes de publicar uma versão.")
        return connection.execute(
            """INSERT INTO regulations (version, content, author_id, author_name)
               VALUES (%s, %s, %s, %s) RETURNING *""",
            (current["version"] + 1, data.content, user["id"], user["name"]),
        ).fetchone()


@app.get("/api/admin/reservations")
def admin_reservations(
    area_id: AreaId | None = None,
    day: Annotated[date | None, Query(alias="date")] = None,
    status: Literal["active", "cancelled"] | None = None,
    _user=Depends(admin),
):
    with connect() as connection:
        return connection.execute(
            f"""SELECT {RESERVATION_FIELDS}, r.resident_id
               FROM reservations r JOIN areas a ON a.id = r.area_id
               WHERE (%(area)s::text IS NULL OR r.area_id = %(area)s)
                 AND (%(day)s::date IS NULL OR r.date = %(day)s)
                 AND (%(status)s::text IS NULL OR r.status = %(status)s)
               ORDER BY r.date, r.code""",
            {"area": area_id, "day": day, "status": status},
        ).fetchall()


@app.get("/api/admin/visits")
def admin_visits(
    apartment: ApartmentNumber | None = None,
    day: Annotated[date | None, Query(alias="date")] = None,
    _user=Depends(admin),
):
    with connect() as connection:
        return connection.execute(
            f"""SELECT {VISIT_FIELDS} FROM visits v
               WHERE (%(unit)s::text IS NULL OR v.apartment = %(unit)s)
                 AND (%(day)s::date IS NULL OR v.date = %(day)s) ORDER BY v.date, v.id""",
            {"unit": apartment.upper() if apartment else None, "day": day},
        ).fetchall()


@app.patch("/api/admin/reservations/{code}/hours")
def update_reservation_hours(code: str, data: ReservationHours, _user=Depends(admin)):
    with connect() as connection:
        row = connection.execute(
            f"""UPDATE reservations AS r SET start_time = %s, end_time = %s
                FROM areas a WHERE r.area_id = a.id AND r.code = %s
                RETURNING {RESERVATION_FIELDS}, r.resident_id""",
            (_clock(data.start_time), _clock(data.end_time), code),
        ).fetchone()
        if row is None:
            raise error(404, "RESERVATION_NOT_FOUND", "Reserva não encontrada.")
        return row


@app.patch("/api/admin/visits/{visit_id}/hours")
def update_visit_hours(
    visit_id: Annotated[int, Path(ge=1, le=2**63 - 1)],
    data: VisitHours,
    _user=Depends(admin),
):
    with connect() as connection:
        current = connection.execute(
            """SELECT entry_time, exit_time FROM visits WHERE id = %s FOR UPDATE""",
            (visit_id,),
        ).fetchone()
        if current is None:
            raise error(404, "VISIT_NOT_FOUND", "Visita não encontrada.")
        values = {field: value.isoformat(timespec="minutes") if value else None for field, value in current.items()}
        values.update(data.model_dump(exclude_unset=True))
        try:
            hours = VisitHours.model_validate(values)
        except ValidationError:
            raise error(422, "INVALID_VISIT_HOURS", "A saída deve ser posterior à entrada.") from None
        return connection.execute(
            f"""UPDATE visits AS v SET entry_time = %s, exit_time = %s WHERE v.id = %s
                RETURNING {VISIT_FIELDS}""",
            (_clock(hours.entry_time), _clock(hours.exit_time), visit_id),
        ).fetchone()


@app.get("/api/resident/apartments")
def resident_apartments(user=Depends(resident)):
    with connect() as connection:
        return connection.execute(
            f"{APARTMENT_VIEW} WHERE ar.resident_id = %s ORDER BY p.number", (user["id"],),
        ).fetchall()


@app.get("/api/resident/reservations")
def resident_reservations(apartment: ApartmentNumber, user=Depends(resident)):
    apartment = apartment.upper()
    with connect() as connection:
        _require_unit(connection, apartment, user["id"])
        return connection.execute(
            f"""SELECT {RESERVATION_FIELDS}
               FROM reservations r JOIN areas a ON a.id = r.area_id JOIN apartments p ON p.number = r.apartment
               JOIN apartment_residents ar ON ar.apartment_id = p.id AND ar.resident_id = r.resident_id
               WHERE r.apartment = %s AND r.resident_id = %s
               ORDER BY r.date, r.code""",
            (apartment, user["id"]),
        ).fetchall()


@app.get("/api/resident/visits")
def resident_visits(apartment: ApartmentNumber, user=Depends(resident)):
    apartment = apartment.upper()
    with connect() as connection:
        _require_unit(connection, apartment, user["id"])
        return connection.execute(
            f"""SELECT {VISIT_FIELDS}
               FROM visits v JOIN apartments p ON p.number = v.apartment
               JOIN apartment_residents ar ON ar.apartment_id = p.id AND ar.resident_id = v.resident_id
               WHERE v.apartment = %s AND v.resident_id = %s
               ORDER BY v.date, v.id""",
            (apartment, user["id"]),
        ).fetchall()


def _get_session(connection, session_id, resident_id):
    row = connection.execute(
        """SELECT s.id, s.apartment, s.created_at FROM chat_sessions s
           JOIN apartments p ON p.number = s.apartment
           JOIN apartment_residents ar ON ar.apartment_id = p.id AND ar.resident_id = s.resident_id
           WHERE s.id = %s AND s.resident_id = %s""",
        (session_id, resident_id),
    ).fetchone()
    if row is None:
        raise error(404, "SESSION_NOT_FOUND", "Sessão não encontrada.")
    return row


@app.post("/api/resident/chat/sessions", status_code=201)
def create_chat_session(data: SessionInput, user=Depends(resident)):
    with connect() as connection:
        row = connection.execute(
            """INSERT INTO chat_sessions (id, apartment, resident_id)
               SELECT %s, p.number, ar.resident_id FROM apartments p
               JOIN apartment_residents ar ON ar.apartment_id = p.id
               WHERE p.number = %s AND ar.resident_id = %s
               RETURNING id, apartment, created_at""",
            (uuid4(), data.apartment, user["id"]),
        ).fetchone()
        if row is None:
            raise error(403, "APARTMENT_FORBIDDEN", "O apartamento não está vinculado à sua conta.")
        return {**row, "status": "awaiting_agent"}


@app.get("/api/resident/chat/sessions")
def list_chat_sessions(user=Depends(resident)):
    with connect() as connection:
        rows = connection.execute(
            """SELECT s.id, s.apartment, s.created_at FROM chat_sessions s
               JOIN apartments p ON p.number = s.apartment
               JOIN apartment_residents ar ON ar.apartment_id = p.id AND ar.resident_id = s.resident_id
               WHERE s.resident_id = %s
               ORDER BY s.created_at DESC, s.id""",
            (user["id"],),
        ).fetchall()
        return [{**row, "status": "awaiting_agent"} for row in rows]


@app.get("/api/resident/chat/sessions/{session_id}")
def get_chat_session(session_id: UUID, user=Depends(resident)):
    with connect() as connection:
        row = _get_session(connection, session_id, user["id"])
        return {**row, "status": "awaiting_agent"}


@app.post("/api/resident/chat/sessions/{session_id}/messages")
def send_chat_message(session_id: UUID, data: MessageInput, user=Depends(resident)):
    with connect() as connection:
        row = _get_session(connection, session_id, user["id"])

    response = internal_request(
        "agent", "POST", "/internal/chat/messages",
        payload={"session_id": str(session_id), "apartment": row["apartment"], "user_id": user["id"],
                 "message": data.message},
    )
    try:
        payload = response.json()
    except ValueError:
        raise error(503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento.") from None
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if response.status_code == 503 and isinstance(detail, dict) and detail.get("code") == "AGENT_NOT_CONFIGURED":
        raise error(503, "AGENT_NOT_CONFIGURED", "A consultoria por agentes ainda será implementada.")
    if not response.is_success:
        raise error(503, "AGENT_UNAVAILABLE", "A consultoria está indisponível no momento.")
    return payload
