"""Importa usuários, apartamentos e áreas pelas APIs administrativas existentes.

Uso: python3 infra/operations/importar_cadastros.py --url http://127.0.0.1:8770
A execução conserva cadastros existentes e não altera os JSONs de origem.
"""

import argparse
from getpass import getpass
import json
from pathlib import Path
from secrets import token_urlsafe
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener


def import_catalogs(url, email, password):
    source = Path(__file__).resolve().parents[2] / "dados"
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Informe uma origem HTTP válida, sem credenciais na URL.")
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("Use HTTPS fora do ambiente local.")
    opener = build_opener(ProxyHandler({}))
    token = None

    def call(path, method="GET", body=None):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode()
        request = Request(
            url.rstrip("/") + path, data=payload, headers=headers, method=method
        )
        try:
            with opener.open(request, timeout=15) as response:
                data = response.read()
                return json.loads(data) if data else None
        except HTTPError as exc:
            raise RuntimeError(
                f"{method} {path} recusado com HTTP {exc.code}."
            ) from None
        except URLError:
            raise RuntimeError("API administrativa indisponível.") from None

    token = call("/api/auth/login", "POST", {"email": email, "password": password})[
        "access_token"
    ]
    try:
        users = call("/api/admin/users")
        apartments = {row["number"]: row for row in call("/api/admin/apartments")}
        areas = {row["id"]: row for row in call("/api/admin/areas")}
        created = {"usuarios": 0, "apartamentos": 0, "areas": 0}
        for row in json.loads(
            (source / "apartamentos.json").read_text(encoding="utf-8")
        ):
            number = row["numero"]
            if number in apartments:
                continue
            matches = [
                user
                for user in users
                if user["role"] == "resident" and user["name"] == row["morador"]
            ]
            if len(matches) > 1:
                raise ValueError(
                    "Há nomes de morador duplicados. Confira os vínculos no painel antes de importar."
                )
            if matches:
                resident = matches[0]
            else:
                resident = call(
                    "/api/admin/users",
                    "POST",
                    {
                        "name": row["morador"],
                        "email": f"morador-{number.lower()}@aurora.test",
                        "password": token_urlsafe(32),
                        "role": "resident",
                    },
                )
                # An unknown random password does not become a usable initial login.
                call("/api/admin/users/" + resident["id"], "PATCH", {"active": False})
                users.append(resident)
                created["usuarios"] += 1
            apartment = call(
                "/api/admin/apartments",
                "POST",
                {"number": number, "resident_id": resident["id"]},
            )
            apartments[number] = apartment
            created["apartamentos"] += 1
        from decimal import Decimal

        rows = json.loads(
            (source / "areas.json").read_text(encoding="utf-8"), parse_float=Decimal
        )
        for row in rows:
            if row["id"] not in areas:
                area = call(
                    "/api/admin/areas",
                    "POST",
                    {
                        "id": row["id"],
                        "name": row["nome"],
                        "fee_cents": int(Decimal(row["taxa"]) * 100),
                    },
                )
                areas[row["id"]] = area
                created["areas"] += 1
        return created
    finally:
        call("/api/auth/logout", "POST")


def main():
    parser = argparse.ArgumentParser(
        description="Importar cadastros pelos endpoints administrativos."
    )
    parser.add_argument("--url", default="http://127.0.0.1:8770")
    parser.add_argument("--email", default="admin@aurora.test")
    args = parser.parse_args()
    try:
        result = import_catalogs(
            args.url, args.email, getpass("Senha administrativa: ")
        )
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
