"""A projeção pública recusa cópias das instruções reais, sem tocar em dados."""

import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from services.agent.runtime.multi_agent_actions import MultiAgentActionRuntime
from services.agent.runtime.routing import ROUTING_INSTRUCTION


class PublicControlProjectionTest(unittest.TestCase):
    def runtime(self):
        runtime = object.__new__(MultiAgentActionRuntime)
        runtime.read_results = []
        runtime.reservas = SimpleNamespace(
            instruction="Use exclusivamente as ferramentas para executar alterações autorizadas."
        )
        runtime.convivencia = SimpleNamespace(
            instruction="Consulte o artigo pertinente sem carregar outros capítulos do regulamento."
        )
        runtime.runner = SimpleNamespace(
            app=SimpleNamespace(
                root_agent=SimpleNamespace(instruction=ROUTING_INSTRUCTION)
            )
        )
        runtime.actions = SimpleNamespace(
            results=[], message_projection=lambda text: {"message": text}
        )
        return runtime

    def test_routing_and_specialist_instruction_fragments_are_not_public(self):
        runtime = self.runtime()
        for text in [
            "**Você distribui a solicitação do morador entre dois especialistas.**",
            runtime.reservas.instruction,
            runtime.convivencia.instruction,
        ]:
            with self.subTest(text=text):
                self.assertTrue(runtime.contains_control_text(text))
                with self.assertRaises(HTTPException) as caught:
                    runtime.project_message(text)
                self.assertEqual(caught.exception.status_code, 503)

    def test_ungrounded_model_text_never_becomes_a_public_receipt(self):
        text = "Olá! Posso ajudar com suas reservas e autorizações de visita."
        with self.assertRaises(HTTPException) as caught:
            self.runtime().project_message(text)
        self.assertEqual(caught.exception.status_code, 503)
        runtime = self.runtime()
        runtime.read_results = [("reservations", {"reservations": []})]
        self.assertIn(
            "Não há reservas ativas", runtime.project_message(text)["message"]
        )
        self.assertNotIn(text, runtime.project_message(text)["message"])
