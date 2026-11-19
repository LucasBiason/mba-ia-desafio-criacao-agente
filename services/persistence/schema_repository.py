"""Instalação e migração transacional dos bancos já existentes."""

from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
from secrets import token_hex

from argon2 import PasswordHasher
from sqlalchemy import MetaData, Table, func, inspect, select, text

from services.persistence.base import Base
from services.persistence.database import database
from services.users.models.account import Account
from services.authentication.models.login_session import LoginSession
from services.authentication.models.login_limit import LoginLimit
from services.authentication.models.identity_seed import IdentitySeed
from services.authentication.models.identity_migration import IdentityMigration
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident
from services.apartments.models.domain_migration import DomainMigration
from services.common_areas.models.area import Area
from services.agenda.models.reservation import Reservation
from services.visits.models.visit import Visit
from services.settings.models.regulation import Regulation
from services.agent.models.chat_session import ChatSession


class SchemaRepository:
    identity_tables = [Account.__table__, LoginSession.__table__, LoginLimit.__table__,
                       IdentitySeed.__table__, IdentityMigration.__table__]
    domain_tables = [Apartment.__table__, ApartmentResident.__table__, DomainMigration.__table__,
                     Area.__table__, Reservation.__table__, Visit.__table__, Regulation.__table__,
                     ChatSession.__table__]

    def __init__(self):
        self.source = Path(os.environ.get("AURORA_DATA_DIR", Path(__file__).resolve().parents[2] / "dados"))

    def read(self, name):
        return json.loads((self.source / name).read_text(encoding="utf-8"), parse_float=Decimal)

    @staticmethod
    def initial_id(number):
        return "demo-resident" if number == "101" else f"resident-{number.lower()}"

    def initialize_identity(self):
        with database.transaction() as session:
            session.execute(select(func.pg_advisory_xact_lock(74109142)))
            Base.metadata.create_all(session.connection(), tables=self.identity_tables)
            if session.get(IdentityMigration, 2):
                return
            hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
            apartments = self.read("apartamentos.json")
            if not session.get(IdentitySeed, True):
                for user_id, name, email, variable in [
                    ("demo-super", "Administração auxiliar", "super@aurora.test", "DEMO_SUPER_PASSWORD"),
                    ("demo-admin", "Administração", "admin@aurora.test", "DEMO_ADMIN_PASSWORD"),
                    ("demo-resident", next(row["morador"] for row in apartments if row["numero"] == "101"),
                     "morador@aurora.test", "DEMO_RESIDENT_PASSWORD"),
                ]:
                    password = os.environ.get(variable, "")
                    if not 12 <= len(password) <= 256:
                        raise RuntimeError(f"Credencial local obrigatória ausente ou inválida: {variable}.")
                    session.add(Account(id=user_id, name=name, email=email, role="resident" if user_id == "demo-resident" else "admin",
                                        password_hash=hasher.hash(password), active=True))
                session.add(IdentitySeed(only_row=True))
                session.flush()
            # DDL changes the historical role constraint; data changes use ORM objects.
            session.execute(text("ALTER TABLE accounts DROP CONSTRAINT IF EXISTS accounts_role_check"))
            for account in session.scalars(select(Account)):
                if account.role == "superuser":
                    account.role = "admin"
                if account.id == "demo-super" and account.name == "Superusuário":
                    account.name = "Administração auxiliar"
            session.flush()
            session.execute(text("ALTER TABLE accounts ADD CONSTRAINT accounts_role_check CHECK (role IN ('admin', 'resident'))"))
            for row in apartments:
                user_id = self.initial_id(row["numero"])
                existing = session.get(Account, user_id)
                if existing:
                    if user_id == "demo-resident" and existing.name == "Morador de demonstração":
                        existing.name = row["morador"]
                    continue
                local = f"morador-{row['numero'].lower()}"
                email = f"{local}@aurora.test"
                suffix = 2
                while session.scalar(select(Account.id).where(Account.email == email)):
                    email = f"{local}+{suffix}@aurora.test"
                    suffix += 1
                session.add(Account(id=user_id, name=row["morador"], email=email, role="resident",
                                    active=False, password_hash=hasher.hash(token_hex(32))))
            session.add(IdentityMigration(version=2))

    def initialize_domain(self):
        with database.transaction() as session:
            session.execute(select(func.pg_advisory_xact_lock(640201)))
            inspector = inspect(session.connection())
            existing = inspector.has_table("apartments")
            old_residents = self.upgrade_legacy(session, inspector) if existing else None
            Base.metadata.create_all(session.connection(), tables=self.domain_tables)
            if session.get(DomainMigration, 3):
                return
            if not existing:
                self.seed_domain(session)
            elif old_residents is not None:
                self.backfill_legacy(session, old_residents)
            for version in (1, 2, 3):
                if not session.get(DomainMigration, version):
                    session.add(DomainMigration(version=version))

    def upgrade_legacy(self, session, inspector):
        columns = {column["name"] for column in inspector.get_columns("apartments")}
        if "id" in columns:
            return None
        legacy = Table("apartments", MetaData(), autoload_with=session.connection())
        rows = session.execute(select(legacy)).mappings().all()
        session.execute(text("ALTER TABLE apartments ADD COLUMN id bigint GENERATED ALWAYS AS IDENTITY UNIQUE"))
        ApartmentResident.__table__.create(session.connection(), checkfirst=True)
        source = {row["numero"]: row["morador"] for row in self.read("apartamentos.json")}
        residents = {}
        for row in rows:
            resident_id = row.get("resident_id")
            name_matches = row.get("initial_resident_name") in (None, source.get(row["number"]))
            if resident_id is None and row["number"] in source and name_matches:
                resident_id = self.initial_id(row["number"])
            if resident_id is not None:
                apartment = session.get(Apartment, row["number"])
                session.add(ApartmentResident(apartment_id=apartment.id, resident_id=resident_id))
                if row["number"] in source and name_matches and resident_id == self.initial_id(row["number"]):
                    residents[row["number"]] = resident_id
        for column in ("resident_id", "initial_resident_name"):
            if column in columns:
                session.execute(text(f"ALTER TABLE apartments DROP COLUMN {column}"))
        for table, names in [
            ("reservations", ("start_time", "end_time")), ("visits", ("entry_time", "exit_time")),
        ]:
            for column in names:
                session.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} time(0)"))
        checks = {
            "reservations": ("reservation_hours_valid", "(start_time IS NULL AND end_time IS NULL) OR (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time)"),
            "visits": ("visit_hours_valid", "exit_time IS NULL OR (entry_time IS NOT NULL AND entry_time < exit_time)"),
        }
        for table, (name, condition) in checks.items():
            session.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition})"))
        session.flush()
        return residents

    def seed_domain(self, session):
        for row in self.read("apartamentos.json"):
            apartment = Apartment(number=row["numero"])
            session.add(apartment)
            session.flush()
            session.add(ApartmentResident(apartment_id=apartment.id, resident_id=self.initial_id(apartment.number)))
        areas = {}
        for row in self.read("areas.json"):
            area = Area(id=row["id"], name=row["nome"], fee_cents=int(Decimal(row["taxa"]) * 100))
            areas[area.id] = area
            session.add(area)
        session.flush()
        for row in self.read("reservas.json"):
            session.add(Reservation(code=row["codigo"], apartment=row["apartamento"],
                                    resident_id=self.initial_id(row["apartamento"]), area_id=row["area"],
                                    date=date.fromisoformat(row["data"]), fee_cents=areas[row["area"]].fee_cents,
                                    status="active"))
        for row in self.read("visitantes.json"):
            session.add(Visit(apartment=row["apartamento"], resident_id=self.initial_id(row["apartamento"]),
                              name=row["nome"], date=date.fromisoformat(row["data"])))
        session.add(Regulation(version=0, content=(self.source / "regulamento.md").read_text(encoding="utf-8")))

    def backfill_legacy(self, session, residents):
        fees = {row["id"]: int(Decimal(row["taxa"]) * 100) for row in self.read("areas.json")}
        for row in self.read("reservas.json"):
            record = session.get(Reservation, row["codigo"])
            if (record and record.resident_id is None and record.apartment == row["apartamento"]
                    and record.area_id == row["area"] and record.date == date.fromisoformat(row["data"])
                    and record.fee_cents == fees[row["area"]]):
                record.resident_id = residents.get(record.apartment)
        for visit_id, row in enumerate(self.read("visitantes.json"), 1):
            record = session.get(Visit, visit_id)
            if (record and record.resident_id is None and record.apartment == row["apartamento"]
                    and record.name == row["nome"] and record.date == date.fromisoformat(row["data"])):
                record.resident_id = residents.get(record.apartment)
