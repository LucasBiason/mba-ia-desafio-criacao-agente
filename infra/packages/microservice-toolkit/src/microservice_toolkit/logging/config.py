"""Configuração dos logs JSON de acesso e de erro."""

import logging
import sys
from .formatters import ErrorJsonFormatter, JsonFormatter


def configure_logging():
    for name, formatter in [
        ("microservice_toolkit.http", JsonFormatter()),
        ("microservice_toolkit.errors", ErrorJsonFormatter()),
    ]:
        target = logging.getLogger(name)
        if not target.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            target.addHandler(handler)
            target.setLevel(logging.INFO)
            target.propagate = False
