#!/usr/bin/env python3
"""Prepare local credentials without printing them."""

import os
from pathlib import Path
from secrets import token_hex


ROOT = Path(__file__).resolve().parents[1]
VARIABLES = (
    "AURORA_IDENTITY_PASSWORD", "AURORA_CONDO_PASSWORD", "AURORA_INTERNAL_TOKEN",
    "AURORA_JWT_KEY", "DEMO_SUPER_PASSWORD", "DEMO_ADMIN_PASSWORD", "DEMO_RESIDENT_PASSWORD",
)
target = ROOT / ".env"
try:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    if target.is_symlink() or not target.is_file():
        raise SystemExit("O caminho .env precisa ser um arquivo local.")
else:
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write("# Credenciais locais. Preserve este arquivo junto com os volumes.\n")
        for name in VARIABLES:
            file.write(f"{name}={token_hex(24)}\n")
    print("Configuração local criada em .env.")
