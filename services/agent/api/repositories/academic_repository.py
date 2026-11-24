"""Persistência acadêmica ORM, com transação por operação e recibos atômicos."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    delete,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import registry
from sqlalchemy.pool import NullPool

from ..models import (
    AcademicConfirmation,
    AcademicConfirmationOutcome,
    AcademicRestoreSnapshot,
    AcademicSeed,
    AcademicSession,
    Apartment,
    Area,
    Base,
    Receipt,
    Reservation,
    Visitor,
)
from ..validators.domain_values import iso_day, slug, visible_name
from .unit_of_work import UnitOfWork

CORE = (AcademicSeed, Apartment, Area, Reservation, Visitor, Receipt)
API = (AcademicSession, AcademicConfirmation, AcademicConfirmationOutcome)


class AcademicRepository:
    is_postgres = False

    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()

    def _engine(self, *, create=False):
        def connect():
            raw = sqlite3.connect(
                self.path.as_uri() + ("?mode=rwc" if create else "?mode=rw"),
                uri=True,
                timeout=10,
            )
            raw.execute("PRAGMA foreign_keys=ON")
            return raw

        return create_engine("sqlite://", creator=connect, poolclass=NullPool)

    @contextmanager
    def _transaction(self, *, write=False, create=False, check_seed=True):
        engine = self._engine(create=create)
        try:
            with engine.connect() as connection:
                if not self.is_postgres and write:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                work = UnitOfWork(connection)
                try:
                    if check_seed and work.orm.get(AcademicSeed, 1) is None:
                        raise RuntimeError("Banco acadêmico não inicializado.")
                    yield work
                    work.orm.flush()
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
                finally:
                    work.orm.close()
        finally:
            engine.dispose()

    @contextmanager
    def connection(self, *, write=False):
        with self._transaction(write=write) as work:
            yield work

    def transaction(self, *, write=False):
        return self.connection(write=write)

    @staticmethod
    def _record(model):
        if model is None:
            return None
        return {
            column.key: getattr(model, column.key) for column in model.__table__.columns
        }

    def initialize(self, fixtures: Path | str) -> bool:
        fixtures = Path(fixtures)

        def rows(name):
            return json.loads((fixtures / (name + ".json")).read_text(encoding="utf-8"))

        with self._transaction(write=True, create=True, check_seed=False) as work:
            if self.is_postgres:
                work.orm.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": 64021901}
                )
            tables = set(inspect(work.connection).get_table_names())
            if "academic_seed" in tables and work.orm.get(AcademicSeed, 1):
                return False
            if tables:
                raise ValueError("Não inicializar sobre banco existente não acadêmico.")
            Base.metadata.create_all(
                work.connection,
                tables=[Base.metadata.tables[model.__tablename__] for model in CORE],
            )
            work.orm.add_all(
                Apartment(number=row["numero"]) for row in rows("apartamentos")
            )
            work.orm.flush()
            work.orm.add_all(
                Area(
                    id=row["id"],
                    name=row["nome"],
                    fee_cents=int(Decimal(str(row["taxa"])) * 100),
                )
                for row in rows("areas")
            )
            work.orm.flush()
            work.orm.add_all(
                Reservation(
                    code=row["codigo"],
                    apartment=row["apartamento"],
                    area=row["area"],
                    day=iso_day(row["data"]),
                )
                for row in rows("reservas")
            )
            work.orm.add_all(
                Visitor(
                    apartment=row["apartamento"],
                    name=visible_name(row["nome"]),
                    day=iso_day(row["data"]),
                )
                for row in rows("visitantes")
            )
            work.orm.add(AcademicSeed(version=1))
            return True

    def prepare_api_tables(self):
        with self.connection(write=True) as work:
            Base.metadata.create_all(
                work.connection,
                tables=[Base.metadata.tables[model.__tablename__] for model in API],
            )

    def restore(self, fixtures: Path | str):
        fixtures = Path(fixtures)
        reservations = [
            (r["codigo"], r["apartamento"], r["area"], iso_day(r["data"]))
            for r in json.loads(
                (fixtures / "reservas.json").read_text(encoding="utf-8")
            )
        ]
        visitors = [
            (r["apartamento"], visible_name(r["nome"]), iso_day(r["data"]))
            for r in json.loads(
                (fixtures / "visitantes.json").read_text(encoding="utf-8")
            )
        ]
        with self.connection(write=True) as work:
            if self.is_postgres:
                work.orm.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": 64021901}
                )
            tables = set(inspect(work.connection).get_table_names())
            known = {
                "academic_seed",
                "apartments",
                "areas",
                "reservations",
                "visitors",
                "receipts",
                "academic_sessions",
                "academic_confirmations",
                "academic_confirmation_outcomes",
                "academic_policy_revisions",
                "academic_policy_head",
                "academic_reservation_policy",
                "academic_restore_snapshots",
                "sessions",
                "events",
                "app_states",
                "user_states",
                "adk_internal_metadata",
                "sqlite_sequence",
            }
            if tables - known:
                raise ValueError(
                    "Restauração recusada: banco contém tabelas não acadêmicas."
                )
            changed = (
                "reservations",
                "visitors",
                "academic_sessions",
                "academic_confirmations",
                "academic_confirmation_outcomes",
                "academic_reservation_policy",
            )
            if self.is_postgres:
                work.connection.exec_driver_sql(
                    "LOCK TABLE "
                    + ",".join(name for name in changed if name in tables)
                    + " IN ACCESS EXCLUSIVE MODE"
                )
            # Optional legacy policy data is reflected only after the allowlist check.
            mapped: dict[str, type] = {
                model.__tablename__: model for model in (*CORE, *API)
            }
            mapping = registry()
            if "academic_reservation_policy" in tables:
                table = Table(
                    "academic_reservation_policy",
                    MetaData(),
                    autoload_with=work.connection,
                )
                entity = type("LegacyReservationPolicy", (), {})
                mapping.map_imperatively(
                    entity,
                    table,
                    primary_key=list(table.primary_key.columns) or list(table.columns),
                )
                mapped["academic_reservation_policy"] = entity
            snapshot = {
                name: [
                    self._record(row)
                    if hasattr(row, "__table__")
                    else {
                        c.key: getattr(row, c.key) for c in inspect(type(row)).columns
                    }
                    for row in work.orm.scalars(select(mapped[name]))
                ]
                for name in changed
                if name in tables
            }
            Base.metadata.tables["academic_restore_snapshots"].create(
                work.connection, checkfirst=True
            )
            snapshot_id = uuid4().hex
            work.orm.add(
                AcademicRestoreSnapshot(
                    id=snapshot_id,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    payload=json.dumps(snapshot, ensure_ascii=False),
                )
            )
            work.orm.flush()
            for name in (
                "academic_confirmation_outcomes",
                "academic_confirmations",
                "academic_sessions",
                "academic_reservation_policy",
            ):
                if name in tables:
                    work.orm.execute(delete(mapped[name]))
            work.orm.execute(update(Reservation).values(active=0))
            for code, apartment, area, day in reservations:
                prior = work.orm.get(Reservation, code)
                if prior and (prior.apartment, prior.area, prior.day) != (
                    apartment,
                    area,
                    day,
                ):
                    raise ValueError(
                        "Código inicial já pertence a outra reserva; restauração cancelada."
                    )
                if prior:
                    prior.active = 1
                else:
                    work.orm.add(
                        Reservation(code=code, apartment=apartment, area=area, day=day)
                    )
            work.orm.execute(delete(Visitor))
            work.orm.add_all(
                Visitor(apartment=apartment, name=name, day=day)
                for apartment, name, day in visitors
            )
        return snapshot_id

    def has_apartment(self, apartment):
        with self.connection() as work:
            return work.orm.get(Apartment, apartment) is not None

    def reservations(self, apartment):
        with self.connection() as work:
            rows = work.orm.scalars(
                select(Reservation)
                .where(Reservation.apartment == apartment, Reservation.active == 1)
                .order_by(Reservation.day, Reservation.area, Reservation.code)
            )
            return [
                {"codigo": row.code, "area": row.area, "data": row.day} for row in rows
            ]

    def visitors(self, apartment):
        with self.connection() as work:
            rows = work.orm.scalars(
                select(Visitor)
                .where(Visitor.apartment == apartment)
                .order_by(Visitor.day, Visitor.name, Visitor.id)
            )
            return [{"nome": row.name, "data": row.day} for row in rows]

    def tools(self, apartment):
        from .bound_domain_repository import BoundDomain

        if not self.has_apartment(apartment):
            raise ValueError("Apartamento não cadastrado.")
        return BoundDomain(self, apartment)

    @staticmethod
    def _area(work, value):
        target = slug(value)
        if not target:
            return None
        for row in work.orm.scalars(select(Area)):
            if target in (row.id, slug(row.name)):
                return AcademicRepository._record(row)
        return None

    @staticmethod
    def _available(work, area, day):
        return (
            work.orm.scalar(
                select(Reservation.code)
                .where(
                    Reservation.area == area,
                    Reservation.day == day,
                    Reservation.active == 1,
                )
                .limit(1)
            )
            is None
        )

    @staticmethod
    def _once(work, apartment, action, details, operation_id, effect):
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 256:
            raise ValueError("Identificador confiável da operação é obrigatório.")
        if not work.in_transaction:
            raise RuntimeError("A operação exige uma transação de escrita.")
        payload = json.dumps(
            details, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        prior = work.orm.get(Receipt, operation_id)
        if prior:
            if (prior.apartment, prior.action, prior.payload) != (
                apartment,
                action,
                payload,
            ):
                return {"status": "operation_conflict"}
            return json.loads(prior.result)
        result = effect()
        work.orm.add(
            Receipt(
                operation_id=operation_id,
                apartment=apartment,
                action=action,
                payload=payload,
                result=json.dumps(result, ensure_ascii=False),
            )
        )
        work.orm.flush()
        return result

    @staticmethod
    def _insert_reservation(work, apartment, area, day):
        for _ in range(3):
            code = "RSV-" + uuid4().hex.upper()
            try:
                with work.orm.begin_nested():
                    work.orm.add(
                        Reservation(code=code, apartment=apartment, area=area, day=day)
                    )
                    work.orm.flush()
                return {"status": "reserved", "codigo": code, "area": area, "data": day}
            except IntegrityError:
                if not AcademicRepository._available(work, area, day):
                    return {"status": "occupied"}
        raise RuntimeError("Não foi possível gerar um código único de reserva.")

    def cancel_reservation(self, work, apartment, area, day):
        result = work.orm.execute(
            update(Reservation)
            .where(
                Reservation.apartment == apartment,
                Reservation.area == area,
                Reservation.day == day,
                Reservation.active == 1,
            )
            .values(active=0)
        )
        return {"status": "cancelled" if result.rowcount else "not_found"}

    def apply_confirmed(self, apartment, action, details, *, operation_id):
        with self.connection(write=True) as work:
            return self.execute_confirmed(
                work, apartment, action, details, operation_id=operation_id
            )

    def execute_confirmed(self, work, apartment, action, details, *, operation_id):
        if work.orm.get(Apartment, apartment) is None:
            return {"status": "unknown_apartment"}
        if action == "reservar_area":
            area = self._area(work, details.get("area"))
            if area is None or area["fee_cents"] <= 0:
                return {"status": "invalid_action"}
            day = iso_day(details.get("data"))
            if details.get("taxa") != area["fee_cents"] / 100:
                return {"status": "invalid_action"}
            payload = {"area": area["id"], "data": day, "taxa": area["fee_cents"] / 100}
            return self._once(
                work,
                apartment,
                "paid_reservation",
                payload,
                operation_id,
                lambda: self._insert_reservation(work, apartment, area["id"], day),
            )
        if action == "autorizar_visitante":
            name, day = visible_name(details.get("nome")), iso_day(details.get("data"))
            payload = {"nome": name, "data": day}

            def insert_visitor():
                work.orm.add(Visitor(apartment=apartment, name=name, day=day))
                work.orm.flush()
                return {"status": "authorized", **payload}

            return self._once(
                work, apartment, action, payload, operation_id, insert_visitor
            )
        return {"status": "invalid_action"}

    def apartment_for(self, work, session_id):
        row = work.orm.get(AcademicSession, session_id)
        return row.apartment if row else None

    def confirmation(self, work, confirmation_id):
        return self._record(work.orm.get(AcademicConfirmation, confirmation_id))

    def processing(self, work, session_id):
        return [
            self._record(row)
            for row in work.orm.scalars(
                select(AcademicConfirmation).where(
                    AcademicConfirmation.session_id == session_id,
                    AcademicConfirmation.status == "processing",
                )
            )
        ]

    def binding(self, work, confirmation_id, session_id, apartment):
        row = work.orm.get(AcademicConfirmationOutcome, confirmation_id)
        return (
            self._record(row)
            if row and (row.session_id, row.apartment) == (session_id, apartment)
            else None
        )

    def receipt(self, work, operation_id):
        return self._record(work.orm.get(Receipt, operation_id))

    def complete(
        self,
        work,
        confirmation_id,
        session_id,
        result,
        *,
        apartment=None,
        processing_only=False,
    ):
        criteria = [
            AcademicConfirmationOutcome.confirmation_id == confirmation_id,
            AcademicConfirmationOutcome.session_id == session_id,
        ]
        if apartment is not None:
            criteria.append(AcademicConfirmationOutcome.apartment == apartment)
        work.orm.execute(
            update(AcademicConfirmationOutcome)
            .where(*criteria)
            .values(result=json.dumps(result, ensure_ascii=False))
        )
        conditions = [
            AcademicConfirmation.id == confirmation_id,
            AcademicConfirmation.session_id == session_id,
        ]
        if processing_only:
            conditions.append(AcademicConfirmation.status == "processing")
        work.orm.execute(
            update(AcademicConfirmation).where(*conditions).values(status="consumed")
        )

    def pending(self, work, session_id):
        return [
            self._record(row)
            for row in work.orm.scalars(
                select(AcademicConfirmation)
                .where(
                    AcademicConfirmation.session_id == session_id,
                    AcademicConfirmation.status == "pending",
                )
                .order_by(AcademicConfirmation.id)
            )
        ]

    def store_proposal(
        self, work, confirmation_id, session_id, invocation, payload, operation_id
    ):
        # Turn ownership serializes a session; the primary keys arbitrate replay.
        if work.orm.get(AcademicConfirmation, confirmation_id) is None:
            work.orm.add(
                AcademicConfirmation(
                    id=confirmation_id,
                    session_id=session_id,
                    invocation=invocation,
                    payload=json.dumps(payload, ensure_ascii=False),
                )
            )
            work.orm.flush()
        if work.orm.get(AcademicConfirmationOutcome, confirmation_id) is None:
            work.orm.add(
                AcademicConfirmationOutcome(
                    confirmation_id=confirmation_id,
                    session_id=session_id,
                    apartment=self.apartment_for(work, session_id),
                    operation_id=operation_id,
                    action=payload["acao"],
                    payload=json.dumps(
                        payload["detalhes"],
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            )
            work.orm.flush()

    def insert_session(self, work, session_id, apartment):
        work.orm.add(AcademicSession(id=session_id, apartment=apartment))
        work.orm.flush()

    def unresolved(self, work, session_id):
        return work.orm.scalar(
            select(AcademicConfirmation.id)
            .where(
                AcademicConfirmation.session_id == session_id,
                AcademicConfirmation.status.in_(("pending", "processing")),
            )
            .limit(1)
        )

    def claim(self, work, confirmation_id, session_id):
        result = work.orm.execute(
            update(AcademicConfirmation)
            .where(
                AcademicConfirmation.id == confirmation_id,
                AcademicConfirmation.session_id == session_id,
                AcademicConfirmation.status == "pending",
            )
            .values(status="processing")
            .returning(AcademicConfirmation.invocation, AcademicConfirmation.payload)
        )
        row = result.mappings().first()
        return dict(row) if row else None
