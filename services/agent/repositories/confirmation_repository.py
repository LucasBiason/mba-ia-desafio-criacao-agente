"""Consumo único no banco, atomicamente com efeitos SQL locais.

Somente portas confiáveis podem ser registradas. authorizer(session, identity)
revalida identidade/vínculo e devolve a unidade; effects[action](session, payload)
executa SQL na MESMA transação, sem commit, rede ou efeitos externos. Integração
com serviços HTTP exigirá outbox/idempotência e NÃO é garantida por esta classe.
"""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from microservice_toolkit import error


from services.agent.models.confirmation_record import ConfirmationRecord


class ConfirmationLedger:
    def __init__(self, *, session_factory, authorizer, effects):
        self.session_factory = session_factory
        self.authorizer = authorizer
        self.effects = dict(effects)

    @staticmethod
    def _reuse(record, identity, apartment, action, payload):
        """Reuse only the original, still-pending proposal in its exact scope."""
        if (
            record.session_id != str(identity.session_id)
            or record.resident_id != identity.resident_id
            or record.apartment != apartment
            or record.action != action
            or record.payload != payload
            or record.status != "pending"
        ):
            raise error(
                409, "CONFIRMATION_INVALID", "Proposta incompatível ou já decidida."
            )
        return record.id

    def create(self, identity, action, payload, *, proposal_id=None):
        if action not in self.effects:
            raise ValueError("Ação de confirmação não registrada.")
        if proposal_id is not None:
            try:
                if (
                    not isinstance(proposal_id, str)
                    or str(UUID(proposal_id)) != proposal_id
                ):
                    raise ValueError
            except (ValueError, AttributeError):
                raise ValueError(
                    "Identificador interno de proposta inválido."
                ) from None
        identifier = proposal_id or str(uuid4())
        # The caller cannot mutate persisted data after the proposal is created.
        original = deepcopy(payload)
        try:
            with self.session_factory() as session, session.begin():
                apartment = self.authorizer(session, identity)
                if proposal_id is not None:
                    existing = session.get(ConfirmationRecord, identifier)
                    if existing is not None:
                        return self._reuse(
                            existing, identity, apartment, action, original
                        )
                record = ConfirmationRecord(
                    id=identifier,
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
        except IntegrityError:
            if proposal_id is None:
                raise
            # A concurrent creator may have won the PK. The failed transaction
            # has rolled back; authorize and compare again in a fresh one.
            with self.session_factory() as session, session.begin():
                apartment = self.authorizer(session, identity)
                existing = session.get(ConfirmationRecord, identifier)
                if existing is None:
                    raise
                return self._reuse(existing, identity, apartment, action, original)

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
