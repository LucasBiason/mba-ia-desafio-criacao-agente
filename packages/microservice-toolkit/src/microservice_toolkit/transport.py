import os

import httpx

from .errors import error
from .observability import request_id_context


def required_secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) < 32 or not value.isascii():
        raise RuntimeError(f"Configuração obrigatória ausente ou inválida: {name}.")
    return value


class ServiceClient:
    def __init__(self, endpoints, *, secret_provider, token_header="X-Service-Token", timeout=3):
        self.endpoints = dict(endpoints)
        self.secret_provider = secret_provider
        self.token_header = token_header
        self.timeout = timeout

    def request(self, service, method, path, *, token=None, payload=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Caminho de serviço inválido.")
        headers = {self.token_header: self.secret_provider()}
        request_id = request_id_context.get()
        if request_id:
            headers["X-Request-ID"] = request_id
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with httpx.Client(timeout=self.timeout, trust_env=False) as client:
                return client.request(method, self.endpoints[service].rstrip("/") + path,
                                      headers=headers, json=payload)
        except httpx.RequestError:
            raise error(503, "SERVICE_UNAVAILABLE", "Serviço temporariamente indisponível.") from None
