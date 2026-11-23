"""Dois bancos isolados: ACK perdido, replay e chave divergente, sem rede."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from services.agent.confirmations.ledger import LedgerBase, ConfirmationLedger
from services.agent.confirmations.remote_probe import (
    InboxBase,
    InboxReceipt,
    OutboxCommand,
    SyntheticDomainInbox,
    OutboxDeliveryProbe,
    enqueue_command,
)
from services.agent.tools.reservation_read import SessionIdentity


class RemoteConfirmationProbeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = create_engine(f"sqlite:///{Path(self.temp.name) / 'agent.db'}")
        self.target = create_engine(f"sqlite:///{Path(self.temp.name) / 'domain.db'}")
        LedgerBase.metadata.create_all(self.source)
        InboxBase.metadata.create_all(self.target)
        with self.target.begin() as conn:
            conn.execute(text("CREATE TABLE effects(value TEXT)"))
        self.source_sessions = sessionmaker(self.source)
        self.target_sessions = sessionmaker(self.target)
        self.identity = SessionIdentity(uuid4(), "resident-a")
        self.command = {
            "id": str(uuid4()),
            "session_id": str(self.identity.session_id),
            "resident_id": "resident-a",
            "apartment": "101",
            "action": "synthetic",
            "payload": {"value": "once"},
        }

        def authorize(session, command):
            if command["resident_id"] != "resident-a" or command["apartment"] != "101":
                raise HTTPException(403, "Denied")

        def effect(session, command):
            session.execute(
                text("INSERT INTO effects VALUES(:value)"), command["payload"]
            )
            return {"status": "stored", "value": command["payload"]["value"]}

        self.inbox = SyntheticDomainInbox(
            session_factory=self.target_sessions, authorizer=authorize, effect=effect
        )
        self.ledger = ConfirmationLedger(
            session_factory=self.source_sessions,
            authorizer=lambda session, identity: "101",
            effects={"remote": enqueue_command},
        )

    def tearDown(self):
        self.source.dispose()
        self.target.dispose()
        self.temp.cleanup()

    def approve(self):
        cid = self.ledger.create(self.identity, "remote", self.command)
        return cid, self.ledger.decide(self.identity, cid, True)

    def count(self):
        with self.target.connect() as conn:
            return conn.execute(text("SELECT count(*) FROM effects")).scalar_one()

    def delivery(self, send=None):
        return OutboxDeliveryProbe(
            session_factory=self.source_sessions, send=send or self.inbox.accept
        )

    def test_approval_only_queues_then_delivers(self):
        cid, result = self.approve()
        self.assertEqual(result["result"]["delivery"], "pending")
        self.assertEqual(self.count(), 0)
        self.delivery().deliver(self.command["id"])
        self.delivery().deliver(self.command["id"])
        self.assertEqual(self.count(), 1)
        with self.assertRaises(HTTPException):
            self.ledger.decide(self.identity, cid, True)

    def test_lost_ack_then_restart_redelivery_executes_once(self):
        self.approve()

        def lose_ack(command):
            self.inbox.accept(command)
            raise TimeoutError("synthetic ACK loss")

        with self.assertRaises(TimeoutError):
            self.delivery(lose_ack).deliver(self.command["id"])
        self.assertEqual(self.count(), 1)
        with self.source_sessions() as session:
            self.assertEqual(
                session.get(OutboxCommand, self.command["id"]).status, "pending"
            )
        self.source.dispose()
        self.target.dispose()
        result = self.delivery().deliver(self.command["id"])
        self.assertEqual(result["status"], "stored")
        self.assertEqual(self.count(), 1)

    def test_same_key_different_original_payload_is_rejected(self):
        self.inbox.accept(self.command)
        changed = {**self.command, "payload": {"value": "different"}}
        with self.assertRaises(HTTPException) as caught:
            self.inbox.accept(changed)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.count(), 1)

    def test_effect_failure_rolls_back_inbox_and_effect(self):
        original = self.inbox.effect

        def fail(session, command):
            original(session, command)
            raise RuntimeError("synthetic failure")

        self.inbox.effect = fail
        with self.assertRaises(RuntimeError):
            self.inbox.accept(self.command)
        self.assertEqual(self.count(), 0)
        with self.target_sessions() as session:
            self.assertIsNone(session.get(InboxReceipt, self.command["id"]))
        self.inbox.effect = original
        self.inbox.accept(self.command)
        self.assertEqual(self.count(), 1)

    def test_mismatched_receipt_cannot_mark_delivered(self):
        self.approve()
        with self.assertRaises(ValueError):
            self.delivery(
                lambda _: {"command_id": "wrong", "digest": "wrong", "result": {}}
            ).deliver(self.command["id"])
        with self.source_sessions() as session:
            self.assertEqual(
                session.get(OutboxCommand, self.command["id"]).status, "pending"
            )
        self.assertEqual(self.count(), 0)

    def test_concurrent_redelivery_with_independent_engines_effect_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        barrier = Barrier(2)

        def receive():
            engine = create_engine(self.target.url, connect_args={"timeout": 15})
            inbox = SyntheticDomainInbox(
                session_factory=sessionmaker(engine),
                authorizer=self.inbox.authorizer,
                effect=self.inbox.effect,
            )
            try:
                barrier.wait(timeout=5)
                return inbox.accept(self.command)
            finally:
                engine.dispose()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(receive) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.count(), 1)

    def test_denied_remote_authorization_leaves_outbox_pending(self):
        self.approve()

        def deny(session, command):
            raise HTTPException(403, "Revoked")

        self.inbox.authorizer = deny
        with self.assertRaises(HTTPException):
            self.delivery().deliver(self.command["id"])
        self.assertEqual(self.count(), 0)
        with self.source_sessions() as session:
            self.assertEqual(
                session.get(OutboxCommand, self.command["id"]).status, "pending"
            )

    def reconciliation_channel(self):
        def allow(session, principal, command_id, digest):
            if principal != "dispatcher-only" or command_id != self.command["id"]:
                raise HTTPException(403, "Denied")

        self.inbox.reconciliation_authorizer = allow
        return lambda cid, digest: self.inbox.reconcile_receipt(
            cid, digest, "dispatcher-only"
        )

    def test_revoked_after_commit_lost_ack_reconciles_without_disclosure(self):
        from unittest.mock import MagicMock

        cid, _ = self.approve()

        def lose_ack(command):
            self.inbox.accept(command)
            raise TimeoutError("lost ACK")

        with self.assertRaises(TimeoutError):
            self.delivery(lose_ack).deliver(self.command["id"])

        def revoked(session, command):
            raise HTTPException(403, "Revoked")

        self.inbox.authorizer = revoked
        with self.assertRaises(HTTPException):
            self.delivery().deliver(self.command["id"])
        effect_spy = MagicMock(side_effect=AssertionError("Must never execute"))
        self.inbox.effect = effect_spy
        send_spy = MagicMock(side_effect=AssertionError("Must never resend"))
        dispatcher = self.delivery(send_spy)
        result = dispatcher.reconcile(self.command["id"], self.reconciliation_channel())
        self.assertEqual(result, {"committed": True, "result_available": False})
        with self.source_sessions() as session:
            row = session.get(OutboxCommand, self.command["id"])
            self.assertEqual(row.status, "reconciled")
            self.assertIsNone(row.result)
        self.assertEqual(
            dispatcher.deliver(self.command["id"]),
            {"delivery": "reconciled", "result_available": False},
        )
        with self.assertRaises(HTTPException):
            self.inbox.accept(self.command)
        with self.assertRaises(HTTPException) as caught:
            self.ledger.decide(self.identity, cid, True)
        self.assertEqual(caught.exception.status_code, 409)
        send_spy.assert_not_called()
        effect_spy.assert_not_called()
        self.assertEqual(self.count(), 1)

    def test_receipt_channel_denies_resident_and_unknown_service(self):
        from services.agent.confirmations.remote_probe import fingerprint

        digest = fingerprint(self.command)
        self.inbox.accept(self.command)
        with self.assertRaises(HTTPException):
            self.inbox.reconcile_receipt(self.command["id"], digest, "resident-a")
        self.reconciliation_channel()
        for principal in ("resident-a", "untrusted-service"):
            with self.assertRaises(HTTPException) as caught:
                self.inbox.reconcile_receipt(self.command["id"], digest, principal)
            self.assertEqual(caught.exception.status_code, 403)
        with self.assertRaises(HTTPException) as caught:
            self.inbox.reconcile_receipt(
                self.command["id"], "wrong-digest", "dispatcher-only"
            )
        self.assertEqual(caught.exception.status_code, 409)

    def test_absent_receipt_never_grants_permission_to_resend(self):
        from unittest.mock import MagicMock

        self.approve()
        send = MagicMock(side_effect=AssertionError("No send"))
        result = self.delivery(send).reconcile(
            self.command["id"], self.reconciliation_channel()
        )
        self.assertFalse(result["committed"])
        with self.source_sessions() as session:
            self.assertEqual(
                session.get(OutboxCommand, self.command["id"]).status, "pending"
            )
        send.assert_not_called()
        self.assertEqual(self.count(), 0)
