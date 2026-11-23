"""Regressão visual exclusivamente na demonstração sintética localhost.

Executar com AURORA_DEMO_URL=http://127.0.0.1:8793. O teste exige o aviso
'Demonstração isolada' antes de interagir; não usar na instância pessoal.
"""

import asyncio
import json
import os
import unittest
from urllib.parse import urlsplit
from playwright.async_api import async_playwright, expect


@unittest.skipUnless(os.environ.get("AURORA_DEMO_URL"), "Exige demo isolada explícita")
class ChatAsyncSessionsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = os.environ["AURORA_DEMO_URL"]
        if urlsplit(url).hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("Somente demo localhost")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={"width": 1200, "height": 900})
        await self.page.goto(url)
        await expect(self.page.get_by_role("note")).to_contain_text(
            "Demonstração isolada"
        )
        await expect(self.page.locator("button.conversation").first).to_be_visible()
        initial_count = await self.page.locator("button.conversation").count()
        await self.page.get_by_role("button", name="Nova conversa", exact=True).click()
        await expect(self.page.locator("button.conversation")).to_have_count(
            initial_count + 1
        )
        await self.page.locator("button.conversation").nth(0).click()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def exercise(self, failed):
        sent = asyncio.Event()
        release = asyncio.Event()

        async def delayed(route):
            sent.set()
            await release.wait()
            payload = (
                {
                    "detail": {
                        "code": "AGENT_UNAVAILABLE",
                        "message": "Falha tardia da conversa A",
                    }
                }
                if failed
                else {"message": "Resposta tardia da conversa A"}
            )
            await route.fulfill(
                status=503 if failed else 200,
                content_type="application/json",
                body=json.dumps(payload),
            )

        await self.page.route("**/messages", delayed)
        field = self.page.get_by_role("textbox", name="Mensagem")
        await field.fill("Pergunta A")
        await self.page.get_by_role("button", name="Enviar", exact=True).click()
        await asyncio.wait_for(sent.wait(), 5)
        await self.page.locator("button.conversation").nth(1).click()
        await field.fill("Rascunho B deve permanecer")
        release.set()
        await expect(
            self.page.get_by_role("button", name="Enviar", exact=True)
        ).to_be_enabled()
        await expect(field).to_have_value("Rascunho B deve permanecer")
        await expect(
            self.page.get_by_text("Falha tardia da conversa A", exact=True)
        ).to_have_count(0)
        await expect(
            self.page.get_by_text("Resposta tardia da conversa A", exact=True)
        ).to_have_count(0)
        await self.page.locator("button.conversation").nth(0).click()
        await expect(
            self.page.get_by_text(
                "Falha tardia da conversa A"
                if failed
                else "Resposta tardia da conversa A",
                exact=True,
            )
        ).to_be_visible()

    async def test_late_success_preserves_other_session_draft(self):
        await self.exercise(False)

    async def test_late_error_stays_in_original_session(self):
        await self.exercise(True)


if __name__ == "__main__":
    unittest.main()
