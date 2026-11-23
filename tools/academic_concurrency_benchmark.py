"""Real HTTP + ADK + SQLite concurrency measurement; deterministic fake, no provider.
Run with the locked environment: python tools/academic_concurrency_benchmark.py --pairs 50 --output /tmp/aurora-benchmark.json
Only its own ephemeral port, child process and temporary databases are touched.
"""

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT),
    str(ROOT / "packages/aurora-toolkit/src"),
    str(ROOT / "packages/microservice-toolkit/src"),
]


def child(folder, fd):
    import logging
    import warnings

    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")

    def deny(*a, **k):
        raise AssertionError("No outbound network in benchmark")

    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.create_connection = deny
    import uvicorn
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    from services.agent.academic.api import create_app
    from services.agent.academic.domain import AcademicDomain

    class Fake(BaseLlm):
        model: str = "benchmark-structured-fake"
        role: str

        async def generate_content_async(self, request, stream=False):
            texts = [
                p.text
                for c in request.contents
                if c.role == "user"
                for p in c.parts or []
                if p.text and "<<<BEGIN_QUOTED_AGENT_CONTENT>>>" not in p.text
            ]
            command = json.loads(texts[-1])
            responses = [
                p.function_response
                for p in request.contents[-1].parts or []
                if p.function_response
            ]
            if self.role == "principal":
                part = types.Part(
                    function_call=types.FunctionCall(
                        name="transfer_to_agent", args={"agent_name": "reservas"}
                    )
                )
            elif responses:
                result = responses[-1].response
                if (
                    command.get("fail_after_commit")
                    and result.get("status") == "reserved"
                ):
                    raise RuntimeError("Synthetic provider failure after tool commit")
                part = types.Part(text=json.dumps(result))
            else:
                part = types.Part(
                    function_call=types.FunctionCall(
                        name="reservar_area",
                        args={"area": command["area"], "data": command["data"]},
                    )
                )
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

    domain = AcademicDomain(Path(folder) / "domain.db")
    app = create_app(
        domain=domain,
        session_url=f"sqlite+aiosqlite:///{folder}/sessions.db",
        models={r: Fake(role=r) for r in ("principal", "reservas", "convivencia")},
        regulation=(ROOT / "dados/regulamento.md").read_text(),
    )

    @app.middleware("http")
    async def measure_ingress(request, call_next):
        marker = request.headers.get("x-benchmark-id")
        start = time.monotonic_ns()
        response = await call_next(request)
        if marker:
            with (Path(folder) / "ingress.jsonl").open("a") as f:
                f.write(
                    json.dumps(
                        {
                            "id": marker,
                            "start_ns": start,
                            "end_ns": time.monotonic_ns(),
                            "http": response.status_code,
                        }
                    )
                    + "\n"
                )
        return response

    uvicorn.run(app, fd=int(fd), access_log=False, log_level="critical")


def classify(responses, committed, apartments, replay=False):
    success = [
        i
        for i, r in enumerate(responses)
        if r["http"] == 200 and (r["tool_result"] or {}).get("status") == "reserved"
    ]
    labels = []
    if len(committed) != 1:
        labels.append("no_effect" if not committed else "multiple_effects")
    if len(success) > 1:
        labels.append("both_success")
    if not success and committed:
        labels.append("no_success_but_committed")
    for i in success:
        if (
            len(committed) != 1
            or committed[0]["apartment"] != apartments[i]
            or committed[0]["code"] != responses[i]["tool_result"].get("codigo")
        ):
            labels.append("incorrect_winner")
    expected = [200, 409] if replay else [200, 200]
    if sorted(r["http"] for r in responses) != expected:
        labels.append("unexpected_http")
    if (
        not replay
        and len(success) == 1
        and (responses[1 - success[0]]["tool_result"] or {}).get("status") != "occupied"
    ):
        labels.append("incorrect_loser_response")
    return sorted(set(labels)) or ["consistent"]


