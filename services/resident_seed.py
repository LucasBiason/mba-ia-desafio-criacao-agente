"""Source identifiers shared by the identity and condominium services."""

import json
import os
from pathlib import Path


def read_seed_apartments():
    default_source = Path(__file__).resolve().parents[1] / "dados"
    source = Path(os.environ.get("AURORA_DATA_DIR", default_source))
    return json.loads((source / "apartamentos.json").read_text(encoding="utf-8"))


def seed_resident_id(number):
    if number == "101":
        return "demo-resident"
    return f"resident-{number.lower()}"
