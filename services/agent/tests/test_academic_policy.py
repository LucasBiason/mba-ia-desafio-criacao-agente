import unittest
from datetime import date, datetime, time, timezone
from dataclasses import replace
from services.agent.academic.policy import (
    Policy,
    AreaPolicy,
    Window,
    evaluate,
    official_policy,
    synthetic_qa_policy,
)


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.official = official_policy(
            {"salao-de-festas": 15000, "churrasqueira": 8000, "quadra": 0},
            version="official-v1",
            timezone="America/Sao_Paulo",
        )
        self.now = datetime(2030, 4, 1, 12, tzinfo=timezone.utc)

    def check(
        self,
        p=None,
        action="reserve",
        area="salao-de-festas",
        day=date(2030, 4, 9),
        **kwargs,
    ):
        return evaluate(
            p or self.official,
            action,
            area,
            day,
            now=kwargs.pop("now", self.now),
            **kwargs,
        )

    def test_official_only_actual_tariffs_no_invented_time_or_cancel_rule(self):
        decision = self.check(
            day=date(2030, 4, 8), start=time(23)
        )  # Monday late is not a reservation ban in Art.36.
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.fee_cents, 15000)
        self.assertTrue(decision.requires_confirmation)
        self.assertEqual(decision.source_articles, ("Art.36",))
        self.assertTrue(self.check(action="cancel", day=date(2030, 4, 1)).allowed)
        self.assertFalse(self.check(area="quadra").requires_confirmation)
        self.assertEqual(self.check(area="piscina").code, "unknown_area")

    def test_synthetic_blocked_weekday_and_boundary_window(self):
        p = synthetic_qa_policy()
        self.assertEqual(
            self.check(p, day=date(2030, 4, 8), start=time(10)).code, "blocked_weekday"
        )
        self.assertEqual(self.check(p).code, "time_required")
        self.assertTrue(self.check(p, start=time(8), end=time(22)).allowed)
        self.assertFalse(self.check(p, start=time(22)).allowed)
        self.assertFalse(self.check(p, start=time(7, 59)).allowed)
        self.assertFalse(self.check(p, start=time(21), end=time(22, 1)).allowed)
        self.assertIn("SYNTHETIC", self.check(p, start=time(10)).provenance)

    def test_optional_end_and_invalid_intervals(self):
        self.assertTrue(self.check(synthetic_qa_policy(), start=time(10)).allowed)
        self.assertEqual(self.check(end=time(10)).code, "invalid_interval")
        self.assertEqual(
            self.check(start=time(23), end=time(1)).code, "invalid_interval"
        )
        self.assertEqual(
            self.check(start=time(10), end=time(10)).code, "invalid_interval"
        )

    def test_business_days_weekend_holiday_and_exact_deadline(self):
        # Event Mon Apr8: previous Thu4, Wed3, Tue2 when Fri5 is a supplied holiday.
        p = synthetic_qa_policy(holidays=frozenset({date(2030, 4, 5)}))
        exact = datetime(2030, 4, 2, 13, tzinfo=timezone.utc)  # 10:00 Sao Paulo
        result = self.check(
            p, action="cancel", day=date(2030, 4, 8), start=time(10), now=exact
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.deadline.date(), date(2030, 4, 2))
        late = exact.replace(second=1)
        self.assertEqual(
            self.check(
                p, action="cancel", day=date(2030, 4, 8), start=time(10), now=late
            ).code,
            "cancel_deadline_passed",
        )
        self.assertEqual(self.check(p, action="cancel").code, "time_required")

    def test_quote_version_and_tariff_change(self):
        self.assertTrue(self.check(quote_version="official-v1").allowed)
        new = replace(self.official, version="official-v2")
        self.assertEqual(
            self.check(new, quote_version="official-v1").code, "stale_quote"
        )
        self.assertEqual(self.check(new).policy_version, "official-v2")

    def test_clock_date_and_dst_fail_closed(self):
        self.assertEqual(self.check(now=datetime(2030, 4, 1)).code, "invalid_clock")
        self.assertEqual(self.check(day="2030-04-09").code, "invalid_date")
        p = replace(self.official, timezone="America/New_York")
        self.assertEqual(
            self.check(p, day=date(2030, 3, 10), start=time(2, 30)).code,
            "ambiguous_or_nonexistent_local_time",
        )
        self.assertEqual(
            self.check(p, day=date(2030, 11, 3), start=time(1, 30)).code,
            "ambiguous_or_nonexistent_local_time",
        )

    def test_no_window_gap_is_implicitly_allowed(self):
        p = Policy(
            "split",
            "UTC",
            (
                AreaPolicy(
                    "salao-de-festas",
                    0,
                    windows=(Window(time(8), time(12)), Window(time(14), time(18))),
                ),
            ),
        )
        self.assertFalse(self.check(p, start=time(11), end=time(15)).allowed)
        self.assertTrue(self.check(p, start=time(14), end=time(18)).allowed)

    def test_invalid_policy_configuration(self):
        for fee in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                AreaPolicy("x", fee)
        with self.assertRaises(ValueError):
            Window(time(22), time(8))
        with self.assertRaises(ValueError):
            AreaPolicy("x", 0, cancel_business_days=-1)
        with self.assertRaises(ValueError):
            official_policy({"piscina": 0}, version="v", timezone="UTC")

    def test_strict_serialization_roundtrip_and_no_silent_coercion(self):
        import copy
        from services.agent.academic.policy import policy_to_dict, policy_from_dict

        for policy in (
            self.official,
            synthetic_qa_policy(holidays=frozenset({date(2030, 4, 5)})),
        ):
            self.assertEqual(policy_from_dict(policy_to_dict(policy)), policy)
        original = policy_to_dict(self.official)
        mutated = []
        x = copy.deepcopy(original)
        x["surprise"] = True
        mutated.append(x)
        x = copy.deepcopy(original)
        del x["timezone"]
        mutated.append(x)
        x = copy.deepcopy(original)
        x["areas"][0]["fee_cents"] = "15000"
        mutated.append(x)
        x = copy.deepcopy(original)
        x["areas"][0]["blocked_weekdays"] = [True]
        mutated.append(x)
        x = copy.deepcopy(original)
        x["areas"][0]["blocked_weekdays"] = [1, 1]
        mutated.append(x)
        x = copy.deepcopy(original)
        x["areas"][0]["windows"] = [{"start": "08:00", "end": "22:00", "extra": 0}]
        mutated.append(x)
        for value in mutated:
            with self.assertRaises(ValueError):
                policy_from_dict(value)
