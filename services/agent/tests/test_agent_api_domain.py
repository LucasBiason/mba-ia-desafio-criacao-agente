"""Domínio acadêmico exercitado em SQLite descartável com fixtures intactas."""

import os
import sqlite3
import unittest
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from tempfile import TemporaryDirectory

from services.agent.api.domain import AcademicDomain

FIXTURES = Path(__file__).resolve().parents[3] / "dados"


_APPROVAL_BARRIER = None


def _worker_init(barrier):
    global _APPROVAL_BARRIER
    _APPROVAL_BARRIER = barrier


def _approve_in_process(path, apartment, details):
    if _APPROVAL_BARRIER is not None:
        _APPROVAL_BARRIER.wait(timeout=10)
    result = AcademicDomain(path).apply_confirmed(
        apartment, "reservar_area", details, operation_id="approve-" + apartment
    )
    return os.getpid(), result


class AcademicDomainTest(unittest.TestCase):
    def setUp(self):
        self.folder = self.enterContext(TemporaryDirectory())
        self.path = Path(self.folder) / "academic.db"
        self.domain = AcademicDomain(self.path)
        self.assertTrue(self.domain.initialize(FIXTURES))
        self.bound = self.domain.tools("101")

    def test_seed_projection_and_reopen_do_not_replace_data(self):
        self.assertEqual(
            self.bound.listar_reservas()["reservas"],
            [
                {"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"},
            ],
        )
        self.assertEqual(
            self.domain.visitors("302"),
            [
                {"nome": "Marina Duarte", "data": "2030-03-16"},
            ],
        )
        cancelled = self.bound.cancelar_reserva(
            "quadra", "2030-03-09", operation_id="cancel"
        )
        self.assertEqual(cancelled, {"status": "cancelled"})
        reopened = AcademicDomain(self.path)
        self.assertFalse(reopened.initialize(FIXTURES))
        self.assertEqual(reopened.reservations("101"), [])
        with reopened.connection() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT active FROM reservations WHERE code='RSV-1377'"
                ).fetchone()[0],
                0,
            )

    def test_scope_no_foreign_codes_or_owners(self):
        self.assertEqual(self.bound.listar_visitantes(), {"visitantes": []})
        self.assertEqual(
            self.bound.cancelar_reserva(
                "Salão de festas", "2030-03-16", operation_id="foreign-cancel"
            ),
            {"status": "not_found"},
        )
        occupied = {"status": "occupied"}
        self.assertEqual(
            self.bound.consultar_disponibilidade("salao-de-festas", "2030-03-16"),
            occupied,
        )
        self.assertEqual(
            self.bound.reservar_area(
                "salao-de-festas", "2030-03-16", operation_id="foreign-attempt"
            ),
            occupied,
        )
        self.assertEqual(self.domain.reservations("302")[0]["codigo"], "RSV-4821")
        with self.assertRaises(ValueError):
            self.domain.tools("' OR 1=1 --")

    def test_free_reservation_replay_and_id_mismatch(self):
        values = ("quadra", "2030-04-06")
        first = self.bound.reservar_area(*values, operation_id="free-1")
        self.assertEqual(first["status"], "reserved")
        self.assertEqual(
            self.bound.reservar_area(*values, operation_id="free-1"), first
        )
        self.assertEqual(
            self.domain.tools("201").reservar_area(*values, operation_id="free-1"),
            {"status": "operation_conflict"},
        )
        self.assertEqual(
            self.bound.reservar_area("quadra", "2030-04-07", operation_id="free-1"),
            {"status": "operation_conflict"},
        )
        self.assertNotIn(first["codigo"], {"RSV-1377", "RSV-4821", "RSV-2950"})
        self.assertEqual(len(self.domain.reservations("101")), 2)

    def test_paid_and_visitor_untouched_until_trusted_path(self):
        paid = self.bound.reservar_area(
            "salao-de-festas", "2030-04-20", operation_id="paid"
        )
        visit = self.bound.preparar_visita("Joana Ribeiro", "2030-04-21")
        self.assertEqual(paid["status"], "confirmation_required")
        self.assertEqual(
            paid["detalhes"],
            {"area": "salao-de-festas", "data": "2030-04-20", "taxa": 150.0},
        )
        self.assertEqual(visit["status"], "confirmation_required")
        self.assertEqual(len(self.domain.reservations("101")), 1)
        self.assertEqual(self.domain.visitors("101"), [])
        previous = []
        for command in (paid, visit):
            result = self.domain.apply_confirmed(
                "101",
                command["acao"],
                command["detalhes"],
                operation_id=command["acao"],
            )
            previous.append(result)
            self.assertEqual(
                self.domain.apply_confirmed(
                    "101",
                    command["acao"],
                    command["detalhes"],
                    operation_id=command["acao"],
                ),
                result,
            )
        self.assertEqual([r["status"] for r in previous], ["reserved", "authorized"])
        self.assertEqual(len(self.domain.reservations("101")), 2)
        self.assertEqual(
            self.domain.visitors("101"),
            [{"nome": "Joana Ribeiro", "data": "2030-04-21"}],
        )

    def test_effect_and_receipt_rollback_together(self):
        command = self.bound.preparar_visita("Joana Ribeiro", "2030-04-21")
        with self.assertRaisesRegex(RuntimeError, "simulated"):
            with self.domain.connection(write=True) as conn:
                self.domain.execute_confirmed(
                    conn,
                    "101",
                    command["acao"],
                    command["detalhes"],
                    operation_id="crash",
                )
                raise RuntimeError("simulated")
        self.assertEqual(self.domain.visitors("101"), [])
        with self.domain.connection() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM receipts").fetchone()[0], 0
            )
        result = self.domain.apply_confirmed(
            "101", command["acao"], command["detalhes"], operation_id="crash"
        )
        self.assertEqual(result["status"], "authorized")

    def test_cross_process_unique_area_day(self):
        day = "2030-05-11"
        apartments = ("101", "201")
        details = []
        for apartment in apartments:
            proposal = self.domain.tools(apartment).reservar_area(
                "salao-de-festas", day, operation_id="proposal-" + apartment
            )
            self.assertEqual(proposal["status"], "confirmation_required")
            details.append(proposal["detalhes"])
        ctx = get_context("spawn")
        barrier = ctx.Barrier(2)
        with ProcessPoolExecutor(
            max_workers=2, mp_context=ctx, initializer=_worker_init, initargs=(barrier,)
        ) as pool:
            futures = [
                pool.submit(_approve_in_process, self.path, apartment, item)
                for apartment, item in zip(apartments, details)
            ]
            outcomes = [future.result(timeout=15) for future in futures]
        self.assertEqual(len({pid for pid, _ in outcomes}), 2)
        results = [result for _, result in outcomes]
        self.assertEqual(sorted(r["status"] for r in results), ["occupied", "reserved"])
        loser = results.index({"status": "occupied"})
        self.assertEqual(
            _approve_in_process(self.path, apartments[loser], details[loser])[1],
            {"status": "occupied"},
        )
        rows = [
            row
            for apt in apartments
            for row in self.domain.reservations(apt)
            if row["data"] == day
        ]
        self.assertEqual(len(rows), 1)

    def test_refuses_to_overwrite_existing_database(self):
        target = Path(self.folder) / "foreign.db"
        with sqlite3.connect(target) as conn:
            conn.execute("CREATE TABLE unrelated (value TEXT)")
            conn.execute("INSERT INTO unrelated VALUES ('preserved')")
        with self.assertRaisesRegex(ValueError, "banco existente"):
            AcademicDomain(target).initialize(FIXTURES)
        with sqlite3.connect(target) as conn:
            self.assertEqual(
                conn.execute("SELECT * FROM unrelated").fetchall(), [("preserved",)]
            )
