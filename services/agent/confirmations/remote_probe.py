"""Experimento de outbox/inbox sem HTTP, worker ativo ou migração de produto.

O inbox aqui é simulador do serviço proprietário, NÃO um repository de agenda
no agente. Cada lado recebe session_factory própria e só escreve no seu banco.
"""

from copy import deepcopy
import hashlib
import json

from sqlalchemy import Column, JSON, String, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase
from microservice_toolkit import error
from services.agent.confirmations.ledger import LedgerBase


class InboxBase(DeclarativeBase):
    """Independent metadata for the remote_probe persistence boundary."""

    pass


def fingerprint(command):
    return hashlib.sha256(
        json.dumps(
            command, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class OutboxCommand(LedgerBase):
    __tablename__ = "agent_outbox_probe"
    id = Column(String(36), primary_key=True)
    command = Column(JSON, nullable=False)
    digest = Column(String(64), nullable=False)
    status = Column(String, nullable=False)
    result = Column(JSON)


class InboxReceipt(InboxBase):
    __tablename__ = "domain_inbox_probe"
    id = Column(String(36), primary_key=True)
    digest = Column(String(64), nullable=False)
    result = Column(JSON)


def enqueue_command(session, command):
    """Porta local do ledger: decisão+outbox no MESMO commit, sem contato remoto."""
    session.add(
        OutboxCommand(
            id=command["id"],
            command=deepcopy(command),
            digest=fingerprint(command),
            status="pending",
        )
    )
    session.flush()
    return {"command_id": command["id"], "delivery": "pending"}


class SyntheticDomainInbox:
    def __init__(
        self, *, session_factory, authorizer, effect, reconciliation_authorizer=None
    ):
        self.session_factory = session_factory
        self.authorizer = authorizer
        self.effect = effect
        self.reconciliation_authorizer = reconciliation_authorizer

    def accept(self, command):
        digest = fingerprint(command)
        try:
            with self.session_factory() as session, session.begin():
                self.authorizer(session, command)
                record = InboxReceipt(id=command["id"], digest=digest)
                session.add(record)
                session.flush()
                # Inbox e efeito no mesmo banco/transação. Erro reverte ambos.
                record.result = deepcopy(self.effect(session, deepcopy(command)))
                session.flush()
                result = deepcopy(record.result)
        except IntegrityError:
            # Após rollback completo, verificar receipt já COMMITADO. Não usar
            # savepoint antes de BEGIN real: sqlite legacy pode persistir cedo.
            with self.session_factory() as session, session.begin():
                self.authorizer(session, command)
                record = session.get(InboxReceipt, command["id"])
                if record is None:
                    raise
                if record.digest != digest:
                    raise error(
                        409,
                        "COMMAND_KEY_REUSED",
                        "Identificador reutilizado para outro comando.",
                    )
                result = deepcopy(record.result)
        return {"command_id": command["id"], "digest": digest, "result": result}

    def reconcile_receipt(self, command_id, digest, service_identity):
        """Canal interno restrito: confirma commit, nunca devolve resultado/payload.

        Não substitui autorização do morador. O caller deve provar identidade
        de serviço E escopo do comando; default desabilitado (fail closed).
        """
        if self.reconciliation_authorizer is None:
            raise error(403, "RECONCILIATION_DENIED", "Reconciliação não autorizada.")
        with self.session_factory() as session, session.begin():
            self.reconciliation_authorizer(
                session, service_identity, command_id, digest
            )
            record = session.get(InboxReceipt, command_id)
            if record is not None and record.digest != digest:
                raise error(
                    409, "COMMAND_KEY_REUSED", "Identificador de comando divergente."
                )
            return {
                "command_id": command_id,
                "digest": digest,
                "committed": record is not None,
            }


class OutboxDeliveryProbe:
    def __init__(self, *, session_factory, send):
        self.session_factory = session_factory
        self.send = send

    def deliver(self, command_id):
        with self.session_factory() as session:
            record = session.get(OutboxCommand, command_id)
            if record is None:
                raise KeyError(command_id)
            if record.status == "reconciled":
                return {"delivery": "reconciled", "result_available": False}
            if record.status == "delivered":
                return deepcopy(record.result)
            command, digest = deepcopy(record.command), record.digest
        # Nenhuma transação local atravessa a chamada remota. Falha/ACK perdido
        # mantém pending para redelivery; idempotência pertence ao inbox remoto.
        receipt = self.send(command)
        if (
            not isinstance(receipt, dict)
            or receipt.get("command_id") != command_id
            or receipt.get("digest") != digest
            or "result" not in receipt
        ):
            raise ValueError("Resposta do destino não corresponde ao comando.")
        with self.session_factory() as session, session.begin():
            session.execute(
                update(OutboxCommand)
                .where(
                    OutboxCommand.id == command_id,
                    OutboxCommand.digest == digest,
                    OutboxCommand.status == "pending",
                )
                .values(status="delivered", result=deepcopy(receipt["result"]))
            )
        return deepcopy(receipt["result"])

    def reconcile(self, command_id, query_receipt):
        """Operação do dispatcher, não uma resposta pública de confirmação.

        Não chama send/effect, nem libera resultado de morador revogado. Ausência
        do receipt não autoriza novo envio: apenas mantém a pendência interna.
        """
        with self.session_factory() as session:
            record = session.get(OutboxCommand, command_id)
            if record is None:
                raise KeyError(command_id)
            digest = record.digest
        receipt = query_receipt(command_id, digest)
        if (
            not isinstance(receipt, dict)
            or receipt.get("command_id") != command_id
            or receipt.get("digest") != digest
            or type(receipt.get("committed")) is not bool
        ):
            raise ValueError("Resposta de reconciliação inválida.")
        if receipt["committed"]:
            with self.session_factory() as session, session.begin():
                session.execute(
                    update(OutboxCommand)
                    .where(
                        OutboxCommand.id == command_id,
                        OutboxCommand.digest == digest,
                        OutboxCommand.status == "pending",
                    )
                    .values(status="reconciled", result=None)
                )
        return {"committed": receipt["committed"], "result_available": False}
