import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from google.genai import types
from services.agent.runtime.portal_history import public_events
from services.agent.controllers.chat_controller import ChatController


class PortalHistoryTest(unittest.TestCase):
    def test_projection_excludes_tools_thought_and_nonfinal(self):
        def event(author, parts, final=True, identity="1"):
            return SimpleNamespace(
                id=identity,
                author=author,
                timestamp=1,
                content=types.Content(
                    role="model" if author != "user" else "user", parts=parts
                ),
                is_final_response=lambda: final,
            )

        events = [
            event("user", [types.Part(text="Pergunta")]),
            event(
                "agent",
                [
                    types.Part(text="raciocinio", thought=True),
                    types.Part(text="Resposta"),
                ],
            ),
            event(
                "agent",
                [
                    types.Part(
                        function_response=types.FunctionResponse(
                            name="private", response={"private": "data"}
                        )
                    )
                ],
            ),
            event("agent", [types.Part(text="internal")], False),
        ]
        self.assertEqual(
            [r["content"] for r in public_events(events)], ["Pergunta", "Resposta"]
        )

    def test_legacy_receipts_are_allowlisted_without_raw_payload(self):
        event = SimpleNamespace(
            id="receipt",
            author="reservas",
            timestamp=1,
            content=types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name="reservar_area",
                            response={
                                "status": "reserved",
                                "code": "RSV-123",
                                "private": "secret",
                            },
                        )
                    )
                ],
            ),
            is_final_response=lambda: True,
        )
        rows = public_events([event])
        self.assertEqual(rows[0]["content"], "Reserva gravada. Código: RSV-123.")
        self.assertNotIn("secret", str(rows))
        event.content.role = "model"
        self.assertEqual(public_events([event]), [])

    def test_create_returns_oldest_owned_session_without_deleting_legacy(self):
        repo = MagicMock()
        repo.__enter__.return_value = repo
        first = SimpleNamespace(
            id="1",
            apartment="101",
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        last = SimpleNamespace(
            id="2",
            apartment="101",
            created_at=datetime(2021, 1, 1, tzinfo=timezone.utc),
        )
        repo.list.return_value = [last, first]
        with (
            patch(
                "services.agent.controllers.chat_controller.ChatRepository",
                return_value=repo,
            ),
            patch(
                "services.agent.controllers.chat_controller.ChatValidator"
            ) as validator,
            patch(
                "services.agent.controllers.chat_controller.ChatSerializer.serialize",
                side_effect=lambda x: x,
            ),
        ):
            result = ChatController().create(
                SimpleNamespace(apartment="101"), {"id": "resident"}
            )
        self.assertIs(result, first)
        validator.return_value.validate_create.assert_called_once()
        repo.create.assert_not_called()


class StoredHistoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_archive_restore_pagination_and_authoritative_text(self):
        from contextlib import contextmanager
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import Session
        from sqlalchemy.pool import StaticPool
        from services.agent.runtime import portal_history as module

        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(engine, "connect")
        def functions(connection, record):
            connection.create_function("pg_advisory_xact_lock", 1, lambda _: 1)

        module.PortalMessage.__table__.create(engine)
        module.PortalArchive.__table__.create(engine)

        @contextmanager
        def transaction():
            with Session(engine) as session, session.begin():
                yield session

        database = SimpleNamespace(transaction=transaction)
        actor = {"id": "owner"}
        with (
            patch.object(module, "get_database", return_value=database),
            patch.object(module, "scope", return_value=("101", ["s1", "legacy"])),
        ):
            module.append_message("legacy", "user", "Anterior")
            module.append_message("s1", "assistant", "Reserva gravada. Código: REAL.")
            page = await module.history("s1", actor, None, limit=1)
            self.assertEqual(
                page["messages"][0]["content"], "Reserva gravada. Código: REAL."
            )
            older = await module.history(
                "s1", actor, None, limit=1, before=page["next_cursor"]
            )
            self.assertEqual(older["messages"][0]["content"], "Anterior")
            module.archive("s1", actor)
            self.assertEqual((await module.history("s1", actor, None))["messages"], [])
            module.append_message("s1", "user", "Nova pergunta")
            archived = await module.history("s1", actor, None)
            self.assertTrue(archived["archived"])
            self.assertEqual(len(archived["messages"]), 1)
            module.archive("s1", actor, restore=True)
            restored = await module.history("s1", actor, None)
            self.assertFalse(restored["archived"])
            self.assertEqual(len(restored["messages"]), 3)
        engine.dispose()