def selftest_classifier():
    def response(code, status=None, reservation=None):
        return {
            "http": code,
            "tool_result": {"status": status, "codigo": reservation}
            if status
            else None,
        }

    win = response(200, "reserved", "A")
    lose = response(200, "occupied")
    fail = response(503)
    row = [{"code": "A", "apartment": "101"}]
    assert classify([win, lose], row, ["101", "201"]) == ["consistent"]
    assert "both_success" in classify(
        [win, response(200, "reserved", "B")], row, ["101", "201"]
    )
    assert "incorrect_winner" in classify(
        [response(200, "reserved", "WRONG"), lose], row, ["101", "201"]
    )
    assert "incorrect_winner" in classify(
        [win, lose], [{"code": "A", "apartment": "201"}], ["101", "201"]
    )
    assert {"no_effect", "unexpected_http"} <= set(
        classify([fail, fail], [], ["101", "201"])
    )
    assert {"no_success_but_committed", "unexpected_http"} <= set(
        classify([fail, fail], row, ["101", "201"])
    )
    assert classify([win, response(409)], row, ["101", "101"], replay=True) == [
        "consistent"
    ]
    return {"cases": 7, "status": "PASS"}


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    return round(values[min(len(values) - 1, int((len(values) - 1) * p))], 3)


