"""Offline-model multi-replica HTTP acceptance against an EXTERNALLY prepared fixture.

Does not start services, initialize/reset databases, or clean up effects. Requires an
explicit isolated-fixture acknowledgement. Never target host product/demo ports 8000/8793. Internal agent-a/b:8000 allowed.
Example (inside the isolated Compose network, or with published loopback ports):
 python tools/academic_postgres_acceptance.py --agent-a http://agent-a:8001 \
   --agent-b http://agent-b:8001 --load-balancer http://gateway:8080 \
   --pairs 40 --start-date 2035-01-01 --isolated-fixture \
   --output /tmp/academic-postgres-run.json
The fake must interpret JSON area/data and serialize tool results in resposta.
Projections are authoritative API reads, NOT direct SQL proof of PostgreSQL usage.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, timezone
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, quote
from urllib.request import Request, build_opener, ProxyHandler
import uuid


class Client:
    def __init__(self, base, timeout, run_id):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.run_id = run_id

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "X-Acceptance-Run": self.run_id,
            },
        )
        start = time.monotonic_ns()
        try:
            # No ambient proxy, shared cookie jar, or automatic POST retries.
            with build_opener(ProxyHandler({})).open(
                request, timeout=self.timeout
            ) as response:
                status, headers, raw = (
                    response.status,
                    response.headers,
                    response.read(),
                )
        except HTTPError as exc:
            status, headers, raw = exc.code, exc.headers, exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            return {
                "http": 0,
                "body": {"transport_error": type(exc).__name__},
                "replica": None,
                "start_ns": start,
                "end_ns": time.monotonic_ns(),
                "base": self.base,
            }
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError):
            payload = {"invalid_json": True}  # Do not copy arbitrary upstream HTML.
        return {
            "http": status,
            "body": payload,
            "replica": headers.get("X-Aurora-Replica"),
            "start_ns": start,
            "end_ns": time.monotonic_ns(),
            "base": self.base,
        }


def require(result, status):
    if result["http"] != status:
        raise RuntimeError(
            f"Expected HTTP {status}, got {result['http']} from {result['base']}"
        )
    return result["body"]


def result_tool(response):
    try:
        value = json.loads(response["body"]["resposta"])
        return value if isinstance(value, dict) else {}
    except (KeyError, TypeError, ValueError):
        return {}


def classify(responses, records, owners, replay=False):
    labels = []
    winners = [
        i
        for i, r in enumerate(responses)
        if r["http"] == 200 and result_tool(r).get("status") == "reserved"
    ]
    if len(records) != 1:
        labels.append("missing_effect" if not records else "multiple_effects")
    if len(winners) != 1:
        labels.append("missing_success" if not winners else "multiple_successes")
    for i in winners:
        tool = result_tool(responses[i])
        if (
            len(records) != 1
            or records[0]["apartment"] != owners[i]
            or records[0]["codigo"] != tool.get("codigo")
        ):
            labels.append("response_owner_or_code_mismatch")
    if len(responses) == 2:
        expected = [200, 409] if replay else [200, 200]
        if sorted(r["http"] for r in responses) != expected:
            labels.append("unexpected_http")
        if not replay and len(winners) == 1:
            if result_tool(responses[1 - winners[0]]).get("status") != "occupied":
                labels.append("incorrect_loser_response")
    elif responses[0]["http"] != 200:
        labels.append("unexpected_http")
    return sorted(set(labels)) or ["consistent"]


def selftest():
    win = {"http": 200, "body": {"resposta": '{"status":"reserved","codigo":"R1"}'}}
    lose = {"http": 200, "body": {"resposta": '{"status":"occupied"}'}}
    record = [{"apartment": "101", "codigo": "R1"}]
    assert classify([win, lose], record, ["101", "201"]) == ["consistent"]
    assert classify([win, {"http": 409}], record, ["101", "101"], True) == [
        "consistent"
    ]
    assert "multiple_successes" in classify([win, win], record, ["101", "101"])
    assert "response_owner_or_code_mismatch" in classify(
        [win, lose], record, ["201", "101"]
    )
    assert "multiple_effects" in classify([win, lose], record * 2, ["101", "201"])
    assert classify([win], record, ["101"]) == ["consistent"]
    return 6


def execute(args, report):
    clients = [
        Client(url, args.timeout, report["run_id"])
        for url in (args.agent_a, args.agent_b)
    ]
    owners_all = list(dict.fromkeys([args.unit_a, args.unit_b] + args.observe_unit))
    serial = 0

    def snapshot(day):
        all_views = []
        for client in clients:
            rows = []
            for owner in owners_all:
                body = require(
                    client.request(
                        "GET", f"/apartamentos/{quote(owner, safe='')}/reservas"
                    ),
                    200,
                )
                if not isinstance(body, list):
                    raise RuntimeError("Projection is not a JSON list")
                rows.extend(
                    dict(row, apartment=owner)
                    for row in body
                    if row.get("data") == day and row.get("area") == args.area
                )
            all_views.append(
                sorted(rows, key=lambda row: (row["apartment"], row["codigo"]))
            )
        return all_views

    def propose(client, owner, day):
        sid = require(client.request("POST", "/sessoes", {"apartamento": owner}), 201)[
            "session_id"
        ]
        command = json.dumps({"area": args.area, "data": day})
        body = require(
            client.request("POST", f"/sessoes/{sid}/mensagens", {"texto": command}), 200
        )
        pending = body["confirmacoes_pendentes"]
        if len(pending) != 1:
            raise RuntimeError("Expected exactly one pending confirmation")
        return sid, pending[0]["id"]

    def approve(client, item, barrier=None):
        if barrier:
            barrier.wait(timeout=10)
        sid, confirmation = item
        return client.request(
            "POST",
            f"/sessoes/{sid}/confirmacoes",
            {"id": confirmation, "confirmado": True},
        )

    probes = [
        require_replica(client.request("GET", "/openapi.json")) for client in clients
    ]
    if probes[0] == probes[1]:
        raise RuntimeError("Direct endpoints must identify distinct replicas")
    report["direct_replicas"] = probes
    with ThreadPoolExecutor(max_workers=2) as pool:
        for group in (
            "cross_replica_resume",
            "different_units_same_slot",
            "same_unit_distinct_requests",
            "same_confirmation_replay",
        ):
            for trial in range(args.pairs):
                day = (
                    date.fromisoformat(args.start_date) + timedelta(days=serial)
                ).isoformat()
                serial += 1
                sample = {"group": group, "trial": trial, "day": day}
                report["samples"].append(sample)
                before = snapshot(day)
                if any(before):
                    raise RuntimeError(
                        f"Nonempty slot {day}; use a clean fixture or unused date range"
                    )
                owners = [
                    args.unit_a,
                    args.unit_b
                    if group == "different_units_same_slot"
                    else args.unit_a,
                ]
                first = propose(clients[0], owners[0], day)
                if group == "cross_replica_resume":
                    responses = [approve(clients[1], first)]
                    expected_replicas = [probes[1]]
                else:
                    second = (
                        first
                        if group == "same_confirmation_replay"
                        else propose(clients[1], owners[1], day)
                    )
                    barrier = threading.Barrier(2)
                    futures = [
                        pool.submit(approve, client, item, barrier)
                        for client, item in zip(clients, (first, second))
                    ]
                    responses = [future.result() for future in futures]
                    expected_replicas = probes
                views = snapshot(day)
                labels = classify(
                    responses, views[0], owners, group == "same_confirmation_replay"
                )
                if views[0] != views[1]:
                    labels.append("replica_projection_disagreement")
                if [r["replica"] for r in responses] != expected_replicas:
                    labels.append("replica_header_mismatch")
                if len(labels) > 1 and "consistent" in labels:
                    labels.remove("consistent")
                sample.update(responses=responses, projections=views, labels=labels)
                if len(responses) == 2:
                    sample["client_request_overlap"] = max(
                        r["start_ns"] for r in responses
                    ) < min(r["end_ns"] for r in responses)
                print(
                    f"{group} {trial + 1}/{args.pairs}: {','.join(labels)}", flush=True
                )
    if args.load_balancer:
        lb = Client(args.load_balancer, args.timeout, report["run_id"])
        seen = [
            require_replica(lb.request("GET", "/openapi.json"))
            for _ in range(args.lb_requests)
        ]
        report["load_balancer"] = {
            "replicas": seen,
            "both_seen": set(seen) == set(probes),
            "alternating": all(a != b for a, b in zip(seen, seen[1:])),
        }
        # Strict alternation is a smoke diagnostic, not a universal LB guarantee.
        if set(seen) != set(probes):
            report["failures"].append(
                "load_balancer_did_not_reach_both_expected_replicas"
            )


def require_replica(response):
    require(response, 200)
    if not response["replica"]:
        raise RuntimeError(
            "Missing X-Aurora-Replica header; cannot establish replica identity"
        )
    return response["replica"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-a", required=True)
    parser.add_argument("--agent-b", required=True)
    parser.add_argument("--load-balancer")
    parser.add_argument("--pairs", type=int, default=40)
    parser.add_argument("--lb-requests", type=int, default=12)
    parser.add_argument("--unit-a", default="101")
    parser.add_argument("--unit-b", default="201")
    parser.add_argument("--observe-unit", action="append", default=[])
    parser.add_argument("--area", default="salao-de-festas")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--isolated-fixture", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.isolated_fixture:
        parser.error(
            "Explicit --isolated-fixture required; this writes synthetic reservations"
        )
    if (
        args.pairs < 1
        or args.lb_requests < 2
        or args.timeout <= 0
        or args.unit_a == args.unit_b
    ):
        parser.error("Invalid counts/timeout or identical unit IDs")
    try:
        date.fromisoformat(args.start_date)
        for url in (args.agent_a, args.agent_b, args.load_balancer):
            if not url:
                continue
            parsed = urlsplit(url)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or (
                    parsed.port == 8793
                    or (
                        parsed.port == 8000
                        and parsed.hostname not in ("agent-a", "agent-b")
                    )
                )
            ):
                raise ValueError("Invalid endpoint or forbidden product/demo port")
    except ValueError as exc:
        parser.error(str(exc))
    if args.agent_a.rstrip("/") == args.agent_b.rstrip("/"):
        parser.error("Two distinct direct URLs required")
    report = {
        "run_id": str(uuid.uuid4()),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        },
        "classifier_selftest_cases": selftest(),
        "samples": [],
        "failures": [],
        "scope": "Externally configured offline ADK fake; no seed/reset/cleanup/provider calls by this client. Projection verification covers configured observed units only. Client overlap is not proof of server overlap or database engine.",
    }
    # Reserve report before side effects; never overwrite a prior run.
    with args.output.open("x", encoding="utf-8") as output:
        try:
            execute(args, report)
        except Exception as exc:
            report["failures"].append(f"{type(exc).__name__}: {exc}")
        finally:
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report["categories"] = dict(
                Counter(
                    label
                    for s in report["samples"]
                    for label in s.get("labels", ["incomplete"])
                )
            )
            report["passed"] = not report["failures"] and set(report["categories"]) == {
                "consistent"
            }
            json.dump(report, output, ensure_ascii=False, indent=2)
            output.write("\n")
    print(
        json.dumps(
            {k: report[k] for k in ("run_id", "passed", "categories", "failures")}
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
