"""Inicializa explicitamente um banco, sem iniciar servidores HTTP.

Uso: python -m services.initialize identity|condominium
"""

import argparse


def initialize_identity() -> None:
    from services.users.bootstrap import initialize as initialize_users
    from services.authentication.bootstrap import (
        initialize as initialize_authentication,
    )

    initialize_users()
    initialize_authentication()


def initialize_condominium() -> None:
    from services.common_areas.bootstrap import initialize as initialize_common_areas
    from services.apartments.bootstrap import initialize as initialize_apartments
    from services.agenda.bootstrap import initialize as initialize_agenda
    from services.visits.bootstrap import initialize as initialize_visits
    from services.parameters.bootstrap import initialize as initialize_parameters
    from services.agent.bootstrap import initialize as initialize_agent

    initialize_common_areas()
    initialize_apartments()
    initialize_agenda()
    initialize_visits()
    initialize_parameters()
    initialize_agent()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", choices=("identity", "condominium"))
    args = parser.parse_args()
    initialize = (
        initialize_identity if args.database == "identity" else initialize_condominium
    )
    initialize()
    print(f"Inicialização concluída: {args.database}.")


if __name__ == "__main__":
    main()
