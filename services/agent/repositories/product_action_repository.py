"""Resident actions coordinated with their durable confirmation ledger.

Agenda and visits own the effects. Identity, regulation version and confirmation
are checked in code; effects and their receipts share the condo-db transaction.
"""

from datetime import date
import re
import unicodedata

from sqlalchemy import func, select

from microservice_toolkit import error, get_database
from services.agenda.models.reservation import Reservation
from services.agenda.resident_agent_actions import (
    reserve as reserve_effect,
    cancel as cancel_effect,
)
from services.agent.confirmations.ledger import ConfirmationLedger, ConfirmationRecord
from services.agent.models.chat_session import ChatSession
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident
from services.common_areas.models.area import Area
from services.parameters.models.regulation import Regulation
from services.visits.models.visit import Visit
from services.visits.resident_agent_actions import authorize_visit as visit_effect


def read_day(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Use uma data válida no formato AAAA-MM-DD.")
    return date.fromisoformat(value)


def slug(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        return ""
    text = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    )
    return re.sub("[^a-z0-9]+", "-", text).strip("-")


def current_version(session):
    # F06 publishes under the exclusive counterpart of the same xact lock.
    session.execute(select(func.pg_advisory_xact_lock_shared(640202)))
    regulation = session.scalar(
        select(Regulation).order_by(Regulation.version.desc()).limit(1)
    )
    if (
        regulation is None
        or type(regulation.version) is not int
        or regulation.version < 0
        or not isinstance(regulation.content, str)
        or not 1 <= len(regulation.content) <= 200_000
        or not regulation.content.strip()
    ):
        return None
    # Published revisions do not change the fixed authorization/charging rules.
    # Confirmations separately compare this version with their durable proposal.
    return regulation.version


class ProductActionRepository:
    def __init__(self, identity):
        self.identity = identity

    @staticmethod
    def _authorize(session, identity):
        apartment = session.scalar(
            select(ChatSession.apartment)
            .join(Apartment, Apartment.number == ChatSession.apartment)
            .join(ApartmentResident, ApartmentResident.apartment_id == Apartment.id)
            .where(
                ChatSession.id == identity.session_id,
                ChatSession.resident_id == identity.resident_id,
                ApartmentResident.resident_id == identity.resident_id,
            )
            .with_for_update(of=Apartment)
        )
        if apartment is None:
            raise error(404, "SESSION_NOT_FOUND", "Sessão não encontrada.")
        return apartment

    @staticmethod
    def _area(session, area):
        key = slug(area)
        if not key:
            return None
        rows = list(session.scalars(select(Area)))
        exact = [row for row in rows if key in (slug(row.id), slug(row.name))]
        if exact:
            return exact[0] if len(exact) == 1 else None
        # Accept a complete leading name only when the catalog has one match.
        # Never choose an arbitrary area when an abbreviated name is ambiguous.
        matches = [
            row
            for row in rows
            if any(
                candidate.startswith(key + "-")
                for candidate in (slug(row.id), slug(row.name))
            )
        ]
        return matches[0] if len(matches) == 1 else None

    def _ledger(self):
        def check_and_run(effect):
            def execute(session, payload):
                if current_version(session) != payload["regulation_version"]:
                    return {"status": "policy_changed"}
                return effect(session, payload)

            return execute

        return ConfirmationLedger(
            session_factory=get_database().session,
            authorizer=self._authorize,
            effects={
                "reservar_area": check_and_run(reserve_effect),
                "autorizar_visitante": check_and_run(visit_effect),
            },
        )

    def reservation_limit(self):
        with get_database().transaction() as session:
            self._authorize(session, self.identity)
            if current_version(session) != 0:
                return (
                    "Não consegui confirmar se a versão vigente do regulamento estabelece "
                    "um limite por apartamento. Consulte a administração para confirmar."
                )
        return (
            "Não encontrei um limite de quantidade por apartamento no regulamento vigente. "
            "O art. 36 indica que as reservas são feitas pelo aplicativo. "
            "Na agenda, cada área aceita uma única reserva ativa por dia, "
            "mas isso não é um limite de reservas por morador."
        )

    def availability(self, area, data):
        try:
            day = read_day(data)
        except ValueError:
            return {"status": "invalid_details"}
        with get_database().transaction() as session:
            self._authorize(session, self.identity)
            row = self._area(session, area)
            if row is None:
                return {"status": "unknown_area"}
            exists = session.scalar(
                select(Reservation.code).where(
                    Reservation.area_id == row.id,
                    Reservation.date == day,
                    Reservation.status == "active",
                )
            )
            return {"status": "occupied" if exists else "available"}

    def reserve(self, area, data, *, proposal_id=None):
        try:
            day = read_day(data)
        except ValueError:
            return {"status": "invalid_details"}
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            existing = self._area(session, area)
            if existing is None:
                return {"status": "unknown_area"}
            version = current_version(session)
            if version is None:
                return {"status": "policy_review_required"}
            payload = {
                "apartment": apartment,
                "resident_id": self.identity.resident_id,
                "area": existing.id,
                "date": day.isoformat(),
                "fee_cents": existing.fee_cents,
                "regulation_version": version,
            }
            if existing.fee_cents == 0:
                result = reserve_effect(session, payload)
            else:
                occupied = session.scalar(
                    select(Reservation.code).where(
                        Reservation.area_id == existing.id,
                        Reservation.date == day,
                        Reservation.status == "active",
                    )
                )
                if occupied:
                    return {"status": "occupied"}
                result = None
        if result is not None:
            return result
        self._ledger().create(
            self.identity, "reservar_area", payload, proposal_id=proposal_id
        )
        return {"status": "pending"}

    def cancel(self, area, data):
        try:
            day = read_day(data)
        except ValueError:
            return {"status": "invalid_details"}
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            row = self._area(session, area)
            if row is None:
                return {"status": "unknown_area"}
            if current_version(session) is None:
                return {"status": "policy_review_required"}
            result = cancel_effect(
                session,
                {
                    "apartment": apartment,
                    "resident_id": self.identity.resident_id,
                    "area": row.id,
                    "date": day.isoformat(),
                },
            )
        return result

    def authorize_visit(self, nome, data, *, proposal_id=None):
        try:
            day = read_day(data)
            if (
                not isinstance(nome, str)
                or not 1 <= len(nome.strip()) <= 160
                or not nome.isprintable()
            ):
                raise ValueError("Nome inválido.")
        except ValueError:
            return {"status": "invalid_details"}
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            version = current_version(session)
            if version is None:
                return {"status": "policy_review_required"}
        self._ledger().create(
            self.identity,
            "autorizar_visitante",
            {
                "apartment": apartment,
                "resident_id": self.identity.resident_id,
                "name": " ".join(nome.split()),
                "date": day.isoformat(),
                "regulation_version": version,
            },
            proposal_id=proposal_id,
        )
        return {"status": "pending"}

    def list_my_visits(self):
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            visits = session.scalars(
                select(Visit)
                .where(
                    Visit.apartment == apartment,
                    Visit.resident_id == self.identity.resident_id,
                )
                .order_by(Visit.date, Visit.id)
            )
            return {
                "visitors": [
                    {"nome": row.name, "data": row.date.isoformat()} for row in visits
                ]
            }

    def pending(self):
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            records = session.scalars(
                select(ConfirmationRecord)
                .where(
                    ConfirmationRecord.session_id == str(self.identity.session_id),
                    ConfirmationRecord.resident_id == self.identity.resident_id,
                    ConfirmationRecord.apartment == apartment,
                    ConfirmationRecord.status == "pending",
                )
                .order_by(ConfirmationRecord.created_at, ConfirmationRecord.id)
            )
            return [
                {
                    "id": row.id,
                    "acao": row.action,
                    "detalhes": {
                        "data": row.payload["date"],
                        **(
                            {
                                "area": row.payload["area"],
                                "taxa": row.payload["fee_cents"] / 100,
                            }
                            if row.action == "reservar_area"
                            else {"nome": row.payload["name"]}
                        ),
                    },
                }
                for row in records
            ]
