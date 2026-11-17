#!/usr/bin/env python3
"""Adiciona ou remove reservas de demonstração na agenda local."""

import argparse
from calendar import monthrange
from datetime import date, time
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess


PROJECT = "residencial-aurora-base"
SERVICE = "condo"
PREFIX = "TEST-AGENDA-"
HOURS = (
    (time(8), time(10)),
    (time(9, 30), time(12)),
    (time(12), time(15)),
    (time(14), time(17, 30)),
    (time(17), time(19)),
    (time(18, 30), time(21, 45)),
)


def reserve_examples(anchor, areas, residents):
    center = anchor.year * 12 + anchor.month - 1
    for month_index in range(center - 2, center + 3):
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        for day in range(1, monthrange(year, month)[1] + 1):
            if (day + month_index) % 7 == 0:
                continue
            booking_date = date(year, month, day)
            for index, area in enumerate(areas):
                dense_day = (day + month_index) % 4 == 0
                selection = day + month_index + index * 2
                if not dense_day and selection % 5 >= 3:
                    continue
                resident = residents[(selection + index) % len(residents)]
                start, end = HOURS[selection % len(HOURS)]
                area_key = sha256(area["id"].encode()).hexdigest()[:16]
                code = f"{PREFIX}{booking_date:%Y%m%d}-{area_key}"
                yield (
                    code, resident["number"], resident["resident_id"], area["id"],
                    booking_date, area["fee_cents"], start, end,
                )


def add(connection):
    source = Path(os.environ.get("AURORA_DATA_DIR", "/app/dados")) / "areas.json"
    source_ids = [area["id"] for area in json.loads(source.read_text(encoding="utf-8"))]
    areas = connection.execute(
        "SELECT id, fee_cents FROM areas WHERE id = ANY(%s) ORDER BY id FOR SHARE",
        (source_ids,),
    ).fetchall()
    residents = connection.execute(
        """SELECT p.number, r.resident_id FROM apartments p
           JOIN apartment_residents r ON r.apartment_id = p.id ORDER BY p.number FOR SHARE OF p, r"""
    ).fetchall()
    if not areas or not residents:
        return "Nenhuma reserva criada. A agenda precisa de áreas iniciais e apartamentos vinculados."

    anchor = connection.execute(
        "SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date AS today"
    ).fetchone()["today"]
    connection.execute(
        """CREATE TABLE IF NOT EXISTS public.aurora_agenda_seed (
               reservation_code text PRIMARY KEY REFERENCES reservations(code) ON DELETE CASCADE
           )"""
    )
    inserted = skipped = 0
    for booking in reserve_examples(anchor, areas, residents):
        result = connection.execute(
            """WITH new_reservation AS (
                   INSERT INTO reservations
                       (code, apartment, resident_id, area_id, date, fee_cents, start_time, end_time, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
                   ON CONFLICT DO NOTHING
                   RETURNING code
               )
               INSERT INTO public.aurora_agenda_seed (reservation_code)
               SELECT code FROM new_reservation RETURNING reservation_code""",
            booking,
        ).fetchone()
        if result is None:
            skipped += 1
        else:
            inserted += 1
    return (
        f"{inserted} reservas de demonstração criadas em {len(areas)} áreas. "
        f"{skipped} combinações já ocupadas ou existentes foram preservadas."
    )


def remove(connection):
    ledger = connection.execute(
        "SELECT to_regclass('public.aurora_agenda_seed') AS ledger"
    ).fetchone()["ledger"]
    if ledger is None:
        return "Nenhuma reserva de demonstração registrada."
    removed = connection.execute(
        """DELETE FROM reservations
           WHERE code IN (SELECT reservation_code FROM public.aurora_agenda_seed)"""
    ).rowcount
    connection.execute("DROP TABLE public.aurora_agenda_seed")
    return f"{removed} reservas de demonstração removidas."


def inside_container(action):
    from psycopg import Error
    from psycopg.conninfo import conninfo_to_dict
    from services.domain.database import connect

    try:
        settings = conninfo_to_dict(os.environ["DATABASE_URL"])
        if settings.get("host") != "condo-db" or settings.get("dbname") != "aurora_condo":
            raise SystemExit("A agenda aceita somente o banco Condo da base local.")
        with connect() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('aurora.agenda.seed.v1'))")
            if connection.execute("SELECT 1 FROM domain_migrations WHERE version = 3").fetchone() is None:
                raise SystemExit("Atualize a base local com a migração de horários antes de gerar reservas.")
            result = {"add": add, "remove": remove}[action](connection)
    except (Error, OSError, ValueError, KeyError):
        raise SystemExit("Falha ao acessar a base ou as áreas de demonstração.") from None
    print(result)


def local_container(workspace):
    compose = [
        "docker", "compose", "--project-name", PROJECT, "--project-directory", str(workspace),
        "--file", str(workspace / "compose.yaml"),
    ]
    status = subprocess.run(
        [*compose, "ps", "--status", "running", "--quiet", SERVICE],
        capture_output=True, text=True, check=False,
    )
    ids = status.stdout.split()
    if status.returncode or len(ids) != 1:
        raise SystemExit("Suba o serviço Condo da base local antes de usar a agenda.")

    labels = (
        "com.docker.compose.project",
        "com.docker.compose.service",
        "com.docker.compose.project.working_dir",
    )
    template = "\n".join(f'{{{{index .Config.Labels "{label}"}}}}' for label in labels)
    identity = subprocess.run(
        ["docker", "inspect", "--format", template, ids[0]],
        capture_output=True, text=True, check=False,
    )
    if identity.returncode or identity.stdout.splitlines() != [PROJECT, SERVICE, str(workspace)]:
        raise SystemExit("O serviço em execução pertence a outro projeto ou diretório.")
    return ids[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("add", "remove"), help="Adicionar ou remover reservas de demonstração.")
    action = parser.parse_args().action
    if __file__ == "<stdin>":
        inside_container(action)
        return

    script = Path(__file__).resolve()
    try:
        container_id = local_container(script.parents[1])
        result = subprocess.run(
            ["docker", "exec", "-i", container_id, "python", "-", action],
            input=script.read_text(encoding="utf-8"), capture_output=True, text=True, check=False,
        )
    except OSError:
        raise SystemExit("Não foi possível executar a agenda no Compose local.") from None

    if result.returncode:
        raise SystemExit("Não foi possível atualizar a agenda. Confira a saúde do serviço e a migração 003.")
    print(result.stdout, end="")


if __name__ == "__main__":
    main()
