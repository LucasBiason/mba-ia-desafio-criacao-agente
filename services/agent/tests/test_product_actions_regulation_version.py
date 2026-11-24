"""Published revisions remain usable while confirmations bind to their version."""

import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.agent.confirmations.ledger import ConfirmationRecord
from services.agent.repositories import product_action_repository as module
from services.agent.runtime.resident_actions import ProductActions
from services.agent.tools.reservation_read import SessionIdentity
from services.parameters.models.regulation import Regulation


class ProductRegulationVersionTest(unittest.TestCase):
    def setUp(self):
        self.locks = []
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def lock_function(connection, _):
            connection.create_function(
                "pg_advisory_xact_lock_shared",
                1,
                lambda key: self.locks.append(key) or 1,
            )

        Regulation.__table__.create(self.engine)
        ConfirmationRecord.__table__.create(self.engine)
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE reservations (code TEXT,area_id TEXT,date DATE,status TEXT)"
                )
            )
            conn.execute(text("CREATE TABLE effects (action TEXT,apartment TEXT)"))
        self.sessions = sessionmaker(self.engine)

        @contextmanager
        def transaction():
            with self.sessions() as session, session.begin():
                yield session

        self.transaction = transaction
        self.identity = SessionIdentity(uuid4(), "resident-test")
        self.actions = ProductActions(self.identity)
        self.actions._actor = MagicMock()
        self.actions.repository._authorize = MagicMock(return_value="101")
        self.actions.repository._area = MagicMock(
            return_value=SimpleNamespace(id="salao-de-festas", fee_cents=15000)
        )
        self.enterContext(
            patch.object(
                module,
                "get_database",
                return_value=SimpleNamespace(
                    transaction=transaction, session=self.sessions
                ),
            )
        )
        for name, status in (
            ("reserve_effect", "reserved"),
            ("cancel_effect", "cancelled"),
            ("visit_effect", "authorized"),
        ):
            self.enterContext(
                patch.object(module, name, side_effect=self.effect(status))
            )

    @staticmethod
    def effect(status):
        def execute(session, payload):
            if not session.in_transaction():
                raise AssertionError("Effect must remain inside the ledger transaction")
            session.execute(
                text("INSERT INTO effects VALUES(:action,:apartment)"),
                {"action": status, "apartment": payload["apartment"]},
            )
            return {"status": status, "code": "RSV-synthetic"}

        return execute

    def publish(self, version, content="Texto vigente revisado pela administração."):
        with self.transaction() as session:
            session.add(Regulation(version=version, content=content))

    def proposal(self, action="reservar_area"):
        result = (
            self.actions.reserve("salao-de-festas", "2030-04-20")
            if action == "reservar_area"
            else self.actions.authorize_visit("Visitante fictício", "2030-04-21")
        )
        self.assertEqual(result, {"status": "pending"})
        with self.sessions() as session:
            row = session.scalar(
                select(ConfirmationRecord).where(ConfirmationRecord.action == action)
            )
            self.assertEqual(row.payload["regulation_version"], 8)
            self.assertEqual(row.payload["apartment"], "101")
            return row.id

    def effect_count(self):
        with self.engine.connect() as conn:
            return conn.scalar(text("SELECT count(*) FROM effects"))

    def test_nonzero_current_revision_uses_database_and_keeps_shared_lock(self):
        self.publish(0, "Edição inicial.")
        self.publish(8)
        with self.transaction() as session:
            self.assertEqual(module.current_version(session), 8)
        self.assertEqual(self.locks, [640202])

    def test_nonzero_revision_allows_free_paid_cancellation_and_visitor(self):
        self.publish(8)
        self.actions.repository._area.return_value = SimpleNamespace(
            id="quadra", fee_cents=0
        )
        self.assertEqual(
            self.actions.reserve("quadra", "2030-04-06")["status"], "reserved"
        )
        self.assertEqual(
            self.actions.cancel("quadra", "2030-04-06")["status"], "cancelled"
        )
        self.actions.repository._area.return_value = SimpleNamespace(
            id="salao-de-festas", fee_cents=15000
        )
        for action, expected in (
            ("reservar_area", "reserved"),
            ("autorizar_visitante", "authorized"),
        ):
            cid = self.proposal(action)
            self.assertEqual(self.effect_count(), 2 if action == "reservar_area" else 3)
            outcome = self.actions._ledger().decide(self.identity, cid, True)
            self.assertEqual(outcome["result"]["status"], expected)
            with self.assertRaises(HTTPException) as replay:
                self.actions._ledger().decide(self.identity, cid, True)
            self.assertEqual(replay.exception.status_code, 409)
        self.assertEqual(self.effect_count(), 4)

    def test_revision_changed_after_proposal_refuses_both_effects(self):
        self.publish(8)
        ids = [
            self.proposal(action) for action in ("reservar_area", "autorizar_visitante")
        ]
        self.publish(9, "Uma nova edição foi publicada após as propostas.")
        for cid in ids:
            result = self.actions._ledger().decide(self.identity, cid, True)
            self.assertEqual(result["result"], {"status": "policy_changed"})
        self.assertEqual(self.effect_count(), 0)

    def test_missing_regulation_fails_closed_for_every_write(self):
        for operation, args in (
            (self.actions.reserve, ("salao-de-festas", "2030-04-20")),
            (self.actions.cancel, ("salao-de-festas", "2030-04-20")),
            (self.actions.authorize_visit, ("Visitante fictício", "2030-04-21")),
        ):
            self.assertEqual(operation(*args), {"status": "policy_review_required"})
        self.assertEqual(self.effect_count(), 0)
        with self.sessions() as session:
            self.assertEqual(session.scalars(select(ConfirmationRecord)).all(), [])

    def test_invalid_revision_fails_closed(self):
        self.publish(-1)
        with self.transaction() as session:
            self.assertIsNone(module.current_version(session))
        self.publish(1, "   ")
        with self.transaction() as session:
            self.assertIsNone(module.current_version(session))

    def test_missing_regulation_after_proposal_refuses_effect(self):
        self.publish(8)
        cid = self.proposal()
        with self.transaction() as session:
            session.execute(text("DELETE FROM regulations"))
        result = self.actions._ledger().decide(self.identity, cid, True)
        self.assertEqual(result["result"], {"status": "policy_changed"})
        self.assertEqual(self.effect_count(), 0)


if __name__ == "__main__":
    unittest.main()
