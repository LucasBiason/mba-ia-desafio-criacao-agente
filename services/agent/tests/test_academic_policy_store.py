"""Opt-in policy persistence/wiring; disposable SQLite only, no product/provider.

Time windows, Monday closure, holiday and cancellation deadline below are
SYNTHETIC QA configuration, not assertions about the official regulation.
"""

from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.agent.academic.domain import AcademicDomain
from services.agent.academic.policy import policy_to_dict, synthetic_qa_policy
from services.agent.academic.policy_store import PolicyStore

FIXTURES = Path(__file__).resolve().parents[3] / "dados"
AREA = "salao-de-festas"


class AcademicPolicyStoreTest(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(
            TemporaryDirectory(prefix="aurora-policy-store-test-")
        )
        self.domain = AcademicDomain(Path(folder) / "isolated.db")
        self.domain.initialize(FIXTURES)
        self.store = PolicyStore(self.domain)
        self.store.prepare()
        self.domain.policy_store = self.store
        self.domain.policy_now = lambda: datetime(2030, 3, 1, tzinfo=timezone.utc)
        self.bound = self.domain.tools("101")

    def publish(self, version="qa-v1", expected=None, text=None):
        payload = policy_to_dict(
            synthetic_qa_policy(
                version=version, holidays=frozenset({date(2030, 3, 14)})
            )
        )
        self.store.publish(
            version=version,
            payload=payload,
            regulation=text or f"SYNTHETIC QA text {version}",
            expected_version=expected,
        )
        return payload

    def proposal(self, day="2030-03-15", start="10:00", end="11:00"):
        return self.bound.reservar_area(
            AREA, day, operation_id="proposal", start=start, end=end
        )

    def reserve(self, day="2030-03-15"):
        proposal = self.proposal(day)
        self.assertEqual(proposal["status"], "confirmation_required")
        result = self.domain.apply_confirmed(
            "101", "reservar_area", proposal["detalhes"], operation_id="approve-" + day
        )
        self.assertEqual(result["status"], "reserved")
        return result

    def active_for(self, day):
        with self.domain.connection() as conn:
            return conn.execute(
                "SELECT count(*) FROM reservations WHERE area=? AND day=? AND active=1",
                (AREA, day),
            ).fetchone()[0]

    def test_versioned_current_text_preserves_immutable_revision_and_hash(self):
        first = self.publish(text="SYNTHETIC first text")
        self.assertEqual(self.store.regulation(), "SYNTHETIC first text")
        self.publish("qa-v2", "qa-v1", "SYNTHETIC second text")
        reopened = PolicyStore(self.domain)
        reopened.prepare()  # Idempotent preparation must not reset the head.
        self.assertEqual(reopened.regulation(), "SYNTHETIC second text")
        with self.domain.connection() as conn:
            active = reopened.active(conn)
            old = conn.execute(
                "SELECT * FROM academic_policy_revisions WHERE version=?", ("qa-v1",)
            ).fetchone()
        self.assertEqual(active.version, "qa-v2")
        self.assertEqual(json.loads(old["payload"]), first)
        self.assertEqual(old["regulation"], "SYNTHETIC first text")
        self.assertEqual(
            old["source_sha256"], sha256(b"SYNTHETIC first text").hexdigest()
        )
        self.assertIsNotNone(datetime.fromisoformat(old["published_at"]).tzinfo)

    def test_optimistic_publish_conflict_has_no_partial_revision(self):
        self.publish()
        self.publish("qa-v2", "qa-v1")
        with self.assertRaises(ValueError):
            self.publish("qa-v3", "qa-v1")
        with self.domain.connection() as conn:
            self.assertEqual(self.store.active(conn).version, "qa-v2")
            self.assertIsNone(
                conn.execute(
                    "SELECT version FROM academic_policy_revisions WHERE version=?",
                    ("qa-v3",),
                ).fetchone()
            )
        with self.assertRaises(ValueError):
            self.publish("qa-v1", "qa-v2", "replacement is forbidden")

    def test_unpublished_optional_profile_fails_closed(self):
        with self.assertRaises(ValueError):
            self.store.regulation()
        self.assertEqual(self.proposal()["status"], "invalid_policy_input")
        self.assertEqual(self.active_for("2030-03-15"), 0)

    def test_paid_v1_proposal_then_v2_publish_rejects_without_effect(self):
        self.publish()
        proposal = self.proposal()
        self.assertEqual(proposal["detalhes"]["policy_version"], "qa-v1")
        self.assertEqual(proposal["detalhes"]["taxa"], 150)
        self.assertEqual(self.active_for("2030-03-15"), 0)
        self.publish("qa-v2", "qa-v1")
        result = self.domain.apply_confirmed(
            "101", "reservar_area", proposal["detalhes"], operation_id="stale-approval"
        )
        self.assertEqual(result["status"], "policy_changed")
        self.assertEqual(result["reason"], "stale_quote")
        self.assertEqual(result["policy_version"], "qa-v2")
        self.assertEqual(self.active_for("2030-03-15"), 0)
        with self.domain.connection() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT count(*) FROM academic_reservation_policy"
                ).fetchone()[0],
                0,
            )

    def test_weekday_and_hour_boundaries_through_bound_domain(self):
        self.publish()
        cases = [
            ("2030-03-11", "10:00", "11:00", "blocked_weekday"),
            ("2030-03-12", "07:59", "08:30", "outside_window"),
            ("2030-03-12", "08:00", "22:00", None),
            ("2030-03-12", "21:59", "22:00", None),
            ("2030-03-12", "22:00", None, "outside_window"),
            ("2030-03-12", "21:00", "22:01", "outside_window"),
            ("2030-03-12", None, None, "time_required"),
        ]
        for day, start, end, reason in cases:
            with self.subTest(day=day, start=start, end=end):
                result = self.proposal(day, start, end)
                if reason:
                    self.assertEqual(result["status"], "policy_denied")
                    self.assertEqual(result["reason"], reason)
                else:
                    self.assertEqual(result["status"], "confirmation_required")
        self.assertEqual(self.active_for("2030-03-12"), 0)

    def test_local_time_persisted_and_cancel_exact_three_business_day_deadline(self):
        self.publish()
        booking = self.reserve()
        with self.domain.connection() as conn:
            saved = conn.execute(
                "SELECT * FROM academic_reservation_policy WHERE code=?",
                (booking["codigo"],),
            ).fetchone()
        self.assertEqual(
            (saved["version"], saved["start_time"], saved["end_time"]),
            ("qa-v1", "10:00", "11:00"),
        )
        # Friday 15: Thu14 holiday; Wed13, Tue12, Mon11 = 3 business dates.
        # Stored 10:00 Sao Paulo = 13:00 UTC. Exact boundary remains permitted.
        self.domain.policy_now = lambda: datetime(
            2030, 3, 11, 13, 0, tzinfo=timezone.utc
        )
        result = self.bound.cancelar_reserva(
            AREA, "2030-03-15", operation_id="cancel-boundary"
        )
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.active_for("2030-03-15"), 0)

    def test_one_second_after_holiday_adjusted_deadline_denies_without_effect(self):
        self.publish()
        self.reserve()
        self.domain.policy_now = lambda: datetime(
            2030, 3, 11, 13, 0, 1, tzinfo=timezone.utc
        )
        result = self.bound.cancelar_reserva(
            AREA, "2030-03-15", operation_id="late-cancel"
        )
        self.assertEqual(result["status"], "policy_denied")
        self.assertEqual(result["reason"], "cancel_deadline_passed")
        self.assertEqual(self.active_for("2030-03-15"), 1)

    def test_optional_profile_does_not_enable_itself_on_new_domain(self):
        self.publish()
        fresh = AcademicDomain(self.domain.path)
        self.assertIsNone(fresh.policy_store)
        legacy = fresh.tools("101")
        # Monday restriction exists only in the explicit synthetic profile.
        proposal = legacy.reservar_area(AREA, "2030-03-11", operation_id="legacy")
        self.assertEqual(proposal["status"], "confirmation_required")
        self.assertNotIn("policy_version", proposal["detalhes"])
        self.assertEqual(
            legacy.reservar_area(
                AREA, "2030-03-12", operation_id="legacy-time", start="10:00"
            )["status"],
            "time_not_supported",
        )


if __name__ == "__main__":
    unittest.main()
