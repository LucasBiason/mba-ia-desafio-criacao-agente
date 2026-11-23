"""API real + controller + Runner fake; identidade/domínio simulados, SQLite temporário."""

import tempfile
import unittest
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from services.agent.routers.chat_router import router, message_handler
from aurora_toolkit.identity import authenticated_user, verify_internal
from test_adk_read_runner import BaseLlm

if BaseLlm is not None:
    from test_adk_read_runner import FakeModel
    from google.adk.sessions import DatabaseSessionService
    from services.agent.runtime.message_handler import ReadOnlyMessageHandler
    from services.agent.tools.reservation_read import ReservationReadTool


@unittest.skipIf(BaseLlm is None, "Instale requirements-adk-probe.txt")
class AdkMessageApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{Path(self.temp.name) / 'api.db'}"
        )
        self.sid = uuid4()
        self.actor = {"id": "a", "role": "resident", "active": True}
        self.repo = MagicMock()
        self.repo.__enter__.return_value = self.repo
        self.repo.get.side_effect = (
            lambda sid, uid: SimpleNamespace(apartment="101")
            if sid == self.sid and uid == "a"
            else None
        )
        self.repo.active_reservations.return_value = []
        self.loader = lambda uid: {**self.actor, "id": uid}
        self.model_factory = MagicMock(side_effect=FakeModel)
        self.handler = ReadOnlyMessageHandler(
            identity_loader=self.loader,
            repository_factory=lambda: self.repo,
            tool_factory=lambda identity: ReservationReadTool(
                identity,
                repository_factory=lambda: self.repo,
                identity_loader=self.loader,
            ),
            model_factory=self.model_factory,
            session_service=self.db,
        )
        self.app = FastAPI()
        self.app.include_router(router)

        def internal_guard(x_test_internal: str | None = Header(default=None)):
            if x_test_internal != "synthetic":
                raise HTTPException(401)

        self.app.dependency_overrides[verify_internal] = internal_guard
        self.app.dependency_overrides[authenticated_user] = lambda: dict(self.actor)
        self.app.dependency_overrides[message_handler] = lambda: self.handler
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.repo_patch = patch(
            "services.agent.controllers.chat_controller.ChatRepository",
            return_value=self.repo,
        )
        self.repo_patch.start()

        def forward(service, method, path, payload, timeout):
            self.assertEqual(timeout.read, 65)
            self.assertEqual(timeout.connect, 3)
            return self.client.post(
                path, json=payload, headers={"x-test-internal": "synthetic"}
            )

        self.forward = patch(
            "services.agent.controllers.chat_controller.internal_request",
            side_effect=forward,
        )
        self.forward.start()

    def tearDown(self):
        self.forward.stop()
        self.repo_patch.stop()
        self.client.portal.call(self.db.close)
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def payload(self, **changes):
        return {
            "session_id": str(self.sid),
            "user_id": "a",
            "apartment": "101",
            "message": "Minhas reservas",
            **changes,
        }

    def post(self, **changes):
        return self.client.post(
            "/internal/chat/messages",
            json=self.payload(**changes),
            headers={"x-test-internal": "synthetic"},
        )

    def test_public_api_through_internal_boundary_to_runner(self):
        for _ in range(2):
            result = self.client.post(
                f"/api/resident/chat/sessions/{self.sid}/messages",
                json={"message": "Reservas"},
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json(), {"message": "Consulta concluída."})
        self.assertEqual(self.repo.active_reservations.call_count, 2)
        session = self.client.portal.call(
            partial(
                self.db.get_session,
                app_name="aurora_read_probe",
                user_id="a",
                session_id=str(self.sid),
            )
        )
        self.assertEqual(len(session.events), 8)
        foreign = self.client.portal.call(
            partial(
                self.db.get_session,
                app_name="aurora_read_probe",
                user_id="b",
                session_id=str(self.sid),
            )
        )
        self.assertIsNone(foreign)

    def test_cross_session_owner_and_unit_never_start_model(self):
        for changes in (
            {"session_id": str(uuid4())},
            {"user_id": "b"},
            {"apartment": "302"},
            {"session_id": "invalid"},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.post(**changes).status_code, 404)
        self.model_factory.assert_not_called()
        self.repo.active_reservations.assert_not_called()

    def test_revoked_actor_fails_before_model(self):
        self.assertEqual(self.post().status_code, 200)
        self.actor["active"] = False
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.model_factory.call_count, 1)

    def test_internal_guard_and_disabled_default_are_preserved(self):
        self.assertEqual(
            self.client.post(
                "/internal/chat/messages", json=self.payload()
            ).status_code,
            401,
        )
        del self.app.dependency_overrides[message_handler]
        result = self.post()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json()["detail"]["code"], "AGENT_NOT_CONFIGURED")
        self.model_factory.assert_not_called()

    def test_public_api_preserves_conflict_without_automatic_retry(self):
        from google.adk.errors._stale_session_error import StaleSessionError

        with patch(
            "services.agent.runtime.message_handler.ReadOnlyAgentRuntime.respond",
            new=AsyncMock(side_effect=StaleSessionError("internal details")),
        ) as respond:
            result = self.client.post(
                f"/api/resident/chat/sessions/{self.sid}/messages",
                json={"message": "Reservas"},
            )
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json()["detail"]["code"], "CHAT_SESSION_CONFLICT")
        self.assertNotIn("internal details", result.text)
        respond.assert_awaited_once()

    def test_first_consultation_uses_real_domain_sql_and_excludes_foreign_records(self):
        from test_reservation_tool_repository import ReservationToolRepositoryTest
        from services.agent.repositories.reservation_tool_repository import (
            ReservationToolRepository,
        )
        from sqlalchemy import create_engine, text
        from functools import partial

        domain_engine = create_engine(f"sqlite:///{Path(self.temp.name) / 'domain.db'}")
        fixture = ReservationToolRepositoryTest()
        with patch(
            "test_reservation_tool_repository.create_engine", return_value=domain_engine
        ):
            fixture.setUp()
        try:
            self.sid = fixture.session_id

            def factory():
                return ReservationToolRepository(fixture.database)

            self.repo_patch.stop()
            self.repo_patch = patch(
                "services.agent.controllers.chat_controller.ChatRepository",
                side_effect=factory,
            )
            self.repo_patch.start()
            handler = ReadOnlyMessageHandler(
                identity_loader=self.loader,
                repository_factory=factory,
                tool_factory=lambda identity: ReservationReadTool(
                    identity, repository_factory=factory, identity_loader=self.loader
                ),
                model_factory=FakeModel,
                session_service=self.db,
            )
            self.app.dependency_overrides[message_handler] = lambda: handler
            response = self.client.post(
                f"/api/resident/chat/sessions/{self.sid}/messages",
                json={"message": "Minhas reservas"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            session = self.client.portal.call(
                partial(
                    self.db.get_session,
                    app_name="aurora_read_probe",
                    user_id="a",
                    session_id=str(self.sid),
                )
            )
            results = [
                part.function_response.response
                for event in session.events
                if event.content
                for part in event.content.parts or []
                if part.function_response
            ]
            reservations = results[0]["reservations"]
            self.assertEqual([r["code"] for r in reservations], ["mine"])
            self.assertNotIn("resident_id", reservations[0])
            with domain_engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE apartment_residents SET resident_id='b' WHERE apartment_id=1"
                    )
                )
            denied = self.client.post(
                f"/api/resident/chat/sessions/{self.sid}/messages",
                json={"message": "Mostre histórico"},
            )
            self.assertEqual(denied.status_code, 404)
            after = self.client.portal.call(
                partial(
                    self.db.get_session,
                    app_name="aurora_read_probe",
                    user_id="a",
                    session_id=str(self.sid),
                )
            )
            self.assertEqual(len(after.events), len(session.events))
        finally:
            fixture.tearDown()


@unittest.skipIf(BaseLlm is None, "Requires ADK")
class ProviderQuotaTest(unittest.IsolatedAsyncioTestCase):
    async def test_quota_is_sanitized_and_not_retried(self):
        from google.genai.errors import ClientError

        handler = ReadOnlyMessageHandler(
            identity_loader=None,
            repository_factory=None,
            tool_factory=None,
            model_factory=None,
            session_service=None,
        )
        handler._respond = AsyncMock(
            side_effect=ClientError(
                429, {"error": {"message": "private-provider-detail"}}
            )
        )
        with self.assertRaises(HTTPException) as caught:
            await handler(None)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.detail["code"], "AGENT_QUOTA_EXCEEDED")
        self.assertNotIn("private-provider-detail", str(caught.exception.detail))
        handler._respond.assert_awaited_once()
