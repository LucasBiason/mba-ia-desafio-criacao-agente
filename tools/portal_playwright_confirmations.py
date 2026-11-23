"""Opt-in real Chrome UI test on isolated official portal 8803 only.

No mocked routes, screenshots, recordings, retries or provider calls outside UI.
Reads only the authorized local demo resident password; never logs credentials.
Do not run concurrently with another Gemini test. Effects are synthetic fixtures.
"""

import argparse
import asyncio
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8803"


def demo_password():
    value = os.environ.get("DEMO_RESIDENT_PASSWORD")
    if value:
        return value
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("DEMO_RESIDENT_PASSWORD="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("Demo resident password unavailable")


async def run(args):
    from playwright.async_api import async_playwright, expect

    observations = []
    last_call = None
    password = demo_password()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}, service_workers="block"
        )
        page = await context.new_page()
        page.set_default_timeout(12000)
        token = None
        try:
            await page.goto(BASE, wait_until="domcontentloaded")
            assert urlsplit(page.url).netloc == "127.0.0.1:8803", (
                "Unexpected portal destination"
            )
            await page.get_by_label("E-mail", exact=True).fill("morador@aurora.test")
            await page.get_by_label("Senha", exact=True).fill(password)
            async with page.expect_response(
                lambda r: r.url == BASE + "/api/auth/login", timeout=15000
            ) as response:
                await page.get_by_role(
                    "button", name="Entrar no portal", exact=True
                ).click()
            login = await response.value
            assert login.status == 200, "Login failed"
            token = (await login.json())["access_token"]
            password = None
            await page.get_by_role("link", name="Assistente", exact=True).click()
            await expect(
                page.get_by_role("heading", name="Assistente", exact=True)
            ).to_be_visible()

            async def projection(kind, day, name=None):
                # Read only official authenticated projection; never academic endpoints.
                response = await context.request.get(
                    BASE + "/api/resident/" + kind + "?apartment=101",
                    headers={"Authorization": "Bearer " + token},
                )
                assert response.status == 200, "Projection unavailable"
                values = await response.json()
                if kind == "reservations":
                    return [
                        v
                        for v in values
                        if v["date"] == day
                        and v["area_id"] == "salao-de-festas"
                        and v["status"] == "active"
                    ]
                return [v for v in values if v["date"] == day and v["name"] == name]

            async def send(text):
                nonlocal last_call
                if last_call is not None:
                    await asyncio.sleep(
                        max(0, args.min_gap - (time.monotonic() - last_call))
                    )
                async with page.expect_response(
                    lambda r: r.request.method == "POST"
                    and r.url == BASE + "/api/resident/chat/sessions"
                ) as created:
                    await page.get_by_role(
                        "button", name="Nova conversa", exact=True
                    ).click()
                response = await created.value
                assert response.status == 201, "Session creation failed"
                sid = (await response.json())["id"]
                await page.get_by_label("Mensagem", exact=True).fill(text)
                try:
                    async with page.expect_response(
                        lambda r: r.url
                        == BASE + "/api/resident/chat/sessions/" + sid + "/messages",
                        timeout=95000,
                    ) as sent:
                        await page.get_by_role(
                            "button", name="Enviar", exact=True
                        ).click()
                    response = await sent.value
                    if response.status == 429:
                        raise RuntimeError("QUOTA_429_STOP_NO_RETRY")
                    assert response.status == 200, "Chat failed; stop without retry"
                    return sid, await response.json()
                finally:
                    last_call = time.monotonic()

            cases = (
                ("deny", "approve", "visitor") if args.case == "all" else (args.case,)
            )
            for kind in cases:
                offset = {"deny": 0, "approve": 1, "visitor": 2}[kind]
                day = (args.first_day + timedelta(days=offset)).isoformat()
                name = "Visitante Playwright QA " + day
                projection_kind = "visits" if kind == "visitor" else "reservations"
                assert not await projection(projection_kind, day, name), (
                    "Fixture already exists; select new date, do not retry"
                )
                text = (
                    f"Quero autorizar a visita de {name} no dia {day}. Solicite minha confirmação antes de liberar."
                    if kind == "visitor"
                    else f"Quero reservar o salão de festas para {day}. Mostre a taxa e peça minha confirmação antes de reservar."
                )
                sid, payload = await send(text)
                expected_action = (
                    "autorizar_visitante" if kind == "visitor" else "reservar_area"
                )
                pending = [
                    item
                    for item in payload.get("confirmacoes_pendentes", [])
                    if item["acao"] == expected_action
                    and item["detalhes"].get("data") == day
                ]
                assert len(pending) == 1, (
                    "Expected exact confirmation was not returned; stop without extra model call"
                )
                item = pending[0]
                if kind == "visitor":
                    assert item["detalhes"].get("nome") == name, "Visitor mismatch"
                else:
                    assert item["detalhes"].get("area") == "salao-de-festas", (
                        "Area mismatch"
                    )
                    assert (
                        isinstance(item["detalhes"].get("taxa"), (int, float))
                        and item["detalhes"]["taxa"] > 0
                    ), "Missing positive fee"
                card = page.get_by_role(
                    "region", name="Confirmação pendente", exact=True
                ).filter(has_text=day)
                await expect(card).to_have_count(1)
                await expect(card).to_contain_text(
                    name if kind == "visitor" else "salao-de-festas"
                )
                assert not await projection(projection_kind, day, name), (
                    "Effect happened before UI confirmation"
                )
                decision = kind != "deny"
                endpoint = (
                    BASE + "/api/resident/chat/sessions/" + sid + "/confirmations"
                )
                async with page.expect_response(
                    lambda r: r.url == endpoint, timeout=95000
                ) as completed:
                    await card.get_by_role(
                        "button", name="Aprovar" if decision else "Negar", exact=True
                    ).click()
                response = await completed.value
                assert response.request.post_data_json == {
                    "id": item["id"],
                    "confirmado": decision,
                }, "Client sent unexpected confirmation fields"
                if response.status == 429:
                    raise RuntimeError("QUOTA_429_STOP_NO_RETRY")
                assert response.status == 200, (
                    "Confirmation failed; consult projections, do not retry"
                )
                answer = await response.json()
                expected = (
                    "rejected"
                    if not decision
                    else "authorized"
                    if kind == "visitor"
                    else "reserved"
                )
                assert answer.get("resultado", {}).get("status") == expected, (
                    "Authoritative outcome differs from requested UI decision"
                )
                values = await projection(projection_kind, day, name)
                assert len(values) == (1 if decision else 0), (
                    "Projection does not match confirmed outcome"
                )
                if kind == "approve":
                    result = answer["resultado"]
                    code = result.get("codigo", result.get("code"))
                    assert code and values[0]["code"] == code, (
                        "Reservation code differs from committed projection"
                    )
                await expect(card).to_have_count(0)
                observations.append(
                    {
                        "case": kind,
                        "date": day,
                        "status": "PASS",
                        "ui_decision_verified": True,
                        "authoritative_status": answer["resultado"]["status"],
                        "committed_projection_verified": True,
                    }
                )
                print("PASS UI " + kind, flush=True)
        finally:
            token = None
            await context.close()
            await browser.close()
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required explicit execution slot; real Gemini may incur usage",
    )
    parser.add_argument("--first-day", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--case", choices=("deny", "approve", "visitor", "all"), default="deny"
    )
    parser.add_argument("--min-gap", type=int, default=65)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error(
            "Prepared only; pass --execute after coordinator assigns exclusive Gemini slot."
        )
    if args.min_gap < 60:
        parser.error("Minimum gap is 60 seconds; no parallel Gemini runs.")
    try:
        cases = asyncio.run(run(args))
        report = {
            "target": "official isolated portal 8803",
            "model": "real configured provider; no mocks",
            "status": "PASS",
            "cases": cases,
        }
        code = 0
    except Exception as exc:
        # Browser errors may include page/input content. Never print raw exception.
        report = {
            "target": "official isolated portal 8803",
            "status": "STOP",
            "error_type": type(exc).__name__,
            "reason": "QUOTA_429_STOP_NO_RETRY"
            if str(exc) == "QUOTA_429_STOP_NO_RETRY"
            else "Execution stopped without retries; inspect authorized projections before resuming.",
        }
        code = 1
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(report["status"], flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
