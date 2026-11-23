"""Provas locais sem modelo, credenciais, rede ou gravação no condomínio."""

from dataclasses import FrozenInstanceError
from datetime import date
import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import HTTPException
from services.agent.tools.reservation_read import ReservationReadTool, SessionIdentity


class ReservationReadToolTest(unittest.TestCase):
    def setUp(self):
        self.session_id = uuid4()
        self.actor = {
            "id": "resident-a",
            "name": "Morador",
            "email": "a@aurora.test",
            "role": "resident",
            "active": True,
        }
        self.identity = SessionIdentity.from_authenticated_actor(
            self.session_id, self.actor
        )
        self.repository = MagicMock()
        self.repository.__enter__.return_value = self.repository
        self.repository.get.return_value = SimpleNamespace(apartment="101")
        self.repository.active_reservations.return_value = []
        self.loader = MagicMock(return_value=dict(self.actor))
        self.tool = ReservationReadTool(
            self.identity,
            repository_factory=lambda: self.repository,
            identity_loader=self.loader,
        )

    def test_identity_is_immutable_and_actor_snapshot_is_not_reused(self):
        with self.assertRaises(FrozenInstanceError):
            self.identity.resident_id = "other"
        self.actor["id"] = "other"
        self.assertEqual(self.identity.resident_id, "resident-a")

    def test_model_has_no_identity_or_apartment_arguments(self):
        self.assertEqual(
            list(inspect.signature(self.tool.list_my_reservations).parameters), []
        )
        with self.assertRaises(TypeError):
            self.tool.list_my_reservations(apartment="302")

    def test_uses_only_bound_session_and_current_owner(self):
        self.assertEqual(self.tool.list_my_reservations(), {"reservations": []})
        self.loader.assert_called_once_with("resident-a")
        self.repository.get.assert_called_once_with(self.session_id, "resident-a")
        self.repository.active_reservations.assert_called_once_with(
            self.session_id, "resident-a"
        )

    def test_foreign_missing_or_revoked_session_never_queries_reservations(self):
        self.repository.get.return_value = None
        with self.assertRaises(HTTPException) as caught:
            self.tool.list_my_reservations()
        self.assertEqual(caught.exception.status_code, 404)
        self.repository.active_reservations.assert_not_called()

    def test_deactivated_or_mismatched_identity_is_rejected(self):
        for values in ({"active": False}, {"id": "resident-b"}):
            with self.subTest(values=values):
                self.loader.return_value = {**self.actor, **values}
                with self.assertRaises(HTTPException) as caught:
                    self.tool.list_my_reservations()
                self.assertEqual(caught.exception.status_code, 401)
        self.repository.get.assert_not_called()

    def test_role_change_is_rejected(self):
        self.loader.return_value = {**self.actor, "role": "admin"}
        with self.assertRaises(HTTPException) as caught:
            self.tool.list_my_reservations()
        self.assertEqual(caught.exception.status_code, 403)
        self.repository.active_reservations.assert_not_called()

    def test_public_projection_is_json_serializable_without_resident_id(self):
        row = SimpleNamespace(
            code="QA-1",
            apartment="101",
            area_id="quadra",
            date=date(2030, 4, 6),
            fee_cents=0,
            status="active",
            start_time=None,
            end_time=None,
            resident_id="private-owner",
        )
        self.repository.active_reservations.return_value = [(row, "Quadra")]
        result = self.tool.list_my_reservations()["reservations"][0]
        self.assertEqual(result["date"], "2030-04-06")
        self.assertEqual(result["apartment"], "101")
        self.assertNotIn("resident_id", result)

    def test_admin_and_inactive_actor_cannot_bind_identity(self):
        for values in ({"role": "admin"}, {"active": False}):
            with self.subTest(values=values), self.assertRaises(HTTPException):
                SessionIdentity.from_authenticated_actor(
                    self.session_id, {**self.actor, **values}
                )

    def test_identity_service_failure_is_not_converted_to_empty_success(self):
        self.loader.side_effect = HTTPException(503, "Unavailable")
        with self.assertRaises(HTTPException) as caught:
            self.tool.list_my_reservations()
        self.assertEqual(caught.exception.status_code, 503)
        self.repository.active_reservations.assert_not_called()


if __name__ == "__main__":
    unittest.main()
