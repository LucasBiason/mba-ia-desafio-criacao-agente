"""Cliente de transporte para upstreams explicitamente cadastrados."""

import httpx
from ..exceptions import error
from ..logging.context import request_id_context


class ServiceClient:
    """Catálogo de upstreams confiáveis; os callers escolhem operação e payload."""

    def __init__(
        self, endpoints, *, secret_provider, token_header="X-Service-Token", timeout=3
    ):
        self.endpoints = dict(endpoints)
        self.secret_provider = secret_provider
        self.token_header = token_header
        self.timeout = timeout

    def request(self, service, method, path, *, token=None, payload=None):
        """Envia JSON sem registrar credenciais ou conteúdo da requisição."""
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
                return client.request(
                    method,
                    self.endpoints[service].rstrip("/") + path,
                    headers=headers,
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise error(
                503, "SERVICE_UNAVAILABLE", "Serviço temporariamente indisponível."
            ) from exc
