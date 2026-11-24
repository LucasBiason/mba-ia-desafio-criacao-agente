"""Real ADK/SQLite/API; deterministic injected model, never a Gemini call."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from services.agent.api.api import create_app, prepare_domain_tables
from services.agent.api.domain import AcademicDomain

ROOT = Path(__file__).resolve().parents[3]


class AcademicFake(BaseLlm):
    model: str = "offline-academic-test"
    role: str

    async def generate_content_async(self, llm_request, stream=False):
        parts = llm_request.contents[-1].parts or []
        responses = [p.function_response for p in parts if p.function_response]
        texts = [
            p.text
            for c in llm_request.contents
            if c.role == "user"
            for p in c.parts or []
            if p.text and "<<<BEGIN_QUOTED_AGENT_CONTENT>>>" not in p.text
        ]
        command = json.loads(texts[-1])
        target = (
            "convivencia"
            if command["tool"]
            in ("autorizar_visitante", "listar_visitantes", "consultar_regulamento")
            else "reservas"
        )
        if self.role == "principal":
            part = types.Part(
                function_call=types.FunctionCall(
                    name="transfer_to_agent", args={"agent_name": target}
                )
            )
        elif self.role != target and not responses:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="transfer_to_agent", args={"agent_name": "principal"}
                )
            )
        elif responses:
            part = types.Part(
                text=json.dumps(responses[-1].response, ensure_ascii=False)
            )
        else:
            part = types.Part(
                function_call=types.FunctionCall(
                    name=command["tool"], args=command.get("args", {})
                )
            )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


class AcademicApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.domain = AcademicDomain(self.path / "domain.db")
        self.domain.initialize(ROOT / "dados")
        prepare_domain_tables(self.domain)
        prepared = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{self.path}/adk.db"
        )
        await prepared.prepare_tables()
        await prepared.close()
        self.models = {
            role: AcademicFake(role=role)
            for role in ("principal", "reservas", "convivencia")
        }
        self.apps = []
        self.clients = []
        self.client = self.new_client()
        self.network = patch(
            "socket.socket.connect",
            side_effect=AssertionError("No provider/network allowed"),
        )
        self.network.start()

    def new_client(self):
        app = create_app(
            domain=self.domain,
            session_url=f"sqlite+aiosqlite:///{self.path}/adk.db",
            models=self.models,
            regulation=(ROOT / "dados/regulamento.md").read_text(),
        )
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://academic"
        )
        self.apps.append(app)
        self.clients.append(client)
        return client

    async def asyncTearDown(self):
        self.network.stop()
        for client in self.clients:
            await client.aclose()
        for app in self.apps:
            await app.state.session_service.close()
        self.temp.cleanup()

    async def session(self, apartment="101"):
        response = await self.client.post("/sessoes", json={"apartamento": apartment})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["session_id"]

    async def message(self, sid, tool, **args):
        response = await self.client.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": json.dumps({"tool": tool, "args": args})},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def approve(self, sid, id, confirmed=True):
        return await self.client.post(
            f"/sessoes/{sid}/confirmacoes", json={"id": id, "confirmado": confirmed}
        )

    async def test_paid_confirmation_resumes_specialist_after_restart_once(self):
        sid = await self.session()
        result = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2030-04-20"
        )
        self.assertEqual(len(result["confirmacoes_pendentes"]), 1, result)
        confirmation = result["confirmacoes_pendentes"][0]
        self.assertNotIn("2030-04-20", str(self.domain.reservations("101")))
        await self.apps[0].state.session_service.close()
        self.client = self.new_client()
        response = await self.approve(sid, confirmation["id"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["confirmacoes_pendentes"], [])
        self.assertEqual(
            sum(r["data"] == "2030-04-20" for r in self.domain.reservations("101")), 1
        )
        replay = await self.approve(sid, confirmation["id"])
        self.assertEqual(replay.status_code, 409)
        events = (await self.client.get(f"/sessoes/{sid}/eventos")).json()
        calls = [
            (e["author"], p["function_call"]["name"])
            for e in events
            for p in e.get("content", {}).get("parts", [])
            if "function_call" in p
        ]
        self.assertIn(("principal", "transfer_to_agent"), calls)
        self.assertIn(("reservas", "adk_request_confirmation"), calls)
        self.assertIn("reserved", json.dumps(events))

    async def test_denial_foreign_unknown_and_strict_bool(self):
        sid = await self.session()
        other = await self.session()
        result = await self.message(
            sid, "autorizar_visitante", nome="Joana Ribeiro", data="2030-04-21"
        )
        id = result["confirmacoes_pendentes"][0]["id"]
        self.assertEqual((await self.approve(other, id)).status_code, 409)
        self.assertEqual((await self.approve(sid, "unknown")).status_code, 409)
        response = await self.client.post(
            f"/sessoes/{sid}/confirmacoes", json={"id": id, "confirmado": "true"}
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual((await self.approve(sid, id, False)).status_code, 200)
        self.assertNotIn("Joana Ribeiro", str(self.domain.visitors("101")))
        self.assertEqual((await self.approve(sid, id)).status_code, 409)
        for suffix in ("eventos", "mensagens", "confirmacoes"):
            if suffix == "eventos":
                r = await self.client.get("/sessoes/absent/" + suffix)
            else:
                r = await self.client.post(
                    "/sessoes/absent/" + suffix,
                    json={"texto": "x"}
                    if suffix == "mensagens"
                    else {"id": "x", "confirmado": True},
                )
            self.assertEqual(r.status_code, 404)

    async def test_free_reserve_cancel_and_regulation(self):
        sid = await self.session()
        result = await self.message(
            sid, "reservar_area", area="quadra", data="2030-04-20"
        )
        self.assertEqual(result["confirmacoes_pendentes"], [])
        self.assertIn("2030-04-20", str(self.domain.reservations("101")))
        await self.message(sid, "cancelar_reserva", area="quadra", data="2030-04-20")
        self.assertNotIn("2030-04-20", str(self.domain.reservations("101")))
        new = await self.session()
        response = await self.message(
            new,
            "consultar_regulamento",
            pergunta="Horário de fechamento piscina domingos",
        )
        self.assertIn("20h", response["resposta"])
        events = (await self.client.get(f"/sessoes/{new}/eventos")).json()
        self.assertNotIn("Capítulo XI", str(events))
        self.assertNotIn("Art. 29", str(events))

    async def test_evaluator_vertical_sequence_with_injected_model(self):
        # HTTP/data/event guarantees; not a natural-language/Gemini evaluation.
        sid = await self.session()
        first = await self.message(sid, "listar_reservas")
        self.assertIn("RSV-1377", first["resposta"])
        self.assertNotIn("RSV-4821", first["resposta"])
        visitors = await self.message(sid, "listar_visitantes")
        self.assertNotIn("Marina Duarte", visitors["resposta"])
        await self.message(
            sid, "cancelar_reserva", area="salao-de-festas", data="2030-03-16"
        )
        self.assertIn("RSV-4821", str(self.domain.reservations("302")))
        await self.message(sid, "cancelar_reserva", area="quadra", data="2030-03-09")
        await self.message(sid, "reservar_area", area="quadra", data="2030-04-06")
        denied = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2030-04-20"
        )
        self.assertEqual(
            (
                await self.approve(
                    sid, denied["confirmacoes_pendentes"][0]["id"], False
                )
            ).status_code,
            200,
        )
        self.assertNotIn("2030-04-20", str(self.domain.reservations("101")))
        paid = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2030-04-20"
        )
        self.assertEqual(
            (
                await self.approve(sid, paid["confirmacoes_pendentes"][0]["id"])
            ).status_code,
            200,
        )
        self.assertEqual(
            (
                await self.approve(sid, paid["confirmacoes_pendentes"][0]["id"])
            ).status_code,
            409,
        )
        occupied = await self.message(
            await self.session(),
            "reservar_area",
            area="salao-de-festas",
            data="2030-03-16",
        )
        self.assertIn("occupied", occupied["resposta"])
        self.assertNotIn("302", occupied["resposta"])
        visit = await self.message(
            sid, "autorizar_visitante", nome="Joana Ribeiro", data="2030-04-21"
        )
        self.assertNotIn("Joana Ribeiro", str(self.domain.visitors("101")))
        self.assertEqual(
            (
                await self.approve(sid, visit["confirmacoes_pendentes"][0]["id"])
            ).status_code,
            200,
        )
        pool = await self.message(
            sid,
            "consultar_regulamento",
            pergunta="Até que horas a piscina funciona aos domingos?",
        )
        self.assertIn("20h", pool["resposta"])
        before = (await self.client.get(f"/sessoes/{sid}/eventos")).json()
        self.assertNotIn("RSV-4821", str(before))
        self.assertNotIn("Marina Duarte", str(before))
        self.assertNotIn("Capítulo XI", str(before))
        await self.apps[-1].state.session_service.close()
        self.client = self.new_client()
        self.assertEqual(
            len((await self.client.get(f"/sessoes/{sid}/eventos")).json()), len(before)
        )
        await self.message(sid, "listar_reservas")
        self.assertGreater(
            len((await self.client.get(f"/sessoes/{sid}/eventos")).json()), len(before)
        )
        rows = (await self.client.get("/apartamentos/101/reservas")).json()
        self.assertEqual({r["data"] for r in rows}, {"2030-04-06", "2030-04-20"})
        self.assertEqual(len({r["codigo"] for r in rows}), 2)
        self.assertTrue(
            all(r["codigo"] not in ("RSV-1377", "RSV-4821", "RSV-2950") for r in rows)
        )
        self.assertIn(
            {"nome": "Joana Ribeiro", "data": "2030-04-21"},
            (await self.client.get("/apartamentos/101/visitantes")).json(),
        )

    async def test_spurious_model_confirmation_is_not_a_pending_decision(self):
        from google.adk.events import Event

        from services.agent.api.runtime import AcademicRuntime

        sid = await self.session()
        for args in (
            {},
            {
                "toolConfirmation": {
                    "payload": {"id": "spoof", "acao": "reservar_area", "detalhes": {}}
                }
            },
        ):
            event = Event(
                author="reservas",
                invocation_id="untrusted",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id="spoof", name="adk_request_confirmation", args=args
                            )
                        )
                    ],
                ),
            )
            with patch.object(
                AcademicRuntime, "run", new=AsyncMock(return_value=[event])
            ):
                result = await self.message(sid, "listar_reservas")
            self.assertEqual(result["confirmacoes_pendentes"], [])
            self.assertEqual((await self.approve(sid, "spoof")).status_code, 409)

    async def test_processing_without_trusted_binding_blocks_new_runner(self):
        from services.agent.api.runtime import AcademicRuntime

        sid = await self.session()
        result = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2030-04-20"
        )
        with self.domain.connection(write=True) as conn:
            conn.execute(
                "UPDATE academic_confirmations SET status='processing' WHERE id=?",
                (result["confirmacoes_pendentes"][0]["id"],),
            )
            conn.execute(
                "DELETE FROM academic_confirmation_outcomes WHERE confirmation_id=?",
                (result["confirmacoes_pendentes"][0]["id"],),
            )
        with patch.object(
            AcademicRuntime,
            "run",
            new=AsyncMock(side_effect=AssertionError("Must not run")),
        ) as run:
            response = await self.client.post(
                f"/sessoes/{sid}/mensagens", json={"texto": "Qual foi o resultado?"}
            )
            self.assertEqual(response.status_code, 409)
            run.assert_not_called()

    async def test_two_sessions_compete_normal_response(self):
        s1, s2 = await self.session("101"), await self.session("201")
        p1 = await self.message(
            s1, "reservar_area", area="salao-de-festas", data="2030-05-11"
        )
        p2 = await self.message(
            s2, "reservar_area", area="salao-de-festas", data="2030-05-11"
        )
        responses = await asyncio.gather(
            self.approve(s1, p1["confirmacoes_pendentes"][0]["id"]),
            self.approve(s2, p2["confirmacoes_pendentes"][0]["id"]),
        )
        self.assertEqual(
            [r.status_code for r in responses], [200, 200], [r.text for r in responses]
        )
        rows = self.domain.reservations("101") + self.domain.reservations("201")
        self.assertEqual(sum(r["data"] == "2030-05-11" for r in rows), 1)

    async def test_confirmation_receipt_mapping_matches_actual_adk_tool_id(self):
        sid = await self.session()
        proposed = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2033-01-01"
        )
        cid = proposed["confirmacoes_pendentes"][0]["id"]
        response = await self.approve(sid, cid)
        self.assertEqual(response.status_code, 200, response.text)
        result = json.loads(response.json()["resposta"])
        with self.domain.connection() as conn:
            binding = conn.execute(
                "SELECT * FROM academic_confirmation_outcomes WHERE confirmation_id=?",
                (cid,),
            ).fetchone()
            receipt = conn.execute(
                "SELECT * FROM receipts WHERE operation_id=?",
                (binding["operation_id"],),
            ).fetchone()
        self.assertEqual(binding["session_id"], sid)
        self.assertEqual(receipt["apartment"], "101")
        self.assertEqual(result["codigo"], json.loads(receipt["result"])["codigo"])
        self.assertEqual(json.loads(binding["result"]), json.loads(receipt["result"]))
        events = (await self.client.get(f"/sessoes/{sid}/eventos")).json()
        originals = [
            part["function_call"]["args"]["originalFunctionCall"]["id"]
            for event in events
            for part in event.get("content", {}).get("parts", [])
            if part.get("function_call", {}).get("name") == "adk_request_confirmation"
        ]
        self.assertIn(binding["operation_id"], originals)

    async def test_postcommit_model_failure_recovers_paid_and_visitor_receipt(self):
        original = AcademicFake.generate_content_async

        async def fail_after_commit(model, llm_request, stream=False):
            responses = [
                p.function_response
                for p in llm_request.contents[-1].parts or []
                if p.function_response
            ]
            if any(
                r.response.get("status") in ("reserved", "authorized")
                for r in responses
            ):
                raise RuntimeError(
                    "provider failed after committed effect before final text"
                )
            async for value in original(model, llm_request, stream):
                yield value

        for tool, args, expected in (
            (
                "reservar_area",
                {"area": "salao-de-festas", "data": "2033-02-01"},
                "reserved",
            ),
            (
                "autorizar_visitante",
                {"nome": "Visitante sintético QA", "data": "2033-02-02"},
                "authorized",
            ),
        ):
            sid = await self.session()
            proposal = await self.message(sid, tool, **args)
            cid = proposal["confirmacoes_pendentes"][0]["id"]
            with patch.object(
                AcademicFake, "generate_content_async", new=fail_after_commit
            ):
                response = await self.approve(sid, cid)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                json.loads(response.json()["resposta"])["status"], expected
            )
            self.assertEqual((await self.approve(sid, cid)).status_code, 409)
            with self.domain.connection() as conn:
                row = conn.execute(
                    "SELECT status FROM academic_confirmations WHERE id=?", (cid,)
                ).fetchone()
            self.assertEqual(row["status"], "consumed")

    async def test_model_success_without_receipt_is_not_accepted(self):
        from google.adk.events import Event

        from services.agent.api.runtime import AcademicRuntime

        sid = await self.session()
        proposal = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2033-03-01"
        )
        cid = proposal["confirmacoes_pendentes"][0]["id"]
        event = Event(
            author="reservas",
            content=types.Content(
                role="model", parts=[types.Part(text="Reserva concluída com sucesso!")]
            ),
        )
        with patch.object(AcademicRuntime, "run", new=AsyncMock(return_value=[event])):
            response = await self.approve(sid, cid)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertNotIn("Reserva concluída", response.text)
        self.assertFalse(
            any(r["data"] == "2033-03-01" for r in self.domain.reservations("101"))
        )
        self.assertEqual((await self.approve(sid, cid)).status_code, 409)

    async def test_free_cancel_busy_invalid_and_foreign_ignore_lying_final_text(self):
        original = AcademicFake.generate_content_async

        async def lie(model, request, stream=False):
            async for value in original(model, request, stream):
                if value.content:
                    for part in value.content.parts or []:
                        if part.text:
                            part.text = "Tudo reservado e cancelado com sucesso, inclusive apartamento 302!"
                yield value

        cases = [
            ("reservar_area", {"area": "quadra", "data": "2034-01-01"}, "reserved"),
            ("cancelar_reserva", {"area": "quadra", "data": "2030-03-09"}, "cancelled"),
            (
                "cancelar_reserva",
                {"area": "salao-de-festas", "data": "2030-03-16"},
                "not_found",
            ),
            (
                "reservar_area",
                {"area": "salao-de-festas", "data": "2030-03-16"},
                "occupied",
            ),
            ("reservar_area", {"area": "quadra", "data": "bad-date"}, "invalid_date"),
        ]
        with patch.object(AcademicFake, "generate_content_async", new=lie):
            for tool, args, expected in cases:
                sid = await self.session()
                result = await self.message(sid, tool, **args)
                self.assertEqual(json.loads(result["resposta"])["status"], expected)
                self.assertNotIn("inclusive apartamento", result["resposta"])
        self.assertTrue(
            any(r["codigo"] == "RSV-4821" for r in self.domain.reservations("302"))
        )
        self.assertFalse(
            any(r["codigo"] == "RSV-1377" for r in self.domain.reservations("101"))
        )

    async def test_free_mutation_without_receipt_or_matching_tool_response_fails_closed(
        self,
    ):
        from google.adk.events import Event

        from services.agent.api.runtime import AcademicRuntime

        sid = await self.session()
        call = Event(
            author="reservas",
            invocation_id="test-invocation",
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="no-receipt",
                            name="reservar_area",
                            args={"area": "quadra", "data": "2034-02-01"},
                        )
                    )
                ],
            ),
        )
        response = Event(
            author="reservas",
            invocation_id="test-invocation",
            content=types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id="no-receipt",
                            name="reservar_area",
                            response={"status": "reserved", "codigo": "not-real"},
                        )
                    )
                ],
            ),
        )
        for events in ([call], [call, response]):
            with patch.object(
                AcademicRuntime, "run", new=AsyncMock(return_value=events)
            ):
                answer = await self.client.post(
                    f"/sessoes/{sid}/mensagens", json={"texto": "Teste isolado"}
                )
            self.assertEqual(answer.status_code, 503, answer.text)
            self.assertNotIn("not-real", answer.text)
        self.assertFalse(
            any(r["data"] == "2034-02-01" for r in self.domain.reservations("101"))
        )

    async def test_pre_effect_failure_restart_reconciles_with_terminal_fence(self):
        from services.agent.api.runtime import AcademicRuntime

        sid = await self.session()
        proposal = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2039-04-20"
        )
        cid = proposal["confirmacoes_pendentes"][0]["id"]
        with patch.object(
            AcademicRuntime,
            "run",
            new=AsyncMock(side_effect=RuntimeError("provider before effect")),
        ):
            self.assertEqual((await self.approve(sid, cid)).status_code, 503)
        self.client = self.new_client()
        result = await self.client.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": json.dumps({"tool": "listar_reservas"})},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual((await self.approve(sid, cid)).status_code, 409)
        with self.domain.connection() as conn:
            binding = conn.execute(
                "SELECT * FROM academic_confirmation_outcomes WHERE confirmation_id=?",
                (cid,),
            ).fetchone()
        delayed = self.domain.apply_confirmed(
            "101",
            binding["action"],
            json.loads(binding["payload"]),
            operation_id=binding["operation_id"],
        )
        self.assertEqual(delayed["status"], "interrupted")
        self.assertFalse(
            any(r["data"] == "2039-04-20" for r in self.domain.reservations("101"))
        )

    async def test_live_confirmation_cannot_be_reconciled_by_second_app(self):
        from services.agent.api.runtime import AcademicRuntime

        sid = await self.session()
        proposal = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2039-05-20"
        )
        cid = proposal["confirmacoes_pendentes"][0]["id"]
        entered = asyncio.Event()
        release = asyncio.Event()

        async def paused(*args, **kwargs):
            entered.set()
            await release.wait()
            raise RuntimeError("before effect")

        with patch.object(AcademicRuntime, "run", new=paused):
            task = asyncio.create_task(self.approve(sid, cid))
            await entered.wait()
            other = self.new_client()
            blocked = await other.post(
                f"/sessoes/{sid}/mensagens", json={"texto": "listar"}
            )
            self.assertEqual(blocked.status_code, 409)
            with self.domain.connection() as conn:
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) AS n FROM receipts").fetchone()["n"],
                    0,
                )
            release.set()
            self.assertEqual((await task).status_code, 503)

    async def test_foreign_receipt_blocks_reconciliation(self):
        sid = await self.session()
        proposal = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2039-06-20"
        )
        cid = proposal["confirmacoes_pendentes"][0]["id"]
        with self.domain.connection(write=True) as conn:
            binding = conn.execute(
                "SELECT * FROM academic_confirmation_outcomes WHERE confirmation_id=?",
                (cid,),
            ).fetchone()
            conn.execute(
                "UPDATE academic_confirmations SET status='processing' WHERE id=?",
                (cid,),
            )
            conn.execute(
                "INSERT INTO receipts VALUES(?,?,?,?,?)",
                (
                    binding["operation_id"],
                    "201",
                    "paid_reservation",
                    binding["payload"],
                    json.dumps({"status": "reserved", "codigo": "PRIVATE"}),
                ),
            )
        response = await self.client.post(
            f"/sessoes/{sid}/mensagens", json={"texto": "listar"}
        )
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("PRIVATE", response.text)
        with self.domain.connection() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT status FROM academic_confirmations WHERE id=?", (cid,)
                ).fetchone()["status"],
                "processing",
            )

    async def test_restart_recovers_exact_committed_receipt_without_reexecution(self):
        sid = await self.session()
        proposal = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2039-07-20"
        )
        cid = proposal["confirmacoes_pendentes"][0]["id"]
        self.assertEqual((await self.approve(sid, cid)).status_code, 200)
        before = self.domain.reservations("101")
        with self.domain.connection(write=True) as conn:
            conn.execute(
                "UPDATE academic_confirmations SET status='processing' WHERE id=?",
                (cid,),
            )
        self.client = self.new_client()
        answer = await self.client.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": json.dumps({"tool": "listar_reservas"})},
        )
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(self.domain.reservations("101"), before)
        self.assertEqual((await self.approve(sid, cid)).status_code, 409)

    async def test_rejected_outcome_restart_remains_rejected(self):
        sid = await self.session()
        proposal = await self.message(
            sid, "reservar_area", area="salao-de-festas", data="2039-08-20"
        )
        cid = proposal["confirmacoes_pendentes"][0]["id"]
        answer = await self.client.post(
            f"/sessoes/{sid}/confirmacoes", json={"id": cid, "confirmado": False}
        )
        self.assertEqual(answer.status_code, 200, answer.text)
        with self.domain.connection(write=True) as conn:
            conn.execute(
                "UPDATE academic_confirmations SET status='processing' WHERE id=?",
                (cid,),
            )
        self.client = self.new_client()
        answer = await self.client.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": json.dumps({"tool": "listar_reservas"})},
        )
        self.assertEqual(answer.status_code, 200, answer.text)
        with self.domain.connection() as conn:
            result = conn.execute(
                "SELECT result FROM academic_confirmation_outcomes WHERE confirmation_id=?",
                (cid,),
            ).fetchone()["result"]
        self.assertEqual(json.loads(result), {"status": "rejected"})
        self.assertEqual((await self.approve(sid, cid)).status_code, 409)
        self.assertFalse(
            any(r["data"] == "2039-08-20" for r in self.domain.reservations("101"))
        )

    async def test_orphan_durable_adk_proposal_recovers_exact_id_after_restart(self):
        from services.agent.api.runtime import AcademicRuntime

        original = AcademicRuntime.run
        captured = []

        async def crash_after_persist(runtime, *args, **kwargs):
            events = await original(runtime, *args, **kwargs)
            captured.extend(events)
            raise RuntimeError("crash after ADK persisted before API collect")

        sid = await self.session()
        with patch.object(AcademicRuntime, "run", new=crash_after_persist):
            answer = await self.client.post(
                f"/sessoes/{sid}/mensagens",
                json={
                    "texto": json.dumps(
                        {
                            "tool": "reservar_area",
                            "args": {"area": "salao-de-festas", "data": "2039-09-20"},
                        }
                    )
                },
            )
        self.assertEqual(answer.status_code, 503)
        cid = next(
            call.id
            for e in captured
            for call in e.get_function_calls()
            if call.name == "adk_request_confirmation"
        )
        with self.domain.connection() as conn:
            self.assertIsNone(
                conn.execute(
                    "SELECT id FROM academic_confirmations WHERE id=?", (cid,)
                ).fetchone()
            )
        self.assertFalse(
            any(r["data"] == "2039-09-20" for r in self.domain.reservations("101"))
        )
        self.client = self.new_client()
        other = await self.session("201")
        self.assertEqual((await self.approve(other, cid)).status_code, 409)
        self.assertEqual((await self.approve(sid, "random")).status_code, 409)
        answer = await self.approve(sid, cid)
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(
            sum(r["data"] == "2039-09-20" for r in self.domain.reservations("101")), 1
        )
        self.assertEqual((await self.approve(sid, cid)).status_code, 409)

    async def test_persisted_confirmation_name_without_real_tool_provenance_is_rejected(
        self,
    ):
        from google.adk.events import Event

        from services.agent.api.runtime import APP_NAME, USER_ID

        sid = await self.session()
        service = self.apps[-1].state.session_service
        session = await service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=sid
        )
        fake = Event(
            author="reservas",
            invocation_id="fake-invocation",
            long_running_tool_ids={"fake-confirmation"},
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="fake-confirmation",
                            name="adk_request_confirmation",
                            args={
                                "originalFunctionCall": {
                                    "id": "no-real-operation",
                                    "name": "reservar_area",
                                    "args": {
                                        "area": "salao-de-festas",
                                        "data": "2039-10-20",
                                    },
                                },
                                "toolConfirmation": {
                                    "payload": {
                                        "acao": "reservar_area",
                                        "detalhes": {
                                            "area": "salao-de-festas",
                                            "data": "2039-10-20",
                                            "taxa": 150,
                                        },
                                    }
                                },
                            },
                        )
                    )
                ],
            ),
        )
        await service.append_event(session=session, event=fake)
        self.assertEqual(
            (await self.approve(sid, "fake-confirmation")).status_code, 409
        )
        with self.domain.connection() as conn:
            self.assertIsNone(
                conn.execute(
                    "SELECT id FROM academic_confirmations WHERE id='fake-confirmation'"
                ).fetchone()
            )
        self.assertFalse(
            any(r["data"] == "2039-10-20" for r in self.domain.reservations("101"))
        )
