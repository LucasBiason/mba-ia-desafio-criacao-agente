"""Histórico ADK continua legível com o modelo desativado e sem DDL no HTTP."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import FastAPI
from google.adk.events import Event
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy import event

from services.agent.runtime.configuration import configure_from_environment


class HistoryOnlyConfigurationTest(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_adk_transcript_is_read_without_model_or_schema_writes(self):
        with TemporaryDirectory() as directory:
            url = "sqlite+aiosqlite:///" + str(Path(directory) / "history.db")
            bootstrap = DatabaseSessionService(db_url=url)
            session = await bootstrap.create_session(
                app_name="aurora_resident_actions",
                user_id="fixture-resident",
                session_id="legacy-storage",
                state={"apartment": "101"},
            )
            await bootstrap.append_event(
                session=session,
                event=Event(
                    author="user",
                    invocation_id="legacy-message",
                    content=types.Content(
                        role="user",
                        parts=[types.Part(text="Mensagem fictícia preservada.")],
                    ),
                ),
            )
            await bootstrap.close()

            class Configuration(dict):
                def get(self, key, default=None):
                    if key == "GOOGLE_API_KEY":
                        raise AssertionError(
                            "History-only must not inspect model credentials"
                        )
                    return super().get(key, default)

            app = FastAPI()
            settings = Configuration(
                AURORA_AGENT_ENABLED="0", AURORA_AGENT_SESSION_DATABASE_URL=url
            )
            with patch(
                "google.adk.models.google_llm.Gemini",
                side_effect=AssertionError("No model"),
            ):
                configure_from_environment(app, settings)
                service = app.state.agent_session_service
                ddl = []

                def capture(
                    connection, cursor, statement, parameters, context, executemany
                ):
                    if (
                        statement.lstrip()
                        .upper()
                        .startswith(("CREATE ", "ALTER ", "DROP "))
                    ):
                        ddl.append(statement)

                event.listen(
                    service.db_engine.sync_engine, "before_cursor_execute", capture
                )
                async with app.router.lifespan_context(app):
                    restored = await service.get_session(
                        app_name="aurora_resident_actions",
                        user_id="fixture-resident",
                        session_id=session.id,
                    )
                    self.assertIsNotNone(restored)
                    self.assertEqual(restored.state["apartment"], "101")
                    self.assertEqual(
                        restored.events[0].content.parts[0].text,
                        "Mensagem fictícia preservada.",
                    )
                    self.assertFalse(hasattr(app.state, "agent_message_handler"))
                    self.assertFalse(app.state.resident_actions_enabled)
                self.assertEqual(ddl, [])
