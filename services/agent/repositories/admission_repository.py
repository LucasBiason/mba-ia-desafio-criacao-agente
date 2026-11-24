"""Admissão durável antes do modelo; nenhum lock fica aberto durante o provedor.

O UPDATE ORM na linha singleton serializa a decisão no PostgreSQL e SQLite.
Cada turno reserva seis chamadas (o teto do Runner), sem devolver o orçamento
após falha. Leases sobrevivem a reinícios e expiram após o timeout + margem.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import delete, func, select, update
from microservice_toolkit import error, get_database
from services.agent.models.admission_gate import AdmissionGate
from services.agent.models.admission_lease import AdmissionLease
from services.agent.runtime.limits import AGENT_EXECUTION_TIMEOUT_SECONDS


class AdmissionRepository:
    WINDOW_SECONDS = 60
    ACTOR_TURNS = 10
    GLOBAL_TURNS = 100
    ACTOR_CONCURRENT = 1
    GLOBAL_CONCURRENT = 4
    CALL_BUDGET = 6

    def __init__(self, database=None, *, now=None):
        self.database = database or get_database()
        self.now = now or (lambda: datetime.now(timezone.utc))

    def acquire(self, identity):
        now = self.now()
        with self.database.transaction() as session:
            locked = session.execute(
                update(AdmissionGate)
                .where(AdmissionGate.id == 1)
                .values(revision=AdmissionGate.revision + 1)
            )
            if locked.rowcount != 1:
                raise error(
                    503,
                    "AGENT_NOT_PREPARED",
                    "O assistente ainda não foi preparado pela administração.",
                )
            active = (
                AdmissionLease.released_at.is_(None),
                AdmissionLease.expires_at > now,
            )
            if session.scalar(
                select(AdmissionLease.id)
                .where(*active, AdmissionLease.session_id == str(identity.session_id))
                .limit(1)
            ):
                raise error(
                    409,
                    "CHAT_SESSION_CONFLICT",
                    "Há uma mensagem em andamento nesta conversa. Atualize o histórico antes de reenviar.",
                )
            actor_active = session.scalar(
                select(func.count())
                .select_from(AdmissionLease)
                .where(*active, AdmissionLease.resident_id == identity.resident_id)
            )
            total_active = session.scalar(
                select(func.count()).select_from(AdmissionLease).where(*active)
            )
            if (
                actor_active >= self.ACTOR_CONCURRENT
                or total_active >= self.GLOBAL_CONCURRENT
            ):
                raise error(
                    429,
                    "AGENT_CAPACITY_EXCEEDED",
                    "O assistente está ocupado. Aguarde antes de enviar outra mensagem.",
                )
            window = AdmissionLease.started_at > now - timedelta(
                seconds=self.WINDOW_SECONDS
            )
            actor_budget = session.scalar(
                select(func.coalesce(func.sum(AdmissionLease.call_budget), 0)).where(
                    window, AdmissionLease.resident_id == identity.resident_id
                )
            )
            global_budget = session.scalar(
                select(func.coalesce(func.sum(AdmissionLease.call_budget), 0)).where(
                    window
                )
            )
            if (
                actor_budget + self.CALL_BUDGET > self.ACTOR_TURNS * self.CALL_BUDGET
                or global_budget + self.CALL_BUDGET
                > self.GLOBAL_TURNS * self.CALL_BUDGET
            ):
                raise error(
                    429,
                    "AGENT_RATE_LIMITED",
                    "O limite de mensagens foi atingido. Aguarde um minuto antes de tentar novamente.",
                )
            session.execute(
                delete(AdmissionLease).where(
                    AdmissionLease.started_at
                    < now - timedelta(seconds=2 * self.WINDOW_SECONDS),
                    AdmissionLease.expires_at < now,
                )
            )
            lease = AdmissionLease(
                id=str(uuid4()),
                session_id=str(identity.session_id),
                resident_id=identity.resident_id,
                started_at=now,
                expires_at=now
                + timedelta(seconds=AGENT_EXECUTION_TIMEOUT_SECONDS + 30),
                call_budget=self.CALL_BUDGET,
            )
            session.add(lease)
            session.flush()
            return lease.id

    def release(self, lease_id):
        with self.database.transaction() as session:
            session.execute(
                update(AdmissionLease)
                .where(AdmissionLease.id == lease_id)
                .values(released_at=self.now())
            )
