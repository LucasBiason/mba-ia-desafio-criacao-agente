"""Consumo único no banco, atomicamente com efeitos SQL locais.

Somente portas confiáveis podem ser registradas. authorizer(session, identity)
revalida identidade/vínculo e devolve a unidade; effects[action](session, payload)
executa SQL na MESMA transação, sem commit, rede ou efeitos externos. Integração
com serviços HTTP exigirá outbox/idempotência e NÃO é garantida por esta classe.
"""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, JSON, String, select, update
from sqlalchemy.orm import DeclarativeBase
from microservice_toolkit import error


# Metadata separada para o experimento: não entra no bootstrap do condomínio.
class LedgerBase(DeclarativeBase):
    """Independent metadata for the ledger persistence boundary."""

    pass


class ConfirmationRecord(LedgerBase):
    __tablename__ = "agent_confirmation_ledger"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    resident_id = Column(String, nullable=False)
    apartment = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status IN ('pending','approved','rejected')"),)


class ConfirmationLedger:
    def __init__(self, *, session_factory, authorizer, effects):
        self.session_factory = session_factory
        self.authorizer = authorizer
        self.effects = dict(effects)

    def create(self, identity, action, payload):
        if action not in self.effects:
            raise ValueError("Ação de confirmação não registrada.")
        # Copiar antes de persistir: alterações do caller não mudam o item original.
        original = deepcopy(payload)
        with self.session_factory() as session, session.begin():
            apartment = self.authorizer(session, identity)
            record = ConfirmationRecord(
                id=str(uuid4()),
                session_id=str(identity.session_id),
                resident_id=identity.resident_id,
                apartment=apartment,
                action=action,
                payload=original,
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
            session.add(record)
            session.flush()
            return record.id

    def decide(self, identity, confirmation_id, confirmed):
        if type(confirmed) is not bool:
            raise ValueError("A decisão deve ser booleana.")
        with self.session_factory() as session, session.begin():
            apartment = self.authorizer(session, identity)
            # Compare-and-set no banco é a disputa: não SELECT seguido de UPDATE
            # incondicional nem lock em memória. O perdedor não executa a porta.
            claimed = session.execute(
                update(ConfirmationRecord)
                .where(
                    ConfirmationRecord.id == confirmation_id,
                    ConfirmationRecord.session_id == str(identity.session_id),
                    ConfirmationRecord.resident_id == identity.resident_id,
                    ConfirmationRecord.apartment == apartment,
                    ConfirmationRecord.status == "pending",
                )
                .values(
                    status="approved" if confirmed else "rejected",
                    decided_at=datetime.now(timezone.utc),
                )
            )
            if claimed.rowcount != 1:
                raise error(
                    409,
                    "CONFIRMATION_INVALID",
                    "Confirmação inexistente ou já decidida.",
                )
            record = session.execute(
                select(ConfirmationRecord).where(
                    ConfirmationRecord.id == confirmation_id
                )
            ).scalar_one()
            result = None
            if confirmed:
                # Os argumentos vêm do registro durável, nunca da resposta de aprovação.
                result = self.effects[record.action](session, deepcopy(record.payload))
            record.result = deepcopy(result)
            session.flush()
            # O contexto só retorna ao caller depois do commit; exceção reverte
            # tanto o consumo quanto qualquer efeito local registrado nesta sessão.
            return {
                "id": record.id,
                "status": record.status,
                "result": deepcopy(result),
            }
