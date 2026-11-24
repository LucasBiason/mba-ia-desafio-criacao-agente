"""Ledger SQL real, efeitos sintéticos, arquivo SQLite temporário e processos separados."""

import multiprocessing
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.agent.confirmations.ledger import (
    ConfirmationLedger,
    ConfirmationRecord,
    LedgerBase,
)
from services.agent.tools.reservation_read import SessionIdentity


def authorize(session, identity):
    row = session.execute(
        text(
            "SELECT apartment FROM bindings WHERE session_id=:sid AND resident_id=:uid AND active=1"
        ),
        {"sid": str(identity.session_id), "uid": identity.resident_id},
    ).first()
    if row is None:
        raise HTTPException(404, "Session unavailable")
    return row[0]


def effect(session, payload):
    session.execute(
        text("INSERT INTO effects(value) VALUES(:value)"), {"value": payload["value"]}
    )
    return {"stored": payload["value"]}


def concurrent_worker(url, sid, cid, barrier, queue):
    engine = create_engine(url, connect_args={"timeout": 15})
    ledger = ConfirmationLedger(
        session_factory=sessionmaker(engine),
        authorizer=authorize,
        effects={"synthetic": effect},
    )
    barrier.wait(timeout=15)
    try:
        queue.put(
            ledger.decide(SessionIdentity(UUID(sid), "resident-a"), cid, True)["status"]
        )
    except HTTPException as exc:
        queue.put(exc.status_code)
    except Exception as exc:
        queue.put(type(exc).__name__)
    finally:
        engine.dispose()


def concurrent_proposal_worker(url, sid, proposal_id, barrier, queue):
    engine = create_engine(url, connect_args={"timeout": 15})
    ledger = ConfirmationLedger(
        session_factory=sessionmaker(engine),
        authorizer=authorize,
        effects={"synthetic": effect},
    )
    barrier.wait(timeout=15)
    try:
        queue.put(
            ledger.create(
                SessionIdentity(UUID(sid), "resident-a"),
                "synthetic",
                {"value": "original"},
                proposal_id=proposal_id,
            )
        )
    except Exception as exc:
        queue.put(type(exc).__name__)
    finally:
        engine.dispose()


class ConfirmationLedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.url = f"sqlite:///{Path(self.temp.name) / 'ledger.db'}"
        self.engine = create_engine(self.url, connect_args={"timeout": 15})
        LedgerBase.metadata.create_all(self.engine)
        self.identity = SessionIdentity(uuid4(), "resident-a")
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE bindings(session_id TEXT,resident_id TEXT,apartment TEXT,active INTEGER)"
                )
            )
            conn.execute(text("CREATE TABLE effects(value TEXT)"))
            conn.execute(
                text("INSERT INTO bindings VALUES(:sid,'resident-a','101',1)"),
                {"sid": str(self.identity.session_id)},
            )
        self.ledger = self.build()

    def build(self, effects=None):
        return ConfirmationLedger(
            session_factory=sessionmaker(self.engine),
            authorizer=authorize,
            effects=effects or {"synthetic": effect},
        )

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def rows(self):
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT value FROM effects")).scalars().all()

    def test_approve_original_payload_and_replay_conflict(self):
        payload = {"value": "original"}
        cid = self.ledger.create(self.identity, "synthetic", payload)
        payload["value"] = "tampered"
        result = self.ledger.decide(self.identity, cid, True)
        self.assertEqual(result["result"], {"stored": "original"})
        with self.assertRaises(HTTPException) as caught:
            self.ledger.decide(self.identity, cid, True)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.rows(), ["original"])

    def test_rejection_consumes_without_effect(self):
        cid = self.ledger.create(self.identity, "synthetic", {"value": "unused"})
        self.assertEqual(
            self.ledger.decide(self.identity, cid, False)["status"], "rejected"
        )
        with self.assertRaises(HTTPException):
            self.ledger.decide(self.identity, cid, True)
        self.assertEqual(self.rows(), [])

    def test_failure_rolls_back_claim_and_effect_together(self):
        def fail(session, payload):
            effect(session, payload)
            raise RuntimeError("synthetic failure")

        cid = self.ledger.create(self.identity, "synthetic", {"value": "once"})
        with self.assertRaises(RuntimeError):
            self.build({"synthetic": fail}).decide(self.identity, cid, True)
        self.assertEqual(self.rows(), [])
        with sessionmaker(self.engine)() as session:
            self.assertEqual(session.get(ConfirmationRecord, cid).status, "pending")
        self.ledger.decide(self.identity, cid, True)
        self.assertEqual(self.rows(), ["once"])

    def test_restart_keeps_pending_and_decision(self):
        cid = self.ledger.create(self.identity, "synthetic", {"value": "durable"})
        self.engine.dispose()
        self.engine = create_engine(self.url)
        self.build().decide(self.identity, cid, True)
        self.engine.dispose()
        self.engine = create_engine(self.url)
        with self.assertRaises(HTTPException):
            self.build().decide(self.identity, cid, False)
        self.assertEqual(self.rows(), ["durable"])

    def test_other_session_unknown_pending_and_revocation(self):
        cid = self.ledger.create(self.identity, "synthetic", {"value": "private"})
        other = SessionIdentity(uuid4(), "resident-a")
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO bindings VALUES(:sid,'resident-a','101',1)"),
                {"sid": str(other.session_id)},
            )
        for identity, pending in ((other, cid), (self.identity, str(uuid4()))):
            with self.assertRaises(HTTPException) as caught:
                self.ledger.decide(identity, pending, True)
            self.assertEqual(caught.exception.status_code, 409)
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE bindings SET active=0"))
        with self.assertRaises(HTTPException) as caught:
            self.ledger.decide(self.identity, cid, True)
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.rows(), [])

    def test_two_processes_only_one_consumes(self):
        cid = self.ledger.create(self.identity, "synthetic", {"value": "winner"})
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(3)
        queue = ctx.Queue()
        workers = [
            ctx.Process(
                target=concurrent_worker,
                args=(self.url, str(self.identity.session_id), cid, barrier, queue),
            )
            for _ in range(2)
        ]
        try:
            for worker in workers:
                worker.start()
            barrier.wait(timeout=15)
            results = [queue.get(timeout=20), queue.get(timeout=20)]
            self.assertCountEqual(results, ["approved", 409])
            for worker in workers:
                worker.join(timeout=10)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(self.rows(), ["winner"])
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
            queue.close()

    def test_action_and_boolean_are_strict(self):
        with self.assertRaises(ValueError):
            self.ledger.create(self.identity, "unregistered", {})
        cid = self.ledger.create(self.identity, "synthetic", {"value": "safe"})
        with self.assertRaises(ValueError):
            self.ledger.decide(self.identity, cid, "true")
        self.assertEqual(self.rows(), [])

    def test_proposal_key_reuses_only_same_original_pending_scope(self):
        proposal_id = str(uuid4())
        payload = {"value": "original"}
        first = self.ledger.create(
            self.identity, "synthetic", payload, proposal_id=proposal_id
        )
        self.assertEqual(first, proposal_id)
        self.assertEqual(
            self.ledger.create(
                self.identity, "synthetic", dict(payload), proposal_id=proposal_id
            ),
            first,
        )
        payload["value"] = "tampered"
        with self.assertRaises(HTTPException) as caught:
            self.ledger.create(
                self.identity, "synthetic", payload, proposal_id=proposal_id
            )
        self.assertEqual(caught.exception.status_code, 409)
        other = SessionIdentity(uuid4(), "resident-a")
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO bindings VALUES(:sid,'resident-a','101',1)"),
                {"sid": str(other.session_id)},
            )
        with self.assertRaises(HTTPException) as caught:
            self.ledger.create(
                other, "synthetic", {"value": "original"}, proposal_id=proposal_id
            )
        self.assertEqual(caught.exception.status_code, 409)
        with sessionmaker(self.engine)() as session:
            self.assertEqual(len(session.query(ConfirmationRecord).all()), 1)
        self.assertEqual(self.rows(), [])
        outcome = self.ledger.decide(self.identity, first, True)
        self.assertEqual(outcome["result"], {"stored": "original"})
        with self.assertRaises(HTTPException) as caught:
            self.ledger.create(
                self.identity,
                "synthetic",
                {"value": "original"},
                proposal_id=proposal_id,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.rows(), ["original"])

    def test_proposal_key_does_not_bypass_revocation_or_uuid_validation(self):
        proposal_id = str(uuid4())
        self.ledger.create(
            self.identity, "synthetic", {"value": "original"}, proposal_id=proposal_id
        )
        for invalid in ("foreign", 42, {}, proposal_id.upper()):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.ledger.create(self.identity, "synthetic", {}, proposal_id=invalid)
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE bindings SET active=0"))
        with self.assertRaises(HTTPException) as caught:
            self.ledger.create(
                self.identity,
                "synthetic",
                {"value": "original"},
                proposal_id=proposal_id,
            )
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.rows(), [])

    def test_two_processes_create_one_original_proposal_without_effect(self):
        proposal_id = str(uuid4())
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(3)
        queue = ctx.Queue()
        workers = [
            ctx.Process(
                target=concurrent_proposal_worker,
                args=(
                    self.url,
                    str(self.identity.session_id),
                    proposal_id,
                    barrier,
                    queue,
                ),
            )
            for _ in range(2)
        ]
        try:
            for worker in workers:
                worker.start()
            barrier.wait(timeout=15)
            self.assertEqual(
                [queue.get(timeout=20), queue.get(timeout=20)],
                [proposal_id, proposal_id],
            )
            for worker in workers:
                worker.join(timeout=10)
                self.assertEqual(worker.exitcode, 0)
            with sessionmaker(self.engine)() as session:
                records = session.query(ConfirmationRecord).all()
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0].status, "pending")
                self.assertEqual(records[0].payload, {"value": "original"})
            self.assertEqual(self.rows(), [])
            self.ledger.decide(self.identity, proposal_id, True)
            self.assertEqual(self.rows(), ["original"])
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
            queue.close()
