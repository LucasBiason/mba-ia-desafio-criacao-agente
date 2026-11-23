"""Setup regression tests use temporary files only, never the checkout .env."""

import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

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
