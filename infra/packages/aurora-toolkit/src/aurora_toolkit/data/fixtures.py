"""Leitura das fontes de dados originais do Residencial Aurora."""

from decimal import Decimal
import json
import os
from pathlib import Path


def read_text(name: str) -> str:
    source = Path(os.environ.get("AURORA_DATA_DIR", Path.cwd() / "dados"))
    return (source / name).read_text(encoding="utf-8")


def read_json(name: str):
    return json.loads(read_text(name), parse_float=Decimal)


def initial_resident_id(number: str) -> str:
    return "demo-resident" if number == "101" else f"resident-{number.lower()}"
