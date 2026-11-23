"""Laboratório de transporte SSE: não usa ADK, Gemini, banco nem portal."""

import argparse
import asyncio
import json
import socket
import threading
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class ProbeRequest(BaseModel):
    stream: bool = True
    fail: bool = False


def frame(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def create_probe(delay: float) -> FastAPI:
    app = FastAPI(title="Aurora: prova isolada de transporte SSE")
    app.state.disconnected = threading.Event()

    @app.post("/ask/probe")
    async def probe(payload: ProbeRequest):
        if not payload.stream:
            return {"resposta": "Resposta sintética.", "modo": "json"}

        async def events():
            terminal = False
            try:
                yield frame("progress", {"stage": "retrieving"})
                await asyncio.sleep(delay)
                yield ": heartbeat\n\n"
                await asyncio.sleep(delay)
                if payload.fail:
                    terminal = True
                    yield frame("error", {"code": "synthetic_upstream_failure"})
                    return
                yield frame("delta", {"text": "Resposta "})
                await asyncio.sleep(delay)
                yield frame("delta", {"text": "sintética."})
                terminal = True
                yield frame("done", {"mode": "read_only"})
            finally:
                if not terminal:
                    app.state.disconnected.set()

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def self_test(delay=0.2):
    import httpx
    import uvicorn

    app = create_probe(delay)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(
            uvicorn.Config(app, access_log=False, log_level="error")
        )
        thread = threading.Thread(
            target=server.run, kwargs={"sockets": [sock]}, daemon=True
        )
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        thread.start()
        try:
            for _ in range(200):
                if server.started:
                    break
                if not thread.is_alive():
                    raise RuntimeError("Não foi possível iniciar a prova.")
                time.sleep(0.02)
            else:
                raise TimeoutError("Servidor didático não iniciou.")

            with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:

                def collect(fail=False):
                    started = time.monotonic()
                    observed = {}
                    with client.stream(
                        "POST", "/ask/probe", json={"fail": fail}
                    ) as response:
                        assert response.status_code == 200
                        assert response.headers["content-type"].startswith(
                            "text/event-stream"
                        )
                        for line in response.iter_lines():
                            if line.startswith("event: "):
                                observed.setdefault(
                                    line[7:], time.monotonic() - started
                                )
                            elif line.startswith(": heartbeat"):
                                observed["heartbeat"] = time.monotonic() - started
                    return observed

                ok = collect()
                assert list(ok) == ["progress", "heartbeat", "delta", "done"]
                assert ok["delta"] - ok["progress"] >= delay
                assert ok["done"] > ok["delta"]
                fail = collect(fail=True)
                assert list(fail) == ["progress", "heartbeat", "error"]
                response = client.post("/ask/probe", json={"stream": False})
                assert response.status_code == 200 and response.json()["modo"] == "json"
                with client.stream("POST", "/ask/probe", json={}) as response:
                    assert next(response.iter_lines()) == "event: progress"
                assert app.state.disconnected.wait(timeout=2)
                print(
                    json.dumps(
                        {
                            "progress_ms": round(ok["progress"] * 1000),
                            "primeiro_delta_ms": round(ok["delta"] * 1000),
                            "done_ms": round(ok["done"] * 1000),
                            "erro_terminal": "PASS",
                            "fallback_json": "PASS",
                            "desconexao_cancela_gerador": "PASS",
                        },
                        ensure_ascii=False,
                    )
                )
        finally:
            server.should_exit = True
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Inicia apenas a prova local, porta 8811 por padrão.",
    )
    parser.add_argument("--port", type=int, default=8811)
    args = parser.parse_args()
    if args.serve:
        import uvicorn

        uvicorn.run(create_probe(1.0), host="127.0.0.1", port=args.port)
    else:
        self_test()
