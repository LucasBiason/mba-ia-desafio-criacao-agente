#!/usr/bin/env python3
"""Append missing local credentials without replacing values or printing secrets."""

import fcntl
import os
from pathlib import Path
import re
from secrets import token_hex
import stat

ROOT = Path(__file__).resolve().parents[1]
VARIABLES = (
    "AURORA_IDENTITY_PASSWORD",
    "AURORA_CONDO_PASSWORD",
    "AURORA_INTERNAL_TOKEN",
    "AURORA_JWT_KEY",
    "DEMO_SUPER_PASSWORD",
    "DEMO_ADMIN_PASSWORD",
    "DEMO_RESIDENT_PASSWORD",
)
ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)


def prepare_local(target: Path) -> int:
    """Preserve file bytes and existing assignments, appending only absent keys.

    An existing empty assignment is intentional and is never replaced. Reject
    symlinks, nonregular files and hardlinks. The advisory lock serializes this
    helper's callers; editors that ignore locks must not modify the file during
    setup. Existing file permissions are preserved; new files are private.
    """
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, "r+b") as file:
        metadata = os.fstat(file.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError(
                "O caminho .env precisa ser um arquivo local regular exclusivo."
            )
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        current = os.stat(target, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise ValueError(
                "O arquivo .env mudou durante a preparação; tente novamente."
            )
        original = file.read()
        names = set(ASSIGNMENT.findall(original.decode("utf-8")))
        missing = [name for name in VARIABLES if name not in names]
        if not missing:
            return 0
        prefix = b"" if not original or original.endswith(b"\n") else b"\n"
        if not original:
            prefix += (
                b"# Credenciais locais. Preserve este arquivo junto com os volumes.\n"
            )
        additions = "".join(f"{name}={token_hex(24)}\n" for name in missing).encode()
        file.seek(0, os.SEEK_END)
        file.write(prefix + additions)
        file.flush()
        os.fsync(file.fileno())
        return len(missing)


def main() -> None:
    """Prepare the local portal configuration without displaying credentials."""
    try:
        added = prepare_local(ROOT / ".env")
    except (OSError, ValueError):
        raise SystemExit(
            "Não foi possível preparar .env; use um arquivo local regular UTF-8."
        ) from None
    if added:
        print("Configuração local completada em .env; valores existentes preservados.")


if __name__ == "__main__":
    main()
