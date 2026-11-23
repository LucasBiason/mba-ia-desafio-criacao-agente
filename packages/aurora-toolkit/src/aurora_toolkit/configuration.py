"""Nomes e protocolo internos compartilhados pelo cluster, sem valores secretos."""

import os
from microservice_toolkit import required_secret

INTERNAL_TOKEN_HEADER = "X-Aurora-Internal-Token"


def internal_token():
    return required_secret(
        os.environ.get("INTERNAL_TOKEN_ENV", "AURORA_INTERNAL_TOKEN")
    )
