"""Composição sem acessar credenciais reais ou rede de modelo."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.agent.runtime.configuration import (
    AgentRuntimeSettings,
    configure_read_agent,
)
from services.agent.routers.chat_router import message_handler
from test_adk_read_runner import BaseLlm

if BaseLlm is not None:
    from test_adk_read_runner import FakeModel


class DisabledConfigurationTest(unittest.TestCase):
    def test_disabled_never_reads_credentials_or_imports_provider(self):
        app = FastAPI()
        secret = MagicMock(side_effect=AssertionError("No secrets"))
        configure_read_agent(app, AgentRuntimeSettings(), credential_provider=secret)
        secret.assert_not_called()
        self.assertFalse(hasattr(app.state, "agent_message_handler"))

    def test_invalid_settings_fail_before_credentials(self):
        for model, url in (
            ("", "sqlite+aiosqlite:///x.db"),
            ("gemini-test", "sqlite+aiosqlite:///:memory:"),
            ("gemini-test", "https://remote"),
        ):
            with self.subTest(model=model, url=url), self.assertRaises(ValueError):
                configure_read_agent(
                    FastAPI(),
                    AgentRuntimeSettings(True, model, url),
                    credential_provider=lambda: self.fail("No secrets"),
                )


@unittest.skipIf(BaseLlm is None, "Instale requirements-adk-probe.txt")
class ConfiguredRuntimeTest(unittest.TestCase):
    def test_explicit_wiring_is_lazy_and_provider_is_mocked(self):
        with tempfile.TemporaryDirectory() as folder:
            app = FastAPI()
            secret = MagicMock(return_value="synthetic-not-a-real-key")
            settings = AgentRuntimeSettings(
                True, "gemini-test", f"sqlite+aiosqlite:///{Path(folder) / 'agent.db'}"
            )
            with patch(
                "google.adk.models.google_llm.Gemini", return_value=FakeModel()
            ) as gemini:
                configure_read_agent(app, settings, credential_provider=secret)
                secret.assert_not_called()
                handler = app.state.agent_message_handler
                self.assertIs(message_handler(SimpleNamespace(app=app)), handler)
                handler.model_factory()
                handler.model_factory()
                secret.assert_called_once()
                gemini.assert_called_once()
                args = gemini.call_args.kwargs
                self.assertFalse(args["client_kwargs"]["vertexai"])
                self.assertEqual(args["client_kwargs"]["http_options"].timeout, 15000)
                self.assertEqual(
                    args["client_kwargs"]["http_options"].retry_options.attempts, 1
                )
                with TestClient(app):
                    pass

    def test_missing_credential_is_503_without_client(self):
        from fastapi import HTTPException

        with tempfile.TemporaryDirectory() as folder:
            app = FastAPI()
            with patch("google.adk.models.google_llm.Gemini") as gemini:
                configure_read_agent(
                    app,
                    AgentRuntimeSettings(
                        True,
                        "gemini-test",
                        f"sqlite+aiosqlite:///{Path(folder) / 'agent.db'}",
                    ),
                    credential_provider=lambda: "",
                )
                with self.assertRaises(HTTPException) as caught:
                    app.state.agent_message_handler.model_factory()
                self.assertEqual(caught.exception.status_code, 503)
                gemini.assert_not_called()
                with TestClient(app):
                    pass

    def test_unvalidated_adk_version_is_rejected_before_secret(self):
        with patch(
            "services.agent.runtime.configuration.version", return_value="9.0.0"
        ):
            with self.assertRaises(ValueError):
                configure_read_agent(
                    FastAPI(),
                    AgentRuntimeSettings(
                        True, "gemini-test", "sqlite+aiosqlite:///unused.db"
                    ),
                    credential_provider=lambda: self.fail("No secrets"),
                )

    def test_real_sdk_client_pins_endpoint_under_hostile_environment_without_network(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(
                "os.environ",
                {
                    "GOOGLE_GEMINI_BASE_URL": "https://untrusted.invalid",
                    "HTTPS_PROXY": "http://untrusted.invalid:8888",
                    "SSL_CERT_FILE": "/nonexistent/untrusted.pem",
                    "SSL_CERT_DIR": "/nonexistent/untrusted-dir",
                },
            ),
        ):
            app = FastAPI()
            configure_read_agent(
                app,
                AgentRuntimeSettings(
                    True,
                    "gemini-test",
                    f"sqlite+aiosqlite:///{Path(folder) / 'agent.db'}",
                ),
                credential_provider=lambda: "synthetic-not-a-real-key",
            )
            model = app.state.agent_message_handler.model_factory()
            with patch(
                "socket.socket.connect", side_effect=AssertionError("No network")
            ):
                client = model.api_client
                self.assertEqual(
                    client._api_client._http_options.base_url,
                    "https://generativelanguage.googleapis.com",
                )
                self.assertFalse(client._api_client._httpx_client.trust_env)
                self.assertFalse(client._api_client._async_httpx_client.trust_env)
                self.assertFalse(client._api_client._use_aiohttp())
                import ssl

                context = model.client_kwargs["http_options"].client_args["verify"]
                self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
                self.assertTrue(context.check_hostname)
                self.assertGreater(len(context.get_ca_certs()), 0)
            with TestClient(app):
                pass


class EnvironmentCompositionTest(unittest.TestCase):
    def test_disabled_does_not_read_secret_or_construct_runtime(self):
        from services.agent.runtime.configuration import configure_from_environment

        class Environment(dict):
            def get(self, key, default=None):
                if key == "GOOGLE_API_KEY":
                    raise AssertionError("Secret read before authorized message")
                return super().get(key, default)

        with patch(
            "services.agent.runtime.configuration.configure_read_agent"
        ) as configure:
            configure_from_environment(FastAPI(), Environment())
            configure.assert_not_called()

    def test_explicit_environment_composition_retains_lazy_credentials(self):
        from services.agent.runtime.configuration import configure_from_environment

        env = {
            "AURORA_AGENT_ENABLED": "1",
            "AURORA_AGENT_MODEL": "gemini-test",
            "AURORA_AGENT_SESSION_DATABASE_URL": "sqlite+aiosqlite:///dedicated.db",
        }
        with patch(
            "services.agent.runtime.configuration.configure_read_agent"
        ) as configure:
            configure_from_environment(FastAPI(), env)
            settings = configure.call_args.args[1]
            self.assertTrue(settings.enabled)
            self.assertEqual(settings.model, "gemini-test")
            self.assertEqual(configure.call_args.kwargs["credential_provider"](), "")


class ReservationNoticePreflightTest(unittest.TestCase):
    def test_notice_question_does_not_construct_model_or_read_key(self):
        from services.agent.tools.reservation_read import SessionIdentity
        from uuid import uuid4

        with tempfile.TemporaryDirectory() as folder:
            app = FastAPI()
            secret = MagicMock(side_effect=AssertionError("No key access"))
            configure_read_agent(
                app,
                AgentRuntimeSettings(
                    True,
                    "gemini-test",
                    f"sqlite+aiosqlite:///{Path(folder) / 'sessions.db'}",
                    actions_enabled=True,
                ),
                credential_provider=secret,
            )
            with (
                patch(
                    "services.agent.tools.regulation_read.RegulationReadTool.consultar_regulamento",
                    return_value={
                        "status": "not_specified",
                        "version": 0,
                        "message": "Ausência auditada; não implica gratuidade.",
                    },
                ) as read,
                patch(
                    "services.agent.runtime.resident_actions.ProductActions.pending",
                    return_value=[],
                ),
            ):
                result = app.state.agent_message_handler.portal_preflight(
                    SessionIdentity(uuid4(), "synthetic"),
                    "101",
                    "Qual antecedência mínima para reservar o salão e multa por cancelamento?",
                )
            self.assertIn("não implica gratuidade", result["message"])
            read.assert_called_once()
            secret.assert_not_called()
            import asyncio

            asyncio.run(app.state.agent_session_service.close())
