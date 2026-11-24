#!/usr/bin/env python3
"""Prepare missing or explicitly empty local credentials without printing secrets."""

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
    "AURORA_AGENT_DB_PASSWORD",
    "AURORA_INTERNAL_TOKEN",
    "AURORA_JWT_KEY",
    "DEMO_SUPER_PASSWORD",
    "DEMO_ADMIN_PASSWORD",
    "DEMO_RESIDENT_PASSWORD",
)
ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)

LINE_ASSIGNMENT = re.compile(
    r"^(?P<prefix>[ \t]*(?:export[ \t]+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*)"
    r"(?P<value>[^\r\n]*)",
    re.MULTILINE,
)
EMPTY_VALUE = re.compile(r"(?:''|\"\")?(?P<tail>[ \t]*(?:#.*)?)")


def prepare_local(target: Path, *, complete_empty: bool = False) -> int:
    """Append absent keys, optionally filling empty credentials from the example.

    Existing assignments remain byte-identical unless complete_empty is enabled
    and the name is in VARIABLES with an empty or quoted-empty value. Reject
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
        content = original.decode("utf-8")
        completed = {}
        if complete_empty:

            def fill_empty(match):
                name = match["name"]
                empty = EMPTY_VALUE.fullmatch(match["value"])
                if name not in VARIABLES or empty is None:
                    return match[0]
                if name not in completed:
                    completed[name] = token_hex(24)
                tail = empty["tail"]
                if tail.startswith("#"):
                    tail = " " + tail
                return match["prefix"] + completed[name] + tail

            content = LINE_ASSIGNMENT.sub(fill_empty, content)
        names = set(ASSIGNMENT.findall(content))
        missing = [name for name in VARIABLES if name not in names]
        if not missing and not completed:
            return 0
        updated = content.encode("utf-8")
        prefix = b"" if not updated or updated.endswith(b"\n") else b"\n"
        if not original:
            prefix += (
                b"# Credenciais locais. Preserve este arquivo junto com os volumes.\n"
            )
        additions = "".join(f"{name}={token_hex(24)}\n" for name in missing).encode()
        if completed:
            file.seek(0)
            file.write(updated + (prefix + additions if missing else b""))
            file.truncate()
        else:
            file.seek(0, os.SEEK_END)
            file.write(prefix + additions)
        file.flush()
        os.fsync(file.fileno())
        return len(missing) + len(completed)


def main() -> None:
    """Prepare the local portal configuration without displaying credentials."""
    try:
        added = prepare_local(ROOT / "configs/.env", complete_empty=True)
    except (OSError, ValueError):
        raise SystemExit(
            "Não foi possível preparar .env; use um arquivo local regular UTF-8."
        ) from None
    if added:
        print(
            "Configuração local completada em configs/.env; valores não vazios preservados."
        )


if __name__ == "__main__":
    main()
