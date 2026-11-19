"""Contratos de documentação e segurança do gateway, sem alterar cadastros."""

import unittest

import test_api as api

SERVICES = ("auth", "users", "apartments", "common-areas", "agenda", "visits", "settings", "agent")


class OpenApiContractTest(unittest.TestCase):
    def test_documentation_and_health_of_each_service(self):
        for service in SERVICES:
            with self.subTest(service=service):
                prefix = "/services/" + service
                status, health = api.call(prefix + "/health")
                self.assertEqual(status, 200)
                self.assertEqual(health, {"status": "ready"})
                status, html = api.call(prefix + "/docs")
                self.assertEqual(status, 200)
                self.assertIn((prefix + "/openapi.json").encode(), html)
                status, schema = api.call(prefix + "/openapi.json")
                self.assertEqual(status, 200)
                self.assertIn("/health", schema["paths"])
                for path, operations in schema["paths"].items():
                    for method, operation in operations.items():
                        if method not in ("get", "post", "put", "patch", "delete"):
                            continue
                        self.assertTrue(operation.get("summary"))
                        self.assertTrue(operation.get("tags"))
                        if path.startswith(("/api/admin", "/api/resident")):
                            self.assertEqual(operation["security"], [{"BearerAuth": []}])

    def test_swagger_urls_preserve_identity_and_permissions(self):
        api.AuroraBaseTest.setUpClass()
        for service, path in (("apartments", "/api/admin/apartments"), ("users", "/api/admin/users")):
            with self.subTest(service=service):
                route = "/services/" + service + path
                self.assertEqual(api.call(route)[0], 401)
                self.assertEqual(api.call(route, token=api.AuroraBaseTest.resident)[0], 403)
                self.assertEqual(api.call(route, token=api.AuroraBaseTest.admin)[0], 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
