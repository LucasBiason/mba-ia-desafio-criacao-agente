"""Sem rede: verifica destino, proxy, TLS e orçamento de latência."""

import unittest
from unittest.mock import patch

import httpx
from aurora_toolkit.identity import service_client

from services.agent.runtime.limits import (
    AGENT_EXECUTION_TIMEOUT_SECONDS,
    AGENT_UPSTREAM_READ_TIMEOUT_SECONDS,
)
from services.agent.runtime.provider_transport import (
    create_provider_clients,
    enforce_ai_studio,
)


class ProviderTransportTest(unittest.IsolatedAsyncioTestCase):
    async def test_environment_cannot_redirect_or_disable_tls(self):
        with patch.dict(
            "os.environ",
            {
                "HTTPS_PROXY": "http://untrusted.invalid:8888",
                "SSL_CERT_FILE": "/nonexistent/untrusted.pem",
                "GOOGLE_GEMINI_BASE_URL": "https://untrusted.invalid",
            },
        ):
            sync, asynchronous = create_provider_clients()
            try:
                self.assertFalse(sync.trust_env)
                self.assertFalse(asynchronous.trust_env)
                self.assertFalse(sync.follow_redirects)
                self.assertFalse(asynchronous.follow_redirects)
                for url in (
                    "https://untrusted.invalid/x",
                    "http://generativelanguage.googleapis.com",
                    "https://generativelanguage.googleapis.com:444/x",
                ):
                    with self.assertRaises(ValueError):
                        enforce_ai_studio(httpx.Request("POST", url))
                enforce_ai_studio(
                    httpx.Request(
                        "POST",
                        "https://generativelanguage.googleapis.com/v1beta/models",
                    )
                )
            finally:
                sync.close()
                await asynchronous.aclose()

    async def test_upstream_waits_beyond_runtime_and_identity_remains_short(self):
        self.assertGreater(
            AGENT_UPSTREAM_READ_TIMEOUT_SECONDS, AGENT_EXECUTION_TIMEOUT_SECONDS
        )
        self.assertEqual(service_client().timeout, 3)
        self.assertEqual(service_client(timeout=65).timeout, 65)

    async def test_nginx_message_routes_have_specific_timeout_and_no_retry(self):
        import re
        from pathlib import Path

        config = (
            Path(__file__).resolve().parents[3] / "services/frontend/nginx.conf"
        ).read_text()
        matches = re.findall(r"location ~ ([^\n]+) \{([^}]+)\}", config)
        matches = [
            (pattern, body)
            for pattern, body in matches
            if "(?:messages|confirmations)$" in pattern
        ]
        self.assertEqual(len(matches), 2)
        for prefix in ("", "/services/agent"):
            for action in ("messages", "confirmations"):
                route = f"{prefix}/api/resident/chat/sessions/example/{action}"
                self.assertEqual(
                    sum(bool(re.fullmatch(pattern, route)) for pattern, _ in matches), 1
                )
        for _, body in matches:
            timeout = int(re.search(r"proxy_read_timeout (\d+)s;", body).group(1))
            self.assertGreater(timeout, AGENT_UPSTREAM_READ_TIMEOUT_SECONDS)
            self.assertIn("proxy_next_upstream off;", body)
        self.assertIn("proxy_read_timeout 15s;", config)
        self.assertLess(
            config.index("/(?:messages|confirmations)$"),
            config.index("/api/resident/chat(?:/|$)"),
        )
