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


PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "residencial-aurora-base")
SERVICE = "agenda"
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


def inside_container(action):
    from services.agenda.repositories.agenda_seed_repository import AgendaSeedRepository

    with AgendaSeedRepository() as repository:
        result = repository.add(reserve_examples) if action == "add" else repository.remove()
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
        raise SystemExit("Suba o serviço Agenda da base local antes de usar a agenda.")

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
