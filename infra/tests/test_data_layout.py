"""Official fixture tree stays byte-identical and contains no application scripts."""

import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
# Git blob IDs verified against the configured upstream origin/main.
OFFICIAL = {
    "apartamentos.json": "5c17ae3e2275b6c519936ed096809668c13b8633",
    "areas.json": "242e1a550026bb9753d3d222e2dd793fa5e63ecf",
    "regulamento.md": "46c5d1375d081875a15f2fa0a31ac96cc7533dd2",
    "reservas.json": "e4d3f93680f54db28fb6e0ffa0c2b3fd980135c6",
    "visitantes.json": "5d5a2cbc1010a89d7546b35c405b85a2d0089902",
}


class OfficialDataLayoutTest(unittest.TestCase):
    def test_exact_upstream_tree_and_bytes(self):
        directory = ROOT / "dados"
        self.assertEqual({item.name for item in directory.iterdir()}, set(OFFICIAL))
        for name, expected in OFFICIAL.items():
            with self.subTest(name=name):
                data = (directory / name).read_bytes()
                blob = b"blob " + str(len(data)).encode() + b"\0" + data
                self.assertEqual(hashlib.sha1(blob).hexdigest(), expected)

    def test_relocated_cli_help_does_not_require_database(self):
        for arguments in (
            ["infra/operations/importar_cadastros.py", "--help"],
            ["infra/operations/seed_agenda.py", "--help"],
            ["-m", "services.initialize", "--help"],
        ):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, "-B", *arguments],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