def main(pairs, output):
    classifier_check = selftest_classifier()
    import httpx

    from services.agent.academic.domain import AcademicDomain

    with tempfile.TemporaryDirectory(prefix="aurora-concurrency-bench-") as tmp:
        folder = Path(tmp)
        AcademicDomain(folder / "domain.db").initialize(ROOT / "dados")
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        logfile = (folder / "server.log").open("w")
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
            env.pop(key, None)
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--child",
                tmp,
                str(listener.fileno()),
            ],
            pass_fds=(listener.fileno(),),
            cwd=ROOT,
            env=env,
            stdout=logfile,
            stderr=logfile,
        )
        c = httpx.Client(
            base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=100
        )
        samples = []
        negative = []
        serial = 0

        def session(apt):
            r = c.post("/sessoes", json={"apartamento": apt})
            assert r.status_code == 201, r.text
            return r.json()["session_id"]

        def propose(sid, day, fail=False):
            command = {
                "area": "salao-de-festas",
                "data": day,
                "fail_after_commit": fail,
            }
            r = c.post(f"/sessoes/{sid}/mensagens", json={"texto": json.dumps(command)})
            assert r.status_code == 200, r.text
            pending = r.json()["confirmacoes_pendentes"]
            assert len(pending) == 1, r.text
            return pending[0]["id"]

        def rows(day):
            with sqlite3.connect(folder / "domain.db") as db:
                return [
                    {"code": r[0], "apartment": r[1]}
                    for r in db.execute(
                        "SELECT code,apartment FROM reservations WHERE area=? AND day=? AND active=1",
                        ("salao-de-festas", day),
                    )
                ]

        def approve(sid, id, marker, barrier=None):
            if barrier:
                barrier.wait(timeout=10)
            start = time.monotonic_ns()
            r = c.post(
                f"/sessoes/{sid}/confirmacoes",
                json={"id": id, "confirmado": True},
                headers={"X-Benchmark-Id": marker},
            )
            elapsed = (time.monotonic_ns() - start) / 1e6
            body = r.json()
            result = None
            try:
                result = json.loads(body.get("resposta", ""))
            except (ValueError, TypeError):
                pass
            return {
                "http": r.status_code,
                "body": body,
                "tool_result": result,
                "client_start_ns": start,
                "latency_ms": elapsed,
            }

        try:
            for _ in range(200):
                if process.poll() is not None:
                    raise RuntimeError("Benchmark child exited")
                try:
                    if c.get("/docs", timeout=0.5).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Startup timeout")
            with ThreadPoolExecutor(2) as pool:
                for group in (
                    "different_apartments",
                    "same_apartment_distinct_requests",
                    "same_confirmation_replay",
                ):
                    for trial in range(pairs):
                        day = (date(2031, 1, 1) + timedelta(days=serial)).isoformat()
                        serial += 1
                        a1 = "101"
                        a2 = "201" if group == "different_apartments" else "101"
                        s1 = session(a1)
                        p1 = propose(s1, day)
                        if group == "same_confirmation_replay":
                            s2, p2 = s1, p1
                        else:
                            s2 = session(a2)
                            p2 = propose(s2, day)
                        assert rows(day) == []
                        marker = f"{group}:{trial}"
                        barrier = threading.Barrier(2)
                        futures = [
                            pool.submit(approve, s1, p1, marker + ":0", barrier),
                            pool.submit(approve, s2, p2, marker + ":1", barrier),
                        ]
                        responses = [f.result() for f in futures]
                        committed = rows(day)
                        labels = classify(
                            responses,
                            committed,
                            (a1, a2),
                            replay=group == "same_confirmation_replay",
                        )
                        samples.append(
                            {
                                "group": group,
                                "trial": trial,
                                "day": day,
                                "markers": [marker + ":0", marker + ":1"],
                                "labels": labels,
                                "committed": committed,
                                "responses": responses,
                            }
                        )
                    print(f"FINISHED {group}: {pairs} pairs", flush=True)
            # Separate characterization; not mixed into baseline failure rates.
            for i in range(5):
                day = (date(2031, 1, 1) + timedelta(days=serial)).isoformat()
                serial += 1
                sid = session("101")
                pending = propose(sid, day, True)
                result = approve(sid, pending, f"negative:{i}")
                replay = approve(sid, pending, f"negative-replay:{i}")
                with sqlite3.connect(folder / "domain.db") as db:
                    state = db.execute(
                        "SELECT status FROM academic_confirmations WHERE id=?",
                        (pending,),
                    ).fetchone()[0]
                negative.append(
                    {
                        "http": result["http"],
                        "committed_count": len(rows(day)),
                        "replay_http": replay["http"],
                        "confirmation_state": state,
                    }
                )
            ingress = {
                x["id"]: x
                for x in map(
                    json.loads, (folder / "ingress.jsonl").read_text().splitlines()
                )
            }
            summary = {}
            for group in sorted({s["group"] for s in samples}):
                trials = [s for s in samples if s["group"] == group]
                labels = Counter(label for s in trials for label in s["labels"])
                latencies = []
                gaps = []
                overlaps = 0
                for s in trials:
                    a, b = (ingress[m] for m in s["markers"])
                    gap = abs(a["start_ns"] - b["start_ns"]) / 1e6
                    overlap = max(a["start_ns"], b["start_ns"]) < min(
                        a["end_ns"], b["end_ns"]
                    )
                    overlaps += overlap
                    gaps.append(gap)
                    s["ingress_overlap"] = overlap
                    s["ingress_gap_ms"] = gap
                    latencies.extend(r["latency_ms"] for r in s["responses"])
                summary[group] = {
                    "pairs": len(trials),
                    "category_counts": dict(labels),
                    "category_rates": {
                        k: round(v / len(trials), 4) for k, v in labels.items()
                    },
                    "ingress_overlap_pairs": overlaps,
                    "latency_ms": {
                        "p50": percentile(latencies, 0.5),
                        "p95": percentile(latencies, 0.95),
                    },
                    "ingress_gap_ms": {
                        "p50": percentile(gaps, 0.5),
                        "p95": percentile(gaps, 0.95),
                    },
                }
            report = {
                "classifier_selftest": classifier_check,
                "throughput": "not measured; latency is concurrent approval request only, excludes setup/proposal",
                "model": "structured deterministic fake; no Gemini; no language-quality inference",
                "server_processes": 1,
                "port": port,
                "summary": summary,
                "negative_after_commit": negative,
                "samples": samples,
            }
            if output:
                Path(output).write_text(
                    json.dumps(report, ensure_ascii=False, indent=2)
                )
            print(
                json.dumps(
                    {k: v for k, v in report.items() if k != "samples"},
                    ensure_ascii=False,
                    indent=2,
                ),
                flush=True,
            )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            c.close()
            listener.close()
            logfile.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--pairs", type=int, default=50)
        parser.add_argument("--output", type=Path)
        args = parser.parse_args()
        if args.pairs < 1:
            parser.error("--pairs must be positive")
        main(args.pairs, args.output)
