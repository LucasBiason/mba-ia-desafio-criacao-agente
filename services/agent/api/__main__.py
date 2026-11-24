"""Aurora agent API entrypoint: explicit persistence and Gemini through ADK."""

import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROLES = ("principal", "reservas", "convivencia")


def main():
    parser = argparse.ArgumentParser(
        description="Aurora: API do assistente dos moradores"
    )
    parser.add_argument("command", choices=["init", "restore", "serve"])
    parser.add_argument("--data-dir", type=Path, default=Path("/tmp/aurora-agent-data"))
    parser.add_argument(
        "--confirm-restore",
        action="store_true",
        help="Confirma reset explícito do banco do agente; pare todas as APIs antes.",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    args = parser.parse_args()
    folder = args.data_dir.resolve()
    domain_dsn = os.getenv("AURORA_DOMAIN_DSN", "")
    session_dsn = os.getenv("AURORA_SESSION_DSN", "")
    postgres = bool(domain_dsn or session_dsn)
    if postgres:
        if not domain_dsn.startswith("postgresql://") or not session_dsn.startswith(
            "postgresql+psycopg://"
        ):
            parser.error(
                "Configure AURORA_DOMAIN_DSN e AURORA_SESSION_DSN para o Postgres do agente."
            )
        from services.agent.api.postgres import PostgresAcademicDomain

        domain = PostgresAcademicDomain(domain_dsn)
        session_url = session_dsn
    else:
        from services.agent.api.domain import AcademicDomain

        domain = AcademicDomain(folder / "domain.db")
        session_url = f"sqlite+aiosqlite:///{folder}/sessions.db"
        if args.host != "127.0.0.1":
            parser.error("A instância SQLite do agente aceita somente loopback.")

    if args.command == "restore":
        if not args.confirm_restore:
            parser.error(
                "Pare todas as APIs e informe --confirm-restore para restaurar este banco do agente."
            )
        snapshot_id = domain.restore(ROOT / "dados")
        print(
            "Dados iniciais restaurados; sessões anteriores invalidadas. Snapshot: "
            + snapshot_id
        )
        return

    if args.command == "init":
        if not postgres:
            folder.mkdir(parents=True, exist_ok=True)
        created = domain.initialize(ROOT / "dados")
        from services.agent.api.api import prepare_domain_tables

        prepare_domain_tables(domain)
        from services.agent.bootstrap import initialize_sessions

        initialize_sessions(session_url)
        print(
            "Fixtures inicializadas em banco do agente novo."
            if created
            else "Banco já inicializado; dados preservados."
        )
        return

    if not postgres and not (folder / "domain.db").is_file():
        parser.error("Execute init antes de serve; nenhuma restauração implícita.")
    from importlib.metadata import version

    if version("google-adk") != "2.14.1":
        parser.error("Requer google-adk==2.14.1, execute uv sync --locked.")
    import uvicorn

    from services.agent.api.api import create_app

    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        parser.error(
            "Defina GOOGLE_API_KEY no ambiente; não será lida de arquivo automaticamente."
        )
    model_name = os.getenv("AURORA_MODEL") or "gemini-3.5-flash-lite"
    if not model_name.startswith("gemini-") or "/" in model_name:
        parser.error("AURORA_MODEL deve identificar um Gemini AI Studio.")
    from google.adk.models.google_llm import Gemini
    from google.genai import types

    from services.agent.runtime.provider_transport import (
        AI_STUDIO_BASE_URL,
        create_provider_clients,
        provider_ssl_context,
    )

    context = provider_ssl_context()
    sync_client, async_client = create_provider_clients()
    model = Gemini(
        model=model_name,
        base_url=AI_STUDIO_BASE_URL,
        client_kwargs={
            "api_key": key,
            "vertexai": False,
            "http_options": types.HttpOptions(
                base_url=AI_STUDIO_BASE_URL,
                timeout=20000,
                retry_options=types.HttpRetryOptions(attempts=1),
                httpx_client=sync_client,
                httpx_async_client=async_client,
                client_args={"verify": context, "trust_env": False},
                async_client_args={
                    "verify": context,
                    "ssl": context,
                    "trust_env": False,
                },
            ),
        },
    )
    del key
    models = dict.fromkeys(ROLES, model)

    async def close_model():
        await async_client.aclose()
        sync_client.close()

    regulation = (ROOT / "dados/regulamento.md").read_text(encoding="utf-8")
    app = create_app(
        domain=domain,
        session_url=session_url,
        models=models,
        regulation=regulation,
        replica_id=os.getenv("AURORA_REPLICA_ID"),
    )
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        try:
            async with original(application):
                yield
        finally:
            await close_model()

    app.router.lifespan_context = lifespan

    # Compose binds to all interfaces only inside the container; its published
    # host port is loopback-only because the academic routes have no authentication.
    # SQLite coordinates turns in one process; PostgreSQL scales by container.
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, workers=1)


if __name__ == "__main__":
    main()
