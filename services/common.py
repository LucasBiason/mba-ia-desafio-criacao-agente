"""Security boundary used by the internal product services."""

import hmac
import os
from typing import Annotated

import httpx
from fastapi import Header, HTTPException


def error(status: int, code: str, message: str) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return HTTPException(status, detail={"code": code, "message": message}, headers=headers)


def required_secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) < 32 or not value.isascii():
        raise RuntimeError(f"Configuração obrigatória ausente ou inválida: {name}.")
    return value


def verify_internal(
    credential: Annotated[str | None, Header(alias="X-Aurora-Internal-Token")] = None,
) -> None:
    expected = required_secret("AURORA_INTERNAL_TOKEN")
    if credential is None or not hmac.compare_digest(credential.encode(), expected.encode()):
        raise error(403, "INTERNAL_ACCESS_REQUIRED", "Operação reservada para serviços internos.")


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 4096 or any(ch.isspace() for ch in token):
        raise error(401, "AUTH_REQUIRED", "Entre com sua conta para continuar.")
    return token


def internal_request(
    service: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict | None = None,
) -> httpx.Response:
    endpoints = {
        "auth": os.environ.get("AURORA_AUTH_URL", "http://auth:8000"),
        "users": os.environ.get("AURORA_USERS_URL", "http://users:8000"),
        "agent": os.environ.get("AURORA_AGENT_URL", "http://agent:8000"),
    }
    headers = {"X-Aurora-Internal-Token": required_secret("AURORA_INTERNAL_TOKEN")}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=3, trust_env=False) as client:
            return client.request(method, endpoints[service] + path, headers=headers, json=payload)
    except httpx.RequestError:
        raise error(503, "SERVICE_UNAVAILABLE", "Serviço temporariamente indisponível.") from None


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


def authenticated_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    token = bearer_token(authorization)
    response = internal_request("auth", "GET", "/internal/identity", token=token)
    if response.status_code == 401:
        raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
    if response.status_code != 200:
        raise error(503, "AUTH_UNAVAILABLE", "Serviço de autenticação indisponível.")
    data = identity_payload(response)
    if not data["active"]:
        raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
    return data


def fetch_user(user_id: str) -> dict:
    if not user_id or any(not (char.isascii() and (char.isalnum() or char == "-")) for char in user_id):
        raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
    response = internal_request("users", "GET", f"/internal/users/{user_id}")
    if response.status_code == 404:
        raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
    if response.status_code != 200:
        raise error(503, "USERS_UNAVAILABLE", "Cadastro de usuários temporariamente indisponível.")
    return identity_payload(response)
