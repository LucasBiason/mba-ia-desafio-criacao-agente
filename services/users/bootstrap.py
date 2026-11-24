"""Criação explícita das contas e dos cadastros iniciais de moradores."""

import os
from secrets import token_hex

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from aurora_toolkit.data.bootstrap import initialize_tables
from aurora_toolkit.data.fixtures import initial_resident_id, read_json
from services.users.models.account import Account


def seed_accounts(session: Session) -> None:
    apartments = read_json("apartamentos.json")
    resident_name = next(row["morador"] for row in apartments if row["numero"] == "101")
    accounts = (
        (
            "demo-super",
            "Administração auxiliar",
            "super@aurora.test",
            "admin",
            "DEMO_SUPER_PASSWORD",
        ),
        (
            "demo-admin",
            "Administração",
            "admin@aurora.test",
            "admin",
            "DEMO_ADMIN_PASSWORD",
        ),
        (
            "demo-resident",
            resident_name,
            "morador@aurora.test",
            "resident",
            "DEMO_RESIDENT_PASSWORD",
        ),
    )
    passwords = {}
    for *_, variable in accounts:
        password = os.environ.get(variable, "")
        if not 12 <= len(password) <= 256:
            raise RuntimeError(
                f"Credencial local obrigatória ausente ou inválida: {variable}."
            )
        passwords[variable] = password

    hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
    for user_id, name, email, role, variable in accounts:
        session.add(
            Account(
                id=user_id,
                name=name,
                email=email,
                role=role,
                password_hash=hasher.hash(passwords[variable]),
                active=True,
            )
        )
    session.flush()
    for row in apartments:
        user_id = initial_resident_id(row["numero"])
        if user_id == "demo-resident":
            continue
        local = f"morador-{row['numero'].lower()}"
        email = f"{local}@aurora.test"
        suffix = 2
        while session.scalar(select(Account.id).where(Account.email == email)):
            email = f"{local}+{suffix}@aurora.test"
            suffix += 1
        session.add(
            Account(
                id=user_id,
                name=row["morador"],
                email=email,
                role="resident",
                active=False,
                password_hash=hasher.hash(token_hex(32)),
            )
        )


def initialize() -> bool:
    return initialize_tables([Account.__table__], seed_accounts, lock_key=74109142)
