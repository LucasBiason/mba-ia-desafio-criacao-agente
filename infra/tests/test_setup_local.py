"""Setup regression tests use temporary files only, never the checkout .env."""

import importlib.util
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "setup_local", Path(__file__).resolve().parents[1] / "setup_local.py"
)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class LocalSetupTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / ".env"

    def test_fresh_private_complete_and_repeat_unchanged(self):
        self.assertEqual(setup.prepare_local(self.target), len(setup.VARIABLES))
        original = self.target.read_bytes()
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        self.assertEqual(setup.prepare_local(self.target), 0)
        self.assertEqual(self.target.read_bytes(), original)
        self.assertEqual(
            set(setup.ASSIGNMENT.findall(original.decode())), set(setup.VARIABLES)
        )

    def test_academic_file_preserved_without_final_newline(self):
        original = b"# academic\nGOOGLE_API_KEY=synthetic-only\nAURORA_MODEL=test-model"
        self.target.write_bytes(original)
        self.assertEqual(setup.prepare_local(self.target), len(setup.VARIABLES))
        self.assertTrue(self.target.read_bytes().startswith(original + b"\n"))
        completed = self.target.read_bytes()
        self.assertEqual(setup.prepare_local(self.target), 0)
        self.assertEqual(self.target.read_bytes(), completed)

    def test_existing_values_and_empty_assignments_not_overwritten(self):
        original = b"export AURORA_JWT_KEY='synthetic'\r\nAURORA_INTERNAL_TOKEN=\n"
        self.target.write_bytes(original)
        self.assertEqual(setup.prepare_local(self.target), len(setup.VARIABLES) - 2)
        self.assertTrue(self.target.read_bytes().startswith(original))
        names = setup.ASSIGNMENT.findall(self.target.read_text())
        self.assertEqual(len(names), len(set(names)))

    def test_copied_blank_example_completes_seven_secrets_and_keeps_google_key(self):
        empty_values = ("", "''", '""')
        content = (
            "# Example copied by evaluator\nGOOGLE_API_KEY=synthetic-google-only\n"
        )
        content += "OTHER_EMPTY=\n"
        content += "".join(
            f"{name}={empty_values[index % len(empty_values)]}\n"
            for index, name in enumerate(setup.VARIABLES)
        )
        self.target.write_text(content)
        self.assertEqual(
            setup.prepare_local(self.target, complete_empty=True), len(setup.VARIABLES)
        )
        completed = self.target.read_text()
        assignments = dict(
            line.split("=", 1) for line in completed.splitlines() if "=" in line
        )
        self.assertEqual(assignments["GOOGLE_API_KEY"], "synthetic-google-only")
        self.assertEqual(assignments["OTHER_EMPTY"], "")
        for name in setup.VARIABLES:
            self.assertRegex(assignments[name], r"^[0-9a-f]{48}$")
        names = setup.ASSIGNMENT.findall(completed)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(setup.prepare_local(self.target, complete_empty=True), 0)
        self.assertEqual(self.target.read_text(), completed)

    def test_complete_empty_preserves_nonempty_values_comments_and_crlf(self):
        original = (
            b"export AURORA_JWT_KEY='synthetic-kept'\r\n"
            b'AURORA_INTERNAL_TOKEN="" # keep explanation\r\n'
            b"DEMO_SUPER_PASSWORD=${EXTERNAL_VALUE}\r\n"
            b"GOOGLE_API_KEY=synthetic-google-only\r\n"
        )
        self.target.write_bytes(original)
        self.assertEqual(
            setup.prepare_local(self.target, complete_empty=True),
            len(setup.VARIABLES) - 2,
        )
        completed = self.target.read_bytes()
        self.assertTrue(
            completed.startswith(b"export AURORA_JWT_KEY='synthetic-kept'\r\n")
        )
        self.assertIn(b" # keep explanation\r\n", completed)
        self.assertIn(b"DEMO_SUPER_PASSWORD=${EXTERNAL_VALUE}\r\n", completed)
        self.assertIn(b"GOOGLE_API_KEY=synthetic-google-only\r\n", completed)
        names = setup.ASSIGNMENT.findall(completed.decode())
        self.assertEqual(len(names), len(set(names)))

    def test_main_completes_empty_credentials_without_printing_values(self):
        folder = Path(self.directory.name)
        (folder / "configs").mkdir()
        target = folder / "configs/.env"
        target.write_text(
            "GOOGLE_API_KEY=synthetic-google-only\n"
            + "".join(f"{name}=\n" for name in setup.VARIABLES)
        )
        output = StringIO()
        with patch.object(setup, "ROOT", folder), redirect_stdout(output):
            setup.main()
        self.assertNotIn("synthetic-google-only", output.getvalue())
        for line in target.read_text().splitlines():
            name, value = line.split("=", 1)
            if name in setup.VARIABLES:
                self.assertRegex(value, r"^[0-9a-f]{48}$")
                self.assertNotIn(value, output.getvalue())

    def test_symlink_rejected_without_touching_destination(self):
        destination = Path(self.directory.name) / "destination"
        destination.write_bytes(b"untouched")
        self.target.symlink_to(destination)
        with self.assertRaises(OSError):
            setup.prepare_local(self.target)
        self.assertEqual(destination.read_bytes(), b"untouched")

    def test_broken_symlink_rejected_without_creating_destination(self):
        destination = Path(self.directory.name) / "missing"
        self.target.symlink_to(destination)
        with self.assertRaises(OSError):
            setup.prepare_local(self.target)
        self.assertFalse(destination.exists())

    def test_directory_rejected(self):
        self.target.mkdir()
        with self.assertRaises(OSError):
            setup.prepare_local(self.target)

    def test_parallel_setup_has_one_copy_of_each_key(self):
        with ThreadPoolExecutor(max_workers=4) as workers:
            counts = list(
                workers.map(lambda _: setup.prepare_local(self.target), range(4))
            )
        self.assertEqual(sum(counts), len(setup.VARIABLES))
        names = setup.ASSIGNMENT.findall(self.target.read_text())
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
