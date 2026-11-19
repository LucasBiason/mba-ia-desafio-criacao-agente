"""Integration checks against the local Compose preview with disposable volumes."""

import json
import os
from pathlib import Path
from secrets import token_hex
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[4]
URL = os.environ.get("AURORA_URL", "http://127.0.0.1:8768").rstrip("/")
OPENER = build_opener(ProxyHandler({}))


def local_settings():
    return dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
                if "=" in line and not line.startswith("#"))


def call(route, method="GET", data=None, token=None):
    request = Request(URL + route, method=method)
    if data is not None:
        request.data = json.dumps(data).encode()
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        response = OPENER.open(request, timeout=12)
    except HTTPError as error:
        response = error
    with response:
        payload = response.read()
        media_type = response.headers.get_content_type()
        return response.status, json.loads(payload) if payload and media_type == "application/json" else payload


class AuroraBaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if urlsplit(URL).scheme != "http" or urlsplit(URL).hostname != "127.0.0.1":
            raise RuntimeError("Use uma instância local de teste em 127.0.0.1.")
        cls.settings = local_settings()
        cls.admin = cls.login("admin@aurora.test", "DEMO_ADMIN_PASSWORD")
        cls.resident = cls.login("morador@aurora.test", "DEMO_RESIDENT_PASSWORD")

    @classmethod
    def login(cls, email, secret):
        status, content = call("/api/auth/login", "POST", {"email": email, "password": cls.settings[secret]})
        if status != 200:
            raise RuntimeError(f"Login da conta de teste falhou com HTTP {status}.")
        return content["access_token"]

    def expect(self, status_code, route, method="GET", data=None, token=None):
        status, payload = call(route, method, data, token)
        self.assertEqual(status, status_code, f"{method} {route} retornou HTTP {status}")
        return payload

    def test_health_and_boundaries(self):
        self.assertEqual(self.expect(200, "/api/health"), {"status": "ready"})
        self.expect(401, "/api/admin/users")
        self.expect(401, "/api/admin/apartments")
        self.expect(403, "/api/admin/apartments", token=self.resident)
        self.expect(403, "/api/admin/users", token=self.resident)
        status, _ = call("/internal/identity", token=self.admin)
        self.assertIn(status, (403, 404))

    def test_imported_apartments_have_a_resident_account(self):
        fixtures = json.loads((ROOT / "dados/apartamentos.json").read_text(encoding="utf-8"))
        apartments = {row["number"]: row for row in self.expect(200, "/api/admin/apartments", token=self.admin)}
        users = {row["id"]: row for row in self.expect(200, "/api/admin/users", token=self.admin)}
        self.assertEqual({user["role"] for user in users.values()}, {"admin", "resident"})
        self.assertEqual(len({row["id"] for row in apartments.values()}), len(apartments))
        for fixture in fixtures:
            apartment = apartments[fixture["numero"]]
            user = users[apartment["resident_id"]]
            self.assertEqual(set(apartment), {"id", "number", "resident_id"})
            self.assertEqual(user["name"], fixture["morador"])
            self.assertEqual(user["role"], "resident")
            self.assertEqual(user["active"], fixture["numero"] == "101")
        mine = self.expect(200, "/api/resident/apartments", token=self.resident)
        self.assertEqual([row["number"] for row in mine], ["101"])

    def test_last_active_admin_is_protected(self):
        admins = self.expect(200, "/api/admin/users", token=self.admin)
        own = self.expect(200, "/api/auth/me", token=self.admin)
        other_ids = [row["id"] for row in admins if row["role"] == "admin"
                     and row["active"] and row["id"] != own["id"]]
        disabled = []
        try:
            for user_id in other_ids:
                self.expect(200, f"/api/admin/users/{user_id}", "PATCH", {"active": False}, self.admin)
                disabled.append(user_id)
            error = self.expect(409, f"/api/admin/users/{own['id']}", "PATCH", {"active": False}, self.admin)
            self.assertEqual(error["detail"]["code"], "LAST_ADMIN")
            self.expect(200, "/api/admin/users", token=self.admin)
        finally:
            for user_id in disabled:
                self.expect(200, f"/api/admin/users/{user_id}", "PATCH", {"active": True}, self.admin)

    def test_login_validation_and_logout(self):
        token = self.login("morador@aurora.test", "DEMO_RESIDENT_PASSWORD")
        self.assertEqual(self.expect(200, "/api/auth/me", token=token)["role"], "resident")
        start, middle, signature = token.split(".")
        mutated = ("x" if signature[0] != "x" else "y") + signature[1:]
        self.expect(401, "/api/areas", token=f"{start}.{middle}.{mutated}")
        arbitrary_validation_input = "invalid-input"
        invalid = self.expect(422, "/api/auth/login", "POST", {
            "email": "malformado", "password": arbitrary_validation_input,
        })
        self.assertNotIn(arbitrary_validation_input, json.dumps(invalid))
        self.expect(204, "/api/auth/logout", "POST", token=token)
        self.expect(401, "/api/auth/me", token=token)
        self.expect(401, "/api/areas", token=token)

    def test_accounts_and_apartments(self):
        suffix = token_hex(3)
        email = f"qa-{suffix}@aurora.test"
        password = token_hex(18)
        account = {"name": "Morador QA", "email": email, "password": password, "role": "resident"}
        self.expect(422, "/api/admin/users", "POST", {**account, "role": "superuser"}, self.admin)
        created = self.expect(201, "/api/admin/users", "POST", account, self.admin)
        user_id = created["id"]
        self.assertNotIn("password", json.dumps(created))
        self.expect(409, "/api/admin/users", "POST", account, self.admin)
        error = self.expect(409, f"/api/admin/users/{user_id}", "PATCH", {"role": "admin"}, self.admin)
        self.assertEqual(error["detail"]["code"], "ROLE_IMMUTABLE")
        number_base = str(7_000_000 + int(suffix, 16))
        numbers = (number_base + "A", number_base + "B")
        for number in numbers:
            self.expect(201, "/api/admin/apartments", "POST",
                        {"number": number, "resident_id": user_id}, self.admin)
        self.expect(409, "/api/admin/apartments", "POST",
                    {"number": numbers[0], "resident_id": user_id}, self.admin)
        token = self.expect(200, "/api/auth/login", "POST", {"email": email, "password": password})["access_token"]
        owned = self.expect(200, "/api/resident/apartments", token=token)
        self.assertEqual({row["number"] for row in owned}, {number.upper() for number in numbers})
        self.expect(403, f"/api/admin/apartments/{numbers[0]}", "PATCH", {"resident_id": None}, token)
        self.expect(200, f"/api/admin/apartments/{numbers[0]}", "PATCH", {"resident_id": None}, self.admin)
        owned = self.expect(200, "/api/resident/apartments", token=token)
        self.assertEqual([row["number"] for row in owned], [numbers[1].upper()])
        self.expect(409, "/api/admin/apartments/101", "DELETE", token=self.admin)
        original = self.expect(200, f"/api/admin/apartments/{numbers[0]}", token=self.admin)
        renumbered = number_base + "C"
        changed = self.expect(200, f"/api/admin/apartments/{numbers[0]}", "PATCH",
                              {"number": renumbered}, self.admin)
        self.assertEqual(changed["id"], original["id"])
        self.assertEqual(changed["number"], renumbered)
        for number in (renumbered, numbers[1]):
            self.expect(204, f"/api/admin/apartments/{number}", "DELETE", token=self.admin)
        self.expect(200, f"/api/admin/users/{user_id}", "PATCH", {"active": False}, self.admin)
        self.expect(401, "/api/auth/me", token=token)

    def test_areas_and_agenda(self):
        area = {"id": "qa-" + token_hex(3), "name": "Área QA " + token_hex(3), "fee_cents": 0}
        self.expect(422, "/api/admin/areas", "POST", {**area, "fee_cents": -1}, self.admin)
        self.expect(201, "/api/admin/areas", "POST", area, self.admin)
        self.expect(403, f"/api/admin/areas/{area['id']}", "PATCH", {"fee_cents": 120}, self.resident)
        revised = self.expect(200, f"/api/admin/areas/{area['id']}", "PATCH", {"fee_cents": 250}, self.admin)
        self.assertEqual(revised["fee_cents"], 250)
        self.expect(204, f"/api/admin/areas/{area['id']}", "DELETE", token=self.admin)
        self.expect(404, f"/api/admin/areas/{area['id']}", token=self.admin)
        reservations = self.expect(200, "/api/admin/reservations", token=self.admin)
        self.assertGreater(len(reservations), 0)
        area_id = reservations[0]["area_id"]
        params = urlencode({"area_id": area_id})
        filtered = self.expect(200, f"/api/admin/reservations?{params}", token=self.admin)
        self.assertTrue(filtered and all(row["area_id"] == area_id for row in filtered))
        self.expect(409, f"/api/admin/areas/{area_id}", "DELETE", token=self.admin)
        self.expect(200, "/api/admin/visits", token=self.admin)

    def test_record_hours_are_validated_and_persisted(self):
        reservations = self.expect(200, "/api/admin/reservations", token=self.admin)
        initial = next(row for row in reservations if row["code"] == "RSV-1377")
        route = f"/api/admin/reservations/{initial['code']}/hours"
        unchanged = {key: initial[key] for key in ("start_time", "end_time")}
        valid = {"start_time": "13:30", "end_time": "15:00"}
        self.expect(403, route, "PATCH", valid, self.resident)
        self.expect(422, route, "PATCH", {"start_time": "18:00", "end_time": "09:00"}, self.admin)
        self.expect(422, route, "PATCH", {"start_time": "13:30", "end_time": None}, self.admin)
        self.expect(404, "/api/admin/reservations/RSV-missing/hours", "PATCH", valid, self.admin)
        try:
            changed = self.expect(200, route, "PATCH", valid, self.admin)
            self.assertEqual(changed, {**initial, **valid})
            mine = self.expect(200, "/api/resident/reservations?apartment=101", token=self.resident)
            own = next(row for row in mine if row["code"] == initial["code"])
            self.assertEqual({key: own[key] for key in valid}, valid)
            self.assertNotIn("resident_id", own)
        finally:
            self.expect(200, route, "PATCH", unchanged, self.admin)

        visits = self.expect(200, "/api/admin/visits", token=self.admin)
        initial = next(row for row in visits if row["apartment"] == "302")
        route = f"/api/admin/visits/{initial['id']}/hours"
        unchanged = {key: initial[key] for key in ("entry_time", "exit_time")}
        valid = {"entry_time": "08:45", "exit_time": "10:20"}
        self.expect(403, route, "PATCH", valid, self.resident)
        self.expect(422, route, "PATCH", {"entry_time": None, "exit_time": "10:20"}, self.admin)
        try:
            partial = self.expect(200, route, "PATCH", {"entry_time": "08:45", "exit_time": None}, self.admin)
            self.assertEqual(partial["entry_time"], "08:45")
            self.assertIsNone(partial["exit_time"])
            updated = self.expect(200, route, "PATCH", valid, self.admin)
            self.assertEqual(updated, {**initial, **valid})
            current = self.expect(200, "/api/admin/visits?apartment=302", token=self.admin)
            self.assertIn(updated, current)
        finally:
            self.expect(200, route, "PATCH", unchanged, self.admin)

    def test_regulation_versions(self):
        previous = self.expect(200, "/api/admin/regulation", token=self.admin)
        new_body = {"base_version": previous["version"], "content": previous["content"] + "\nNota QA."}
        self.expect(403, "/api/admin/regulation", "PUT", new_body, self.resident)
        new = self.expect(200, "/api/admin/regulation", "PUT", new_body, self.admin)
        self.assertEqual(new["version"], previous["version"] + 1)
        self.assertEqual(new["author_id"], "demo-admin")
        self.expect(409, "/api/admin/regulation", "PUT", new_body, self.admin)
        history = self.expect(200, "/api/admin/regulation/versions", token=self.admin)
        preserved = next(v for v in history if v["version"] == previous["version"])
        self.assertEqual(preserved["content"], previous["content"])
        current = self.expect(200, "/api/resident/regulation", token=self.resident)
        self.assertEqual(current["version"], new["version"])

    def test_resident_scope_chat_and_history(self):
        self.expect(403, "/api/resident/reservations?apartment=302", token=self.resident)
        self.expect(403, "/api/resident/visits?apartment=302", token=self.resident)
        reservations = self.expect(200, "/api/resident/reservations?apartment=101", token=self.resident)
        visits = self.expect(200, "/api/resident/visits?apartment=101", token=self.resident)
        self.assertGreater(len(reservations), 0)
        self.assertTrue(all(row["apartment"] == "101" for row in reservations + visits))
        self.expect(403, "/api/resident/chat/sessions", "POST", {"apartment": "302"}, self.resident)
        self.expect(403, "/api/resident/chat/sessions", "POST", {"apartment": "101"}, self.admin)
        session = self.expect(201, "/api/resident/chat/sessions", "POST", {"apartment": "101"}, self.resident)
        path = "/api/resident/chat/sessions/" + session["id"]
        self.assertEqual(self.expect(200, path, token=self.resident)["apartment"], "101")
        self.assertTrue(any(row["id"] == session["id"] for row in
                            self.expect(200, "/api/resident/chat/sessions", token=self.resident)))
        failure = self.expect(503, path + "/messages", "POST", {"message": "Quais são minhas reservas?"}, self.resident)
        self.assertEqual(failure["detail"]["code"], "AGENT_NOT_CONFIGURED")
        after = self.expect(200, "/api/resident/reservations?apartment=101", token=self.resident)
        self.assertEqual(reservations, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
