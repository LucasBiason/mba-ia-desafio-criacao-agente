"""Bootstrap explícito, liveness sem banco e preservação do contrato HTTP."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from google.adk.sessions import DatabaseSessionService
from sqlalchemy import event, inspect

from services.agent.api.api import create_app, prepare_domain_tables
from services.agent.api.domain import AcademicDomain

ROOT = Path(__file__).resolve().parents[3]


class AcademicBootstrapTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.domain = AcademicDomain(self.folder / "domain.db")
        self.apps = []

    async def asyncTearDown(self):
        for app in self.apps:
            await app.state.session_service.close()
        self.temp.cleanup()

    def app(self):
        app = create_app(
            domain=self.domain,
            session_url=f"sqlite+aiosqlite:///{self.folder}/sessions.db",
            models={},
            regulation="",
        )
        self.apps.append(app)
        return app

    async def test_cold_lifespan_health_and_openapi_do_not_open_databases(self):
        app = self.app()
        with patch.object(
            self.domain,
            "_engine",
            side_effect=AssertionError("No domain database access"),
        ):
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://academic"
                ) as client:
                    self.assertEqual((await client.get("/health")).status_code, 200)
                    response = await client.get("/openapi.json")
        self.assertEqual(list(self.folder.iterdir()), [])
        spec = response.json()
        paths = set(spec["paths"]) - {"/health"}
        self.assertEqual(
            paths,
            {
                "/sessoes",
                "/sessoes/{session_id}/mensagens",
                "/sessoes/{session_id}/confirmacoes",
                "/sessoes/{session_id}/eventos",
                "/apartamentos/{numero}/reservas",
                "/apartamentos/{numero}/visitantes",
            },
        )
        for path in (
            "/sessoes/{session_id}/mensagens",
            "/sessoes/{session_id}/confirmacoes",
        ):
            for code in ("404", "409", "429", "503"):
                self.assertEqual(
                    spec["paths"][path]["post"]["responses"][code]["content"][
                        "application/json"
                    ]["schema"]["$ref"],
                    "#/components/schemas/ErrorResponse",
                )

    async def test_first_http_operation_uses_prepared_schema_without_ddl(self):
        self.domain.initialize(ROOT / "dados")
        prepare_domain_tables(self.domain)
        prepared = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{self.folder}/sessions.db"
        )
        await prepared.prepare_tables()
        await prepared.close()
        for _ in range(2):
            app = self.app()
            statements = []
            event.listen(
                app.state.session_service.db_engine.sync_engine,
                "before_cursor_execute",
                lambda conn,
                cursor,
                statement,
                parameters,
                context,
                executemany: statements.append(statement),
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://academic"
            ) as client:
                response = await client.post("/sessoes", json={"apartamento": "101"})
                self.assertEqual(response.status_code, 201, response.text)
                events = await client.get(
                    "/sessoes/" + response.json()["session_id"] + "/eventos"
                )
                self.assertEqual(events.json(), [])
            self.assertFalse(
                any(
                    statement.lstrip()
                    .upper()
                    .startswith(("CREATE ", "ALTER ", "DROP "))
                    for statement in statements
                ),
                statements,
            )

    async def test_unprepared_session_database_fails_closed_without_creating_tables(
        self,
    ):
        self.domain.initialize(ROOT / "dados")
        prepare_domain_tables(self.domain)
        app = self.app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://academic"
        ) as client:
            response = await client.post("/sessoes", json={"apartamento": "101"})
        self.assertEqual(response.status_code, 503, response.text)
        async with app.state.session_service.db_engine.connect() as connection:
            tables = await connection.run_sync(
                lambda raw: inspect(raw).get_table_names()
            )
        self.assertEqual(tables, [])
