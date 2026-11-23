"""Academic entrypoint: init before serve; SQLite locally or explicit Postgres."""

import argparse
import asyncio
from contextlib import asynccontextmanager
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROLES = ("principal", "reservas", "convivencia")


def _prepare_pg_sessions(session_url):
    from google.adk.sessions import DatabaseSessionService

    async def prepare():
        sessions = DatabaseSessionService(db_url=session_url)
        try:
            await sessions.prepare_tables()
        finally:
            await sessions.close()

    asyncio.run(prepare())


def main():
    parser = argparse.ArgumentParser(description="Aurora: avaliação acadêmica isolada")
    parser.add_argument(
        "command", choices=["init", "restore", "serve", "publish-policy"]
    )
    parser.add_argument("--data-dir", type=Path, default=Path(".aurora-academic"))
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    parser.add_argument("--policy-file", type=Path)
    parser.add_argument("--regulation-file", type=Path)
    parser.add_argument("--expected-version")
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
                "Configure AURORA_DOMAIN_DSN e AURORA_SESSION_DSN para o Postgres acadêmico."
            )
        if args.command == "restore":
            parser.error(
                "Postgres: use outro banco/volume explícito e rode init. Nenhum dado será apagado."
            )
        from services.agent.academic.postgres import PostgresAcademicDomain

        domain = PostgresAcademicDomain(domain_dsn)
        session_url = session_dsn
    else:
        from services.agent.academic.domain import AcademicDomain

        domain = AcademicDomain(folder / "domain.db")
        session_url = f"sqlite+aiosqlite:///{folder}/sessions.db"
        if args.host != "127.0.0.1":
            parser.error("A instância SQLite acadêmica aceita somente loopback.")

    use_policy = os.getenv("AURORA_POLICY_ENABLED") == "1"
    if use_policy or args.command == "publish-policy":
        from services.agent.academic.policy_store import PolicyStore

        domain.policy_store = PolicyStore(domain)
    if args.command == "publish-policy":
        if not args.policy_file or not args.regulation_file:
            parser.error("Informe --policy-file e --regulation-file revisados.")
        domain.policy_store.prepare()
        policy = json.loads(args.policy_file.read_text(encoding="utf-8"))
        with domain.connection() as conn:
            policies = policy.get("areas", ()) if isinstance(policy, dict) else ()
            if any(
                not isinstance(row, dict) or domain._area(conn, row.get("area")) is None
                for row in policies
            ):
                parser.error("O perfil só pode referenciar áreas cadastradas.")
        domain.policy_store.publish(
            version=policy["version"],
            payload=policy,
            regulation=args.regulation_file.read_text(encoding="utf-8"),
            expected_version=args.expected_version,
        )
        print("Política publicada: " + policy["version"])
        return

    if args.command in ("init", "restore"):
        if not postgres:
            if args.command == "restore" and folder.exists():
                parser.error(
                    "restore exige --data-dir NOVO e inexistente; banco anterior nunca é apagado."
                )
            folder.mkdir(parents=True, exist_ok=True)
        created = domain.initialize(ROOT / "dados")
        if use_policy:
            domain.policy_store.prepare()
        if postgres:
            from services.agent.academic.api import prepare_domain_tables

            prepare_domain_tables(domain)
            _prepare_pg_sessions(session_url)
        print(
            "Fixtures inicializadas em banco acadêmico novo."
            if created
            else "Banco já inicializado; dados preservados."
        )
        return

    if not postgres and not (folder / "domain.db").is_file():
        parser.error("Execute init antes de serve; nenhuma restauração implícita.")
    from importlib.metadata import version

    if version("google-adk") != "2.9.1":
        parser.error("Requer google-adk==2.9.1, execute uv sync --locked.")
    from services.agent.academic.api import create_app
    import uvicorn

    if os.getenv("AURORA_FAKE_MODEL") == "1":
        from services.agent.academic.fake import AcademicFakeModel

        models = {role: AcademicFakeModel(role=role) for role in ROLES}
        close_model = None
    else:
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

    if use_policy:
        with domain.connection() as conn:
            domain.policy_store.active(conn)
    regulation = (
        domain.policy_store.regulation
        if use_policy
        else (ROOT / "dados/regulamento.md").read_text(encoding="utf-8")
    )
    app = create_app(
        domain=domain,
        session_url=session_url,
        models=models,
        regulation=regulation,
        replica_id=os.getenv("AURORA_REPLICA_ID"),
    )
    if close_model:
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
