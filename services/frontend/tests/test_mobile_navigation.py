"""Regressão F11-AC04 contra uma instância local de teste com conta sintética.

AURORA_URL e AURORA_TEST_ADMIN_PASSWORD são fornecidos pelo ambiente do run.
Requer Playwright Python e Chromium instalados.
"""

import os
import unittest
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


class MobileNavigationTest(unittest.TestCase):
    def test_keyboard_focus_stays_inside_drawer(self):
        url = os.environ["AURORA_URL"]
        if urlsplit(url).hostname != "127.0.0.1":
            raise RuntimeError("Use uma instância local de teste.")
        with sync_playwright() as driver:
            browser = driver.chromium.launch(headless=True)
            try:
                for width in (390, 720):
                    with self.subTest(width=width):
                        context = browser.new_context(
                            viewport={"width": width, "height": 900}
                        )
                        page = context.new_page()
                        page.goto(url)
                        page.get_by_label("E-mail", exact=True).fill(
                            os.environ.get(
                                "AURORA_TEST_ADMIN_EMAIL", "admin@aurora.test"
                            )
                        )
                        page.locator("#password-input").fill(
                            os.environ["AURORA_TEST_ADMIN_PASSWORD"]
                        )
                        page.get_by_role(
                            "button", name="Entrar no portal", exact=True
                        ).click()
                        expect(page.locator("#conteudo")).to_be_visible()
                        opener = page.get_by_role(
                            "button", name="Abrir menu", exact=True
                        )
                        opener.click()
                        dialog = page.locator("#menu-mobile")
                        expect(dialog).to_be_visible()
                        for key in ("Tab", "Shift+Tab"):
                            for _ in range(24):
                                page.keyboard.press(key)
                                self.assertTrue(
                                    dialog.evaluate(
                                        "(d) => d.contains(document.activeElement)"
                                    ),
                                    key,
                                )
                        page.keyboard.press("Escape")
                        expect(dialog).not_to_be_visible()
                        expect(opener).to_be_focused()
                        opener.click()
                        dialog.get_by_role("link", name="Agenda", exact=True).click()
                        expect(dialog).not_to_be_visible()
                        expect(page.locator("#conteudo")).to_be_focused()
                        context.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
