"""Explicit restore against disposable stores only; no provider calls."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from services.agent.api.api import prepare_domain_tables
from services.agent.api.domain import AcademicDomain

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "dados"


class AcademicRestoreTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(TemporaryDirectory()))
        self.domain = AcademicDomain(self.folder / "domain.db")
        self.domain.initialize(FIXTURES)
        prepare_domain_tables(self.domain)

    def mutate(self):
        bound = self.domain.tools("101")
        bound.cancelar_reserva("quadra", "2030-03-09", operation_id="cancel-seed")
        created = bound.reservar_area(
            "quadra", "2030-04-06", operation_id="new-booking"
        )
        proposal = bound.preparar_visita("Joana Ribeiro", "2030-04-21")
        self.domain.apply_confirmed(
            "101", proposal["acao"], proposal["detalhes"], operation_id="visit"
        )
        with self.domain.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO academic_sessions VALUES(?,?)", ("old-session", "101")
            )
            conn.execute(
                "INSERT INTO academic_confirmations VALUES(?,?,?,?,?)",
                ("old-confirmation", "old-session", "old-invocation", "{}", "pending"),
            )
        return created

    def test_restore_resets_projections_invalidates_pending_and_keeps_snapshot_and_codes(
        self,
    ):
        created = self.mutate()
        before = {
            name: (FIXTURES / name).read_bytes()
            for name in ("reservas.json", "visitantes.json")
        }
        snapshot_id = self.domain.restore(FIXTURES)
        self.assertEqual(
            self.domain.reservations("101"),
            [{"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}],
        )
        self.assertEqual(self.domain.visitors("101"), [])
        self.assertEqual(
            self.domain.visitors("302"),
            [{"nome": "Marina Duarte", "data": "2030-03-16"}],
        )
        with self.domain.connection() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM academic_sessions").fetchone()[0], 0
            )
            self.assertEqual(
                conn.execute("SELECT count(*) FROM academic_confirmations").fetchone()[
                    0
                ],
                0,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT active FROM reservations WHERE code=?", (created["codigo"],)
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("SELECT count(*) FROM receipts").fetchone()[0], 3
            )
            snapshot = json.loads(
                conn.execute(
                    "SELECT payload FROM academic_restore_snapshots WHERE id=?",
                    (snapshot_id,),
                ).fetchone()[0]
            )
        self.assertTrue(
            any(row["name"] == "Joana Ribeiro" for row in snapshot["visitors"])
        )
        self.assertEqual(
            snapshot["academic_confirmations"][0]["id"], "old-confirmation"
        )
        for name, content in before.items():
            self.assertEqual((FIXTURES / name).read_bytes(), content)

    def test_restore_refuses_mixed_database_without_changing_any_data(self):
        self.mutate()
        with self.domain.connection(write=True) as conn:
            conn.execute("CREATE TABLE portal_accounts (id TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO portal_accounts VALUES('untouched')")
        with self.assertRaisesRegex(ValueError, "não acadêmicas"):
            self.domain.restore(FIXTURES)
        self.assertIn("Joana Ribeiro", str(self.domain.visitors("101")))
        with self.domain.connection() as conn:
            self.assertEqual(
                conn.execute("SELECT id FROM portal_accounts").fetchone()[0],
                "untouched",
            )

    def test_invalid_fixture_rolls_back_reset_and_snapshot_together(self):
        self.mutate()
        invalid = self.folder / "invalid-fixtures"
        invalid.mkdir()
        (invalid / "reservas.json").write_text(
            json.dumps(
                [
                    {
                        "codigo": "RSV-1377",
                        "apartamento": "201",
                        "area": "quadra",
                        "data": "2030-03-09",
                    }
                ]
            )
        )
        (invalid / "visitantes.json").write_text("[]")
        with self.assertRaisesRegex(ValueError, "outra reserva"):
            self.domain.restore(invalid)
        self.assertIn("Joana Ribeiro", str(self.domain.visitors("101")))
        with self.domain.connection() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM academic_sessions").fetchone()[0], 1
            )
            self.assertIsNone(
                conn.execute(
                    "SELECT name FROM sqlite_master WHERE name='academic_restore_snapshots'"
                ).fetchone()
            )

    def test_cli_requires_deliberate_restore_flag_and_resets_same_directory(self):
        self.mutate()
        command = [
            sys.executable,
            "-m",
            "services.agent.api",
            "restore",
            "--data-dir",
            str(self.folder),
        ]
        env = {"PATH": str(Path(sys.executable).parent), "PYTHONPATH": str(ROOT)}
        refused = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn("--confirm-restore", refused.stderr)
        self.assertIn("Joana Ribeiro", str(self.domain.visitors("101")))
        restored = subprocess.run(
            command + ["--confirm-restore"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(self.domain.visitors("101"), [])
        self.assertIn("Snapshot:", restored.stdout)


if __name__ == "__main__":
    unittest.main()
