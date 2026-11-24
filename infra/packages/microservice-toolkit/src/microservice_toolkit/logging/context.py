"""Contexto de correlação e logger de acesso compartilhados."""

import logging
from contextvars import ContextVar

request_id_context = ContextVar("request_id", default=None)
logger = logging.getLogger("microservice_toolkit.http")
