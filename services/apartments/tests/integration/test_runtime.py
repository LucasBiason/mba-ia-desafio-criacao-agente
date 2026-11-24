"""Exercise dependency failure and state preservation in the disposable QA stack."""

import os
import subprocess
from urllib.parse import urlsplit

import test_api as api_tests
from test_api import ROOT, URL, call


COMPOSE = (
    "docker",
    "compose",
    "--file",
    str(ROOT / "configs/compose.yaml"),
    "--env-file",
    os.environ.get("AURORA_ENV_FILE", str(ROOT / "configs/.env")),
    "-p",
    os.environ.get("COMPOSE_PROJECT_NAME", "residencial-aurora-qa"),
)
CONFIG = {**os.environ, "AURORA_PORT": str(urlsplit(URL).port or 8768)}


def compose(*command):
    subprocess.run(
        [*COMPOSE, *command],
        cwd=ROOT,
        env=CONFIG,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def get(path, token):
    status, payload = call(path, token=token)
    if status != 200:
        raise RuntimeError(f"Consulta de verificação retornou HTTP {status}.")
    return payload


def snapshot(admin, resident):
    return (
        get("/api/admin/regulation", admin),
        get("/api/admin/regulation/versions", admin),
        get("/api/admin/users", admin),
        get("/api/resident/reservations?apartment=101", resident),
        get("/api/resident/visits?apartment=101", resident),
        get("/api/resident/chat/sessions", resident),
        get("/api/admin/apartments", admin),
        get("/api/admin/reservations", admin),
        get("/api/admin/visits", admin),
    )


def main():
    target = urlsplit(URL)
    if target.scheme != "http" or target.hostname != "127.0.0.1" or not target.port:
        raise SystemExit(
            "Execute esta prova em uma instância descartável em 127.0.0.1."
        )
    port = subprocess.run(
        [*COMPOSE, "port", "web", "80"],
        cwd=ROOT,
        env=CONFIG,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if port != f"127.0.0.1:{target.port}":
        raise SystemExit("A porta verificada não pertence ao Compose de QA.")
    api_tests.AuroraBaseTest.setUpClass()
    admin, resident = api_tests.AuroraBaseTest.admin, api_tests.AuroraBaseTest.resident
    before = snapshot(admin, resident)
    if before[0]["version"] < 1 or not before[5]:
        raise SystemExit(
            "Rode services/apartments/tests/integration/test_api.py primeiro para preparar estado de teste."
        )
    try:
        compose("stop", "auth")
        for path in ("/api/admin/users", "/api/admin/areas"):
            status, _ = call(path, token=admin)
            if status != 503:
                raise RuntimeError(
                    f"Operação privada retornou HTTP {status} sem autenticação disponível."
                )
    finally:
        compose("up", "--wait", "auth")
    print(
        "Falha fechada: serviços privados retornaram 503 durante a parada de autenticação."
    )
    compose("stop")
    compose("up", "--wait")
    if snapshot(admin, resident) != before:
        raise RuntimeError("O estado de QA divergiu depois da nova subida.")
    print(
        "Persistência: contas, apartamentos, versões, agenda, visitas e sessão permaneceram após nova subida."
    )


if __name__ == "__main__":
    main()
