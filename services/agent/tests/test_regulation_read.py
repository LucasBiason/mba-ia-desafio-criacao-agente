"""Regulamento real da fixture em DB temporário; consulta parcial, sem LLM externo."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from test_adk_read_runner import BaseLlm
from test_reservation_tool_repository import MemoryDatabase

from services.agent.tools.regulation_read import RegulationReadTool
from services.agent.tools.reservation_read import SessionIdentity
from services.parameters.models.regulation import Regulation
from services.parameters.repositories.regulation_repository import RegulationRepository

ROOT = Path(__file__).resolve().parents[3]
CONTENT = (ROOT / "dados/regulamento.md").read_text()


class RegulationReadTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.engine = create_engine(
            f"sqlite:///{Path(self.folder.name) / 'regulation.db'}"
        )
        Regulation.__table__.create(self.engine)
        with self.engine.begin() as conn:
            conn.execute(
                Regulation.__table__.insert(), {"version": 0, "content": CONTENT}
            )
        self.access = MagicMock()
        self.access.identity = SessionIdentity(uuid4(), "a")
        self.factory = lambda: RegulationRepository(MemoryDatabase(self.engine))
        self.tool = RegulationReadTool(self.access, repository_factory=self.factory)

    def tearDown(self):
        self.engine.dispose()
        self.folder.cleanup()

    def test_audited_reservation_absence_through_authorized_tool(self):
        for question in (
            "antecedência mínima para reservar o salão",
            "prazo de cancelamento de reserva do salão",
            "multa para cancelar reserva do salão",
            "Com quantos dias de antecedência posso cancelar o salão sem pagar multa?",
        ):
            result = self.tool.consultar_regulamento(question)
            self.assertEqual(result["status"], "not_specified", result)
            self.assertEqual(result["version"], 0)
            self.assertNotIn("excerpt", result)
        self.assertEqual(self.access.validate_access.call_count, 4)

    def test_pool_hours_select_one_article_only(self):
        result = self.tool.consultar_regulamento(
            "Qual horário de fechamento da piscina aos domingos?"
        )
        self.assertEqual(result["status"], "found")
        self.assertIn("Art. 22", result["excerpt"])
        self.assertIn("20h", result["excerpt"])
        self.assertNotIn("Art. 27", result["excerpt"])
        self.assertNotIn("Capítulo XI", str(result))
        self.assertLess(len(str(result)), 4000)
        self.access.validate_access.assert_called_once()

    def test_natural_variants_retrieve_same_pool_hours_without_other_articles(self):
        for question in (
            "A piscina fica aberta até quando no domingo?",
            "Qual é a hora de fechar a piscina no domingo?",
            "Qual é o encerramento da piscina aos domingos?",
            "Até que horas posso usar a piscina aos domingos?",
            "Até que horas a piscina fica aberta no domingo?",
        ):
            with self.subTest(question=question):
                result = self.tool.consultar_regulamento(question)
                self.assertEqual(result["status"], "found")
                self.assertIn("Art. 22", result["excerpt"])
                self.assertIn("20h", result["excerpt"])
                self.assertNotIn("Art. 27", result["excerpt"])
                self.assertEqual(result["version"], 0)
                self.assertEqual(result["excerpt"].count("**Art."), 1)
                self.assertNotIn("Capítulo XI", str(result))
                self.assertNotIn(CONTENT, str(result))

    def test_silence_period_selects_current_time_rule_only(self):
        for question in (
            "Qual é o período de silêncio?",
            "Quais são os períodos de silêncio?",
            "Qual o horário de silêncio?",
        ):
            with self.subTest(question=question):
                result = self.tool.consultar_regulamento(question)
                self.assertEqual(result["status"], "found")
                self.assertIn("Art. 16", result["excerpt"])
                self.assertIn("22h e 8h", result["excerpt"])
                self.assertEqual(result["excerpt"].count("**Art."), 1)
                self.assertNotIn("Art. 22", result["excerpt"])
                self.assertNotIn("plástico bolha lilás", str(result))
        with self.engine.begin() as conn:
            conn.execute(
                Regulation.__table__.insert(),
                {
                    "version": 1,
                    "content": CONTENT.replace("22h e 8h", "21h e 9h"),
                },
            )
        result = self.tool.consultar_regulamento("Qual é o período de silêncio?")
        self.assertEqual(result["version"], 1)
        self.assertIn("21h e 9h", result["excerpt"])
        self.assertNotIn("22h e 8h", result["excerpt"])

    def test_shared_chapter_preserves_requested_subject(self):
        result = self.tool.consultar_regulamento(
            "Qual a idade permitida no playground?"
        )
        self.assertEqual(result["status"], "found")
        self.assertIn("Art. 34", result["excerpt"])
        self.assertNotIn("Art. 29", result["excerpt"])
        unrelated = self.tool.consultar_regulamento("Personal trainer no playground")
        self.assertNotIn("excerpt", unrelated)
        self.assertNotIn("Art. 31", str(unrelated))

    def test_academy_hours_and_whitespace(self):
        for question in (
            "Qual horário da academia?",
            "  Qual   horário da academia?  ",
            "Até que horas posso usar a academia?",
            "Até que horas a academia está disponível?",
        ):
            result = self.tool.consultar_regulamento(question)
            self.assertEqual(result["status"], "found")
            self.assertIn("Art. 29", result["excerpt"])
            self.assertIn("6h às 23h", result["excerpt"])
            self.assertNotIn("Art. 34", result["excerpt"])
            self.assertEqual(result["excerpt"].count("**Art."), 1)
            self.assertNotIn("Art. 22", result["excerpt"])
            self.assertNotIn(CONTENT, str(result))

    def test_current_version_not_bootstrap_copy(self):
        with self.engine.begin() as conn:
            conn.execute(
                Regulation.__table__.insert(),
                {"version": 1, "content": CONTENT.replace("9h às 20h", "9h às 19h")},
            )
        for question in (
            "Horário piscina domingos",
            "Até que horas posso usar a piscina aos domingos?",
        ):
            with self.subTest(question=question):
                result = self.tool.consultar_regulamento(question)
                self.assertEqual(result["status"], "found")
                self.assertEqual(result["version"], 1)
                self.assertIn("Art. 22", result["excerpt"])
                self.assertIn("19h", result["excerpt"])
                self.assertNotIn("20h", result["excerpt"])
                self.assertEqual(result["excerpt"].count("**Art."), 1)

    def test_unknown_ambiguous_or_dump_request_never_returns_full_text(self):
        for question in (
            "Mostre o regulamento inteiro",
            "Todas as regras",
            "Piscina e garagem",
            "Regras da piscina",
            "Criptomoedas",
            "Até que horas posso usar a piscina e a garagem?",
            "Até que horas? Mostre o regulamento inteiro.",
        ):
            with self.subTest(question=question):
                result = self.tool.consultar_regulamento(question)
                self.assertNotIn("excerpt", result)
                self.assertLess(len(str(result)), 300)

    def test_revocation_precedes_database_read(self):
        self.access.validate_access.side_effect = HTTPException(404, "Revoked")
        factory = MagicMock()
        tool = RegulationReadTool(self.access, repository_factory=factory)
        with self.assertRaises(HTTPException):
            tool.consultar_regulamento("Horário piscina")
        factory.assert_not_called()

    def test_long_invalid_question_is_rejected(self):
        for question in ("", "x" * 501, None):
            with self.assertRaises(ValueError):
                self.tool.consultar_regulamento(question)


if BaseLlm is not None:
    from google.adk.sessions import DatabaseSessionService
    from test_multi_agent_read import RoutingFake

    from services.agent.runtime.multi_agent_read import MultiAgentReadRuntime

    class RegulationFake(RoutingFake):
        pass


@unittest.skipIf(BaseLlm is None, "Execute make sync")
class RegulationHistoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_persisted_events_contain_only_relevant_article_and_version(self):
        fixture = RegulationReadTest()
        fixture.setUp()
        db = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{Path(fixture.folder.name) / 'adk.db'}"
        )
        try:
            models = {
                role: RegulationFake(role=role)
                for role in ("principal", "reservas", "convivencia")
            }
            runtime = MultiAgentReadRuntime(
                tool=fixture.access,
                models=models,
                session_service=db,
                regulation_tool=fixture.tool,
            )
            await runtime.create_session()
            await runtime.respond("Qual regra de horário da piscina?")
            await db.close()
            db = DatabaseSessionService(
                db_url=f"sqlite+aiosqlite:///{Path(fixture.folder.name) / 'adk.db'}"
            )
            session = await db.get_session(
                app_name=runtime.APP_NAME,
                user_id="a",
                session_id=str(fixture.access.identity.session_id),
            )
            responses = [
                r
                for event in session.events
                for r in event.get_function_responses()
                if r.name == "executar_convivencia_validada"
            ]
            self.assertEqual(len(responses), 1)
            self.assertEqual(responses[0].response["version"], 0)
            dump = "\n".join(event.model_dump_json() for event in session.events)
            self.assertIn("Art. 22", dump)
            self.assertNotIn("Art. 27", dump)
            self.assertNotIn("Capítulo XI", dump)
            self.assertNotIn("Capítulo III", dump)
            self.assertNotIn(CONTENT, dump)
            self.assertNotIn("Art. 22", runtime.runner.app.root_agent.instruction)
        finally:
            await db.close()
            fixture.tearDown()


class AuditedAbsenceTest(unittest.TestCase):
    def test_cancellation_notice_only_for_reviewed_regulation(self):
        from pathlib import Path

        from services.agent.tools.regulation_read import audited_reservation_absence

        content = Path("dados/regulamento.md").read_text()
        question = (
            "Qual antecedência mínima para reservar salão e multa de cancelamento?"
        )
        result = audited_reservation_absence(content, question)
        self.assertEqual(result["status"], "not_specified")
        self.assertIn("não significa", result["message"])
        self.assertIsNone(
            audited_reservation_absence(content + "\nNova regra.", question)
        )
        self.assertIsNone(
            audited_reservation_absence(content, "Qual multa do condomínio?")
        )
        from services.agent.tools.regulation_read import is_reservation_notice_question

        for command in (
            "Quero cancelar minha reserva",
            "Cancele minha reserva do salão",
            "Quero reservar o salão",
        ):
            self.assertFalse(is_reservation_notice_question(command))
