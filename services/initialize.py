"""Inicializa explicitamente um banco, sem iniciar servidores HTTP.

Uso: python -m services.initialize identity|condominium|agent-sessions
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


def initialize_agent_sessions() -> None:
    """Prepara o armazenamento ADK dedicado antes de iniciar o servidor."""
    import os
    from services.agent.bootstrap import initialize_sessions

    database_url = os.environ.get("AURORA_AGENT_SESSION_DATABASE_URL", "")
    if not database_url:
        raise SystemExit(
            "Configure AURORA_AGENT_SESSION_DATABASE_URL para preparar as sessões."
        )
    initialize_sessions(database_url)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "database", choices=("identity", "condominium", "agent-sessions")
    )
    args = parser.parse_args()
    initialize = {
        "identity": initialize_identity,
        "condominium": initialize_condominium,
        "agent-sessions": initialize_agent_sessions,
    }[args.database]
    initialize()
    print(f"Inicialização concluída: {args.database}.")


if __name__ == "__main__":
    main()
