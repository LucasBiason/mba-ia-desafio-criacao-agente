"""Cliente de identidade e acesso das APIs do Residencial Aurora."""

import os
from typing import Annotated

import httpx
from fastapi import Header, Request
from microservice_toolkit import ServiceClient, bearer_token, error, internal_guard, required_secret


def service_client():
    return ServiceClient({
        "auth": os.environ.get("AURORA_AUTH_URL", "http://auth:8000"),
        "users": os.environ.get("AURORA_USERS_URL", "http://users:8000"),
        "agent": os.environ.get("AURORA_AGENT_URL", "http://agent:8000"),
    }, secret_provider=lambda: required_secret("AURORA_INTERNAL_TOKEN"),
       token_header="X-Aurora-Internal-Token")


def internal_request(service, method, path, *, token=None, payload=None):
    return service_client().request(service, method, path, token=token, payload=payload)


verify_internal = internal_guard(
    lambda: required_secret("AURORA_INTERNAL_TOKEN"), header_name="X-Aurora-Internal-Token",
)


def identity_payload(response: httpx.Response) -> dict:
    try:
        data = response.json()
        if (not isinstance(data, dict)
                or not all(isinstance(data.get(key), str) for key in ("id", "name", "email", "role"))
                or data["role"] not in {"admin", "resident"}
                or not isinstance(data.get("active"), bool)):
            raise ValueError("invalid identity")
        return data
    except (ValueError, TypeError):
        raise error(503, "IDENTITY_UNAVAILABLE", "Identidade temporariamente indisponível.") from None


def verify_identity(token: str) -> dict:
    response = internal_request("auth", "GET", "/internal/identity", token=token)
    if response.status_code == 401:
        raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
    if response.status_code != 200:
        raise error(503, "AUTH_UNAVAILABLE", "Serviço de autenticação indisponível.")
    data = identity_payload(response)
    if not data["active"]:
        raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
    return data


def authenticated_user(request: Request, authorization: Annotated[str | None, Header()] = None) -> dict:
    user = getattr(request.state, "user", None)
    return user if user is not None else verify_identity(bearer_token(authorization))


def fetch_user(user_id: str) -> dict:
    if not user_id or any(not (char.isascii() and (char.isalnum() or char == "-")) for char in user_id):
        raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
    response = internal_request("users", "GET", f"/internal/users/{user_id}")
    if response.status_code == 404:
        raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
    if response.status_code != 200:
        raise error(503, "USERS_UNAVAILABLE", "Cadastro de usuários temporariamente indisponível.")
    return identity_payload(response)
