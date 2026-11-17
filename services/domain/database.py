"""Persistência, migrações e carga inicial dos dados do condomínio."""
from datetime import date, time
from decimal import Decimal
import json
import os
from pathlib import Path

import psycopg

from psycopg.rows import dict_row

from services.domain.schemas import ReservationHours, VisitHours
from services.resident_seed import seed_resident_id


LATEST_MIGRATION = 3


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3, row_factory=dict_row)


def _read_json(source, name):
    return json.loads((source / name).read_text(encoding="utf-8"), parse_float=Decimal)


def _seed(connection, source):
    apartments = {
        row["numero"]: "demo-resident" if row["numero"] == "101" else None
        for row in _read_json(source, "apartamentos.json")
    }
    areas = {
        row["id"]: (row["nome"], int(Decimal(row["taxa"]) * 100))
        for row in _read_json(source, "areas.json")
    }

    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO apartments (number, resident_id) VALUES (%s, %s)",
            list(apartments.items()),
        )
        cursor.executemany(
            "INSERT INTO areas VALUES (%s, %s, %s)",
            [(area_id, name, fee) for area_id, (name, fee) in areas.items()],
        )
        cursor.execute(
            "INSERT INTO regulations (version, content) VALUES (0, %s)",
            ((source / "regulamento.md").read_text(encoding="utf-8"),),
        )
        cursor.executemany(
            """INSERT INTO reservations (code, apartment, resident_id, area_id, date, fee_cents, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'active')""",
            [
                (
                    row["codigo"], row["apartamento"], apartments[row["apartamento"]], row["area"],
                    date.fromisoformat(row["data"]), areas[row["area"]][1],
                )
                for row in _read_json(source, "reservas.json")
            ],
        )
        cursor.executemany(
            "INSERT INTO visits (apartment, resident_id, name, date) VALUES (%s, %s, %s, %s)",
            [
                (row["apartamento"], apartments[row["apartamento"]], row["nome"], date.fromisoformat(row["data"]))
                for row in _read_json(source, "visitantes.json")
            ],
        )


def _import_apartment_names(connection, source):
    migration = Path(__file__).with_name("migrations") / "002_apartment_source_names.sql"
    connection.execute(migration.read_text(encoding="utf-8"))
    names = [(row["morador"], row["numero"]) for row in _read_json(source, "apartamentos.json")]
    with connection.cursor() as cursor:
        cursor.executemany(
            "UPDATE apartments SET initial_resident_name = %s WHERE number = %s",
            names,
        )


def _fixture_hours(row, model, aliases):
    values = {field: row.get(field, row.get(source_key)) for field, source_key in aliases.items()}
    parsed = model.model_validate(values)
    return tuple(time.fromisoformat(value) if value is not None else None for value in vars(parsed).values())


def _separate_apartment_residents(connection, source):
    source_names = {row["numero"]: row["morador"] for row in _read_json(source, "apartamentos.json")}
    original_units = [
        row["number"]
        for row in connection.execute("SELECT number, initial_resident_name FROM apartments")
        if row["number"] in source_names and source_names[row["number"]] == row["initial_resident_name"]
    ]

    migration = Path(__file__).with_name("migrations") / "003_apartment_residents_and_hours.sql"
    connection.execute(migration.read_text(encoding="utf-8"))

    seed_ids = {number: seed_resident_id(number) for number in original_units}
    with connection.cursor() as cursor:
        cursor.executemany(
            """INSERT INTO apartment_residents (apartment_id, resident_id)
               SELECT id, %s FROM apartments WHERE number = %s ON CONFLICT DO NOTHING""",
            [(resident_id, number) for number, resident_id in seed_ids.items()],
        )

    current_residents = {
        row["number"]: row["resident_id"]
        for row in connection.execute(
            """SELECT p.number, ar.resident_id
               FROM apartments p JOIN apartment_residents ar ON ar.apartment_id = p.id"""
        )
        if seed_ids.get(row["number"]) == row["resident_id"]
    }
    original_fees = {
        row["id"]: int(Decimal(row["taxa"]) * 100) for row in _read_json(source, "areas.json")
    }
    _backfill_original_reservations(connection, source, current_residents, original_fees)
    _backfill_original_visits(connection, source, current_residents)


def _backfill_original_reservations(connection, source, residents, fees):
    for row in _read_json(source, "reservas.json"):
        start, end = _fixture_hours(row, ReservationHours, {"start_time": "hora_inicio", "end_time": "hora_fim"})
        connection.execute(
            """UPDATE reservations
               SET resident_id = COALESCE(resident_id, %s), start_time = %s, end_time = %s
               WHERE code = %s AND apartment = %s AND area_id = %s AND date = %s AND fee_cents = %s""",
            (
                residents.get(row["apartamento"]), start, end, row["codigo"], row["apartamento"],
                row["area"], date.fromisoformat(row["data"]), fees[row["area"]],
            ),
        )


def _backfill_original_visits(connection, source, residents):
    # The initial seed inserted visits in file order, giving them identity values starting at 1.
    # A later row that happens to share the same name, date and apartment must not be reassigned.
    for visit_id, row in enumerate(_read_json(source, "visitantes.json"), start=1):
        entry, exit = _fixture_hours(row, VisitHours, {"entry_time": "hora_entrada", "exit_time": "hora_saida"})
        connection.execute(
            """UPDATE visits SET resident_id = COALESCE(resident_id, %s), entry_time = %s, exit_time = %s
               WHERE id = %s AND apartment = %s AND name = %s AND date = %s""",
            (
                residents.get(row["apartamento"]), entry, exit, visit_id, row["apartamento"],
                row["nome"], date.fromisoformat(row["data"]),
            ),
        )


def initialize():
    default_source = Path(__file__).resolve().parents[2] / "dados"
    source = Path(os.environ.get("AURORA_DATA_DIR", default_source))
    with connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(640201)")
        connection.execute("CREATE TABLE IF NOT EXISTS domain_migrations (version integer PRIMARY KEY)")
        applied = {row["version"] for row in connection.execute("SELECT version FROM domain_migrations")}
        if 1 not in applied:
            connection.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            _seed(connection, source)
            connection.execute("INSERT INTO domain_migrations VALUES (1)")
        if 2 not in applied:
            _import_apartment_names(connection, source)
            connection.execute("INSERT INTO domain_migrations VALUES (2)")
        if 3 not in applied:
            _separate_apartment_residents(connection, source)
            connection.execute("INSERT INTO domain_migrations VALUES (3)")
