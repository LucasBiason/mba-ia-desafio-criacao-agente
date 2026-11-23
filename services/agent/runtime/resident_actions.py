"""Explicit local test composition for portal-owned domain writes.

Agenda and visits supply effects; the portal ledger shares their condo-db
transaction in this profile. No academic store, autonomous charge or model
authorization. Off by default; do not enable against production unreviewed.
"""

from datetime import date
from pathlib import Path
import os
import re
import unicodedata

from sqlalchemy import func, select

from aurora_toolkit.identity import fetch_user
from aurora_toolkit.permissions import require_resident
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


def prepare_product_actions():
    with get_database().engine.begin() as conn:
        conn.execute(select(func.pg_advisory_xact_lock(640243)))
        ConfirmationRecord.__table__.create(conn, checkfirst=True)


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
    base_file = Path(os.getenv("AURORA_DATA_DIR", "/app/dados")) / "regulamento.md"
    if (
        regulation is None
        or regulation.version != 0
        or regulation.content != base_file.read_text(encoding="utf-8")
    ):
        return None  # Unmapped revision: no write authorization.
    return regulation.version


def _friendly(result):
    messages = {
        "reserved": "Reserva gravada. Código: {code}.",
        "occupied": "A área já está ocupada nessa data. Nenhuma reserva foi criada.",
        "cancelled": "Sua reserva foi cancelada.",
        "authorized": "A autorização do visitante foi gravada.",
        "not_found": "Nenhuma reserva ativa da sua unidade corresponde ao pedido.",
        "unknown_area": "Área não cadastrada.",
        "fee_changed": "A taxa mudou. Faça uma nova proposta antes de confirmar.",
        "policy_review_required": "A edição vigente do regulamento ainda não tem regras de execução aprovadas. Nenhuma alteração foi feita.",
        "policy_changed": "O regulamento mudou desde a proposta. Nenhuma alteração foi feita.",
        "invalid_details": "Informe uma área ou um visitante válido e uma data válida.",
        "pending": "O pedido está pendente. Use Aprovar ou Negar no cartão; um “sim” no chat não autoriza.",
        "rejected": "Pedido negado. Nenhuma alteração foi feita.",
    }
    value = result.get("status")
    return messages.get(
        value, "Não há confirmação de que a operação foi executada."
    ).format(code=result.get("code", ""))


class ProductActions:
    def __init__(self, identity):
        self.identity = identity
        self.results = []

    def _actor(self):
        actor = fetch_user(self.identity.resident_id)
        require_resident(actor)
        if (
            actor.get("id") != self.identity.resident_id
            or actor.get("active") is not True
        ):
            raise error(401, "INVALID_SESSION", "Identidade inválida.")
        return actor

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
        return next(
            (
                row
                for row in session.scalars(select(Area))
                if key in (row.id, slug(row.name))
            ),
            None,
        )

    def _store(self, value):
        self.results.append(value)
        return value

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
        self._actor()
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
        self._actor()
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

    def reserve(self, area, data):
        self._actor()
        try:
            day = read_day(data)
        except ValueError:
            return self._store({"status": "invalid_details"})
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            existing = self._area(session, area)
            if existing is None:
                return self._store({"status": "unknown_area"})
            version = current_version(session)
            if version is None:
                return self._store({"status": "policy_review_required"})
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
                    return self._store({"status": "occupied"})
                result = None
        if result is not None:
            return self._store(result)
        self._ledger().create(self.identity, "reservar_area", payload)
        return self._store({"status": "pending"})

    def cancel(self, area, data):
        self._actor()
        try:
            day = read_day(data)
        except ValueError:
            return self._store({"status": "invalid_details"})
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            row = self._area(session, area)
            if row is None:
                return self._store({"status": "unknown_area"})
            if current_version(session) is None:
                return self._store({"status": "policy_review_required"})
            result = cancel_effect(
                session,
                {
                    "apartment": apartment,
                    "resident_id": self.identity.resident_id,
                    "area": row.id,
                    "date": day.isoformat(),
                },
            )
        return self._store(result)

    def authorize_visit(self, nome, data):
        self._actor()
        try:
            day = read_day(data)
            if (
                not isinstance(nome, str)
                or not 1 <= len(nome.strip()) <= 160
                or not nome.isprintable()
            ):
                raise ValueError("Nome inválido.")
        except ValueError:
            return self._store({"status": "invalid_details"})
        with get_database().transaction() as session:
            apartment = self._authorize(session, self.identity)
            version = current_version(session)
            if version is None:
                return self._store({"status": "policy_review_required"})
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
        )
        return self._store({"status": "pending"})

    def list_my_visits(self):
        self._actor()
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
        self._actor()
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

    def _pending_projection(self, *, preserve_receipt):
        try:
            return {"confirmacoes_pendentes": self.pending()}
        except Exception as exc:
            # Never disclose a cached receipt after an explicit ownership or
            # identity revocation. Transient refresh errors must not erase commit.
            from fastapi import HTTPException

            if isinstance(exc, HTTPException) and exc.status_code in (401, 403, 404):
                raise
            if not preserve_receipt:
                raise
            return {"confirmacoes_pendentes": [], "pending_refresh_failed": True}

    def message_projection(self, text):
        if self.results:
            text = "\n".join(_friendly(item) for item in self.results)
        else:
            text = "Nenhuma alteração foi registrada neste turno.\n" + (text or "")
        return {
            "message": text,
            **self._pending_projection(preserve_receipt=bool(self.results)),
        }

    def decide(self, confirmation_id, confirmed):
        self._actor()
        outcome = self._ledger().decide(self.identity, str(confirmation_id), confirmed)
        result = outcome["result"] or {"status": "rejected"}
        # Ledger yields only after successful commit; never ask Gemini for the verdict.
        return {
            "message": _friendly(result),
            "resultado": result,
            **self._pending_projection(preserve_receipt=True),
        }
