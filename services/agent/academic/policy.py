"""Pure, opt-in policy evaluation; not enabled by the academic API by default.

Official profile covers only fixture areas/tariffs. Arts.36–40 do NOT specify a
reservation time window, blocked weekday, or three-business-day cancellation.
Synthetic examples are QA configuration, never claims about the regulation.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Mapping
from zoneinfo import ZoneInfo

Action = Literal["reserve", "cancel"]


@dataclass(frozen=True)
class Window:
    start: time
    end: time

    def __post_init__(self):
        if (
            not isinstance(self.start, time)
            or not isinstance(self.end, time)
            or self.start.tzinfo
            or self.end.tzinfo
            or self.end <= self.start
        ):
            raise ValueError("Windows must be increasing local times within one day.")


@dataclass(frozen=True)
class AreaPolicy:
    area: str
    fee_cents: int
    blocked_weekdays: frozenset[int] = frozenset()
    windows: tuple[Window, ...] = ()
    cancel_business_days: int | None = None
    source_articles: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            not isinstance(self.area, str)
            or not self.area.strip()
            or type(self.fee_cents) is not int
            or self.fee_cents < 0
        ):
            raise ValueError("Area and nonnegative integer tariff required.")
        if (
            not isinstance(self.blocked_weekdays, frozenset)
            or any(type(d) is not int for d in self.blocked_weekdays)
            or not self.blocked_weekdays <= frozenset(range(7))
        ):
            raise ValueError("Weekdays are immutable Monday=0 through Sunday=6.")
        if not isinstance(self.windows, tuple) or not all(
            isinstance(w, Window) for w in self.windows
        ):
            raise ValueError("Windows must be an immutable tuple.")
        if not isinstance(self.source_articles, tuple) or not all(
            isinstance(a, str) and a.strip() for a in self.source_articles
        ):
            raise ValueError(
                "Article IDs must be an immutable tuple of nonempty strings."
            )
        if self.cancel_business_days is not None and (
            type(self.cancel_business_days) is not int or self.cancel_business_days < 0
        ):
            raise ValueError(
                "Cancellation business days must be a nonnegative integer."
            )


@dataclass(frozen=True)
class Policy:
    version: str
    timezone: str
    areas: tuple[AreaPolicy, ...]
    holidays: frozenset[date] = frozenset()
    provenance: str = "explicit-configuration"

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("Policy version is required.")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("Policy provenance is required.")
        if not isinstance(self.timezone, str) or not self.timezone.strip():
            raise ValueError("Timezone is required.")
        ZoneInfo(self.timezone)
        if not isinstance(self.areas, tuple) or not all(
            isinstance(a, AreaPolicy) for a in self.areas
        ):
            raise ValueError("Areas must be an immutable tuple.")
        if len({a.area for a in self.areas}) != len(self.areas):
            raise ValueError("Duplicate area policy.")
        if not isinstance(self.holidays, frozenset) or not all(
            type(d) is date for d in self.holidays
        ):
            raise ValueError(
                "Supply explicit immutable holiday dates; no implicit national calendar."
            )


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    policy_version: str
    source_articles: tuple[str, ...]
    fee_cents: int
    requires_confirmation: bool
    provenance: str
    deadline: datetime | None = None


def _local(day: date, at: time, zone: ZoneInfo) -> datetime | None:
    """Fail closed on nonexistent/ambiguous local wall time, without guessing DST."""
    first = datetime.combine(day, at.replace(fold=0), zone)
    second = datetime.combine(day, at.replace(fold=1), zone)
    if first.utcoffset() != second.utcoffset():
        return None
    if first.astimezone(timezone.utc).astimezone(zone).replace(
        tzinfo=None
    ) != first.replace(tzinfo=None):
        return None
    return first


def evaluate(
    policy: Policy,
    action: Action,
    area: str,
    day: date,
    *,
    now: datetime,
    start: time | None = None,
    end: time | None = None,
    quote_version: str | None = None,
) -> Decision:
    """No I/O. Call inside the write transaction with its current policy snapshot.

    Window start is inclusive; closing is exclusive for a point, inclusive for
    an interval's end. A supplied interval must fit wholly inside ONE window.
    Synthetic cancellation deadline: same local start time N business dates
    before event date, excluding event date, weekends and explicit holidays.
    The exact deadline is allowed. Start is required if such a rule is enabled.
    """
    rule = next((r for r in policy.areas if r.area == area), None)

    def result(allowed, code, deadline=None):
        fee = rule.fee_cents if rule and action == "reserve" else 0
        return Decision(
            allowed,
            code,
            policy.version,
            rule.source_articles if rule else (),
            fee,
            allowed and action == "reserve" and fee > 0,
            policy.provenance,
            deadline,
        )

    if action not in ("reserve", "cancel"):
        return result(False, "invalid_action")
    if not rule:
        return result(False, "unknown_area")
    if type(day) is not date:
        return result(False, "invalid_date")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        return result(False, "invalid_clock")
    if quote_version is not None and quote_version != policy.version:
        return result(False, "stale_quote")
    if any(
        value is not None and (not isinstance(value, time) or value.tzinfo is not None)
        for value in (start, end)
    ):
        return result(False, "invalid_time")
    if end is not None and (start is None or end <= start):
        return result(False, "invalid_interval")
    zone = ZoneInfo(policy.timezone)
    if any(
        _local(day, value, zone) is None for value in (start, end) if value is not None
    ):
        return result(False, "ambiguous_or_nonexistent_local_time")
    if action == "reserve":
        if day.weekday() in rule.blocked_weekdays:
            return result(False, "blocked_weekday")
        if rule.windows:
            if start is None:
                return result(False, "time_required")
            if not any(
                window.start <= start < window.end
                and (end is None or end <= window.end)
                for window in rule.windows
            ):
                return result(False, "outside_window")
        return result(True, "allowed")
    if rule.cancel_business_days is not None:
        if start is None:
            return result(False, "time_required")
        cursor = day
        remaining = rule.cancel_business_days
        while remaining:
            cursor -= timedelta(days=1)
            if cursor.weekday() < 5 and cursor not in policy.holidays:
                remaining -= 1
        deadline = _local(cursor, start, zone)
        if deadline is None:
            return result(False, "ambiguous_or_nonexistent_local_time")
        if now.astimezone(zone) > deadline:
            return result(False, "cancel_deadline_passed", deadline)
        return result(True, "allowed", deadline)
    return result(True, "allowed")


def official_policy(
    tariffs: Mapping[str, int], *, version: str, timezone: str
) -> Policy:
    """Init-only definition from explicit fixture tariffs, not an enabled default.

    Input is integer cents. The caller loads dados/areas.json, converts exactly,
    and persists this version. No unsupported time/cancellation rule is inferred.
    """
    expected = {"salao-de-festas", "churrasqueira", "quadra"}
    if set(tariffs) != expected:
        raise ValueError("Official profile requires exactly the three fixture areas.")
    return Policy(
        version,
        timezone,
        tuple(
            AreaPolicy(area, tariffs[area], source_articles=("Art.36",))
            for area in sorted(expected)
        ),
        provenance="dados/areas.json + regulamento Art.36; tariff configuration supplied by caller",
    )


def synthetic_qa_policy(
    *,
    version: str = "qa-v1",
    timezone: str = "America/Sao_Paulo",
    holidays: frozenset[date] = frozenset(),
) -> Policy:
    """EXAMPLE ONLY: Monday closed, 08–22 window, cancellation 3 business dates ahead.

    These are synthetic QA rules, NOT rules of Residencial Aurora.
    """
    return Policy(
        version,
        timezone,
        (
            AreaPolicy(
                "salao-de-festas",
                15000,
                blocked_weekdays=frozenset({0}),
                windows=(Window(time(8), time(22)),),
                cancel_business_days=3,
            ),
        ),
        holidays=holidays,
        provenance="SYNTHETIC QA ONLY; not official regulation",
    )


def policy_to_dict(policy: Policy) -> dict:
    """JSON-safe complete definition; use sorted JSON keys when persisting/hashing."""
    return {
        "version": policy.version,
        "timezone": policy.timezone,
        "provenance": policy.provenance,
        "holidays": sorted(d.isoformat() for d in policy.holidays),
        "areas": [
            {
                "area": r.area,
                "fee_cents": r.fee_cents,
                "blocked_weekdays": sorted(r.blocked_weekdays),
                "windows": [
                    {"start": w.start.isoformat(), "end": w.end.isoformat()}
                    for w in r.windows
                ],
                "cancel_business_days": r.cancel_business_days,
                "source_articles": list(r.source_articles),
            }
            for r in policy.areas
        ],
    }


def policy_from_dict(value: dict) -> Policy:
    """Strict schema: no unknown keys, coercions, defaults or implicit holiday source."""

    def keys(obj, expected):
        if not isinstance(obj, dict) or set(obj) != set(expected):
            raise ValueError("Invalid policy object keys.")

    def string(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Expected nonempty string.")
        return value

    def array(value):
        if not isinstance(value, list):
            raise ValueError("Expected JSON array.")
        return value

    keys(value, ("version", "timezone", "provenance", "holidays", "areas"))
    areas = []
    for r in array(value["areas"]):
        keys(
            r,
            (
                "area",
                "fee_cents",
                "blocked_weekdays",
                "windows",
                "cancel_business_days",
                "source_articles",
            ),
        )
        days = array(r["blocked_weekdays"])
        if any(type(d) is not int or not 0 <= d <= 6 for d in days) or len(days) != len(
            set(days)
        ):
            raise ValueError("Invalid or duplicate weekday.")
        windows = []
        for w in array(r["windows"]):
            keys(w, ("start", "end"))
            windows.append(
                Window(
                    time.fromisoformat(string(w["start"])),
                    time.fromisoformat(string(w["end"])),
                )
            )
        areas.append(
            AreaPolicy(
                string(r["area"]),
                r["fee_cents"],
                frozenset(days),
                tuple(windows),
                r["cancel_business_days"],
                tuple(string(a) for a in array(r["source_articles"])),
            )
        )
    holidays = [date.fromisoformat(string(d)) for d in array(value["holidays"])]
    if len(holidays) != len(set(holidays)):
        raise ValueError("Duplicate holiday.")
    return Policy(
        string(value["version"]),
        string(value["timezone"]),
        tuple(areas),
        frozenset(holidays),
        string(value["provenance"]),
    )
