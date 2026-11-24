"""Conversa contínua no portal real; credenciais de teste vêm só do ambiente.

Executar com AURORA_UI_URL=http://127.0.0.1:8770 e AURORA_UI_PASSWORD.
A conta moradora deve ter histórico sintético e nenhuma confirmação pendente.
A verificação assíncrona intercepta somente a resposta de mensagem e o refresh
subsequente para testar o rascunho sem chamar Gemini nem gravar dados.
"""

import asyncio
import copy
import json
import os
import re
import unittest
from urllib.parse import urlsplit

from playwright.async_api import async_playwright, expect


@unittest.skipUnless(
    os.environ.get("AURORA_UI_URL"), "Informe a instância local de teste"
)
class AssistantConversationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.url = os.environ["AURORA_UI_URL"].rstrip("/")
        parsed = urlsplit(self.url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.port != 8770
        ):
            raise ValueError("Use o portal local na porta fixa 8770.")
        password = os.environ.get("AURORA_UI_PASSWORD")
        if not password:
            raise ValueError("Defina a senha da conta sintética em AURORA_UI_PASSWORD.")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={"width": 1365, "height": 900})
        await self.page.goto(self.url, wait_until="networkidle")
        await self.page.get_by_role("textbox", name="E-mail", exact=True).fill(
            os.environ.get("AURORA_UI_EMAIL", "morador@aurora.test")
        )
        await self.page.get_by_label("Senha", exact=True).fill(password)
        await self.page.get_by_role(
            "button", name="Entrar no portal", exact=True
        ).click()
        await expect(
            self.page.locator(".sidebar").get_by_role(
                "link", name="Assistente", exact=True
            )
        ).to_be_visible()
        async with self.page.expect_response(self.is_history_response) as response:
            await (
                self.page.locator(".sidebar")
                .get_by_role("link", name="Assistente", exact=True)
                .click()
            )
        history = await response.value
        self.assertEqual(history.status, 200)
        self.assertIn("include_archived=true", history.url)
        self.history = await history.json()
        await expect(
            self.page.get_by_role("textbox", name="Mensagem", exact=True)
        ).to_be_enabled()
        await expect(
            self.page.get_by_text("Carregando sua conversa…", exact=True)
        ).to_have_count(0)

    @staticmethod
    def is_history_response(response):
        return (
            "/api/resident/chat/sessions/" in response.url
            and "/history?" in response.url
        )

    async def asyncTearDown(self):
        if getattr(self, "browser", None):
            await self.browser.close()
        if getattr(self, "playwright", None):
            await self.playwright.stop()

    async def assert_history_visible(self):
        expected = {row["id"] for row in self.history["messages"] if row.get("id")}
        self.assertTrue(
            expected,
            "Prepare ao menos uma mensagem sintética persistida para testar a recuperação.",
        )
        await self.page.wait_for_function(
            "expected => { const rendered = new Set([...document.querySelectorAll('.aurora-chat-message[data-message-id]')].map(node => node.dataset.messageId)); return expected.every(id => rendered.has(id)); }",
            arg=sorted(expected),
        )
        await expect(
            self.page.get_by_role(
                "button",
                name=re.compile(
                    "Nova conversa|Limpar exibição|Arquivar|Desfazer limpeza", re.I
                ),
            )
        ).to_have_count(0)
        await expect(self.page.locator("button.conversation")).to_have_count(0)

    async def assert_composer_fits(self):
        geometry = await self.page.evaluate("""() => {
            const composer = document.querySelector('.aurora-chat-compose').getBoundingClientRect();
            const timeline = document.querySelector('.aurora-chat-timeline').getBoundingClientRect();
            return { bottom: composer.bottom, top: composer.top, height: innerHeight,
                width: innerWidth, documentWidth: document.documentElement.scrollWidth,
                documentHeight: document.documentElement.scrollHeight, timelineHeight: timeline.height };
        }""")
        self.assertLessEqual(geometry["bottom"], geometry["height"] + 1)
        self.assertGreater(geometry["top"], 0)
        self.assertLessEqual(geometry["documentWidth"], geometry["width"] + 1)
        self.assertLessEqual(geometry["documentHeight"], geometry["height"] + 2)
        self.assertGreater(geometry["timelineHeight"], 200)

    async def test_single_conversation_restores_history_after_navigation_and_reload(
        self,
    ):
        await self.assert_history_visible()
        await self.assert_composer_fits()
        await (
            self.page.locator(".sidebar")
            .get_by_role("link", name="Minhas reservas", exact=True)
            .click()
        )
        async with self.page.expect_response(self.is_history_response):
            await (
                self.page.locator(".sidebar")
                .get_by_role("link", name="Assistente", exact=True)
                .click()
            )
        await self.assert_history_visible()
        async with self.page.expect_response(self.is_history_response):
            await self.page.reload()
        await self.assert_history_visible()
        await self.page.set_viewport_size({"width": 390, "height": 844})
        await self.assert_composer_fits()
        await self.assert_history_visible()

        # Reopen through the real mobile drawer, then restore after a full load.
        drawer = self.page.locator("#menu-mobile")
        await self.page.get_by_role("button", name="Abrir menu", exact=True).click()
        await expect(drawer).to_be_visible()
        await drawer.get_by_role("link", name="Minhas reservas", exact=True).click()
        await expect(drawer).not_to_be_visible()
        await expect(self.page).to_have_url(re.compile(r"#/reservas$"))
        await self.page.get_by_role("button", name="Abrir menu", exact=True).click()
        await expect(drawer).to_be_visible()
        async with self.page.expect_response(
            self.is_history_response
        ) as mobile_history:
            await drawer.get_by_role("link", name="Assistente", exact=True).click()
        response = await mobile_history.value
        self.assertEqual(response.status, 200)
        self.assertIn("include_archived=true", response.url)
        await expect(drawer).not_to_be_visible()
        await self.assert_history_visible()
        await self.assert_composer_fits()
        async with self.page.expect_response(self.is_history_response) as mobile_reload:
            await self.page.reload()
        response = await mobile_reload.value
        self.assertEqual(response.status, 200)
        self.assertIn("include_archived=true", response.url)
        await self.assert_history_visible()
        await self.assert_composer_fits()

    async def test_enter_sends_once_and_keeps_next_draft_while_waiting(self):
        self.assertFalse(
            self.history["confirmacoes_pendentes"],
            "A fixture não pode ter uma decisão pendente.",
        )
        sent, release = asyncio.Event(), asyncio.Event()
        calls = 0
        snapshot = copy.deepcopy(self.history)
        snapshot["messages"] += [
            {
                "id": "ui-user",
                "role": "user",
                "content": "Primeira linha\nSegunda linha",
            },
            {
                "id": "ui-assistant",
                "role": "assistant",
                "content": "Resposta sintética para testar a interface.",
            },
        ]

        async def delayed(route):
            nonlocal calls
            calls += 1
            sent.set()
            await release.wait()
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": "Resposta sintética para testar a interface.",
                        "confirmacoes_pendentes": [],
                    }
                ),
            )

        async def persisted(route):
            await route.fulfill(
                status=200, content_type="application/json", body=json.dumps(snapshot)
            )

        await self.page.route("**/api/resident/chat/sessions/*/messages", delayed)
        await self.page.route("**/api/resident/chat/sessions/*/history?*", persisted)
        field = self.page.get_by_role("textbox", name="Mensagem", exact=True)
        await field.fill("Primeira linha")
        await field.press("Shift+Enter")
        await field.press_sequentially("Segunda linha")
        await expect(field).to_have_value("Primeira linha\nSegunda linha")
        await field.press("Enter")
        await asyncio.wait_for(sent.wait(), 5)
        await expect(field).to_have_value("")
        await field.fill("Rascunho da próxima mensagem")
        release.set()
        await expect(
            self.page.get_by_text(
                "Resposta sintética para testar a interface.", exact=True
            )
        ).to_be_visible()
        await expect(field).to_have_value("Rascunho da próxima mensagem")
        await expect(
            self.page.get_by_role("button", name="Enviar", exact=True)
        ).to_be_enabled()
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
