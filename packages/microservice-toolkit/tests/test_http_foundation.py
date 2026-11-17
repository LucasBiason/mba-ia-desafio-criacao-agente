import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from microservice_toolkit import bearer_token, create_app, error
from microservice_toolkit.observability import JsonFormatter, logger, request_id_context


def test_logs_allow_only_operational_fields_and_correlate_requests():
    app = create_app(title="Teste", service_name="test")
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    @app.get("/objects/{object_id}")
    def read(object_id: str):
        return {"id": object_id}

    try:
        response = TestClient(app).get("/objects/private-name?password=private-value",
                                      headers={"Authorization": "Bearer private-token", "X-Request-ID": "known-id"})
        assert response.headers["X-Request-ID"] == "known-id"
        entry = json.loads(output.getvalue())
        assert entry["request_id"] == "known-id"
        assert entry["route"] == "/objects/{object_id}"
        assert entry["status"] == 200
        assert "private-" not in output.getvalue()
        assert request_id_context.get() is None
    finally:
        logger.removeHandler(handler)


def test_error_and_validation_hide_payload_and_preserve_correlation():
    app = create_app(title="Teste", service_name="test")

    class Payload(BaseModel):
        count: int

    @app.post("/validate")
    def validate(payload: Payload):
        return payload

    @app.get("/explode")
    def explode():
        raise RuntimeError("private-database-url")

    client = TestClient(app)
    invalid = client.post("/validate", json={"count": "private-password"})
    assert invalid.status_code == 422
    assert "private-password" not in invalid.text
    unexpected = client.get("/explode", headers={"X-Request-ID": "failure-id"})
    assert unexpected.status_code == 500
    assert unexpected.json()["detail"]["code"] == "INTERNAL_ERROR"
    assert "private-database-url" not in unexpected.text
    assert unexpected.headers["X-Request-ID"] == "failure-id"


def test_authentication_verifies_once_and_fails_closed():
    verified = []

    def verifier(token):
        verified.append(token)
        if token == "invalid":
            raise error(401, "INVALID_SESSION", "Sessão inválida.")
        if token == "offline":
            raise RuntimeError("private-service-error")
        return {"id": "test-user"}

    app = create_app(title="Teste", service_name="test", verifier=verifier, protected_paths=("/private",))

    @app.get("/private")
    def private(request: Request):
        return request.state.user

    @app.get("/public")
    def public():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/public").status_code == 200
    assert client.get("/private").status_code == 401
    assert client.get("/private", headers={"Authorization": "Bearer allowed"}).json() == {"id": "test-user"}
    assert verified == ["allowed"]
    assert client.get("/private", headers={"Authorization": "Bearer invalid"}).headers["WWW-Authenticate"] == "Bearer"
    response = client.get("/private", headers={"Authorization": "Bearer offline"})
    assert response.status_code == 503
    assert "private-service-error" not in response.text


@pytest.mark.parametrize("header", [None, "", "Basic value", "Bearer ", "Bearer a b", "Bearer " + "x" * 4097])
def test_invalid_bearer_is_rejected(header):
    with pytest.raises(Exception) as exc:
        bearer_token(header)
    assert exc.value.status_code == 401


def test_request_context_is_independent_between_concurrent_calls():
    app = create_app(title="Teste", service_name="test")

    @app.get("/id")
    def identifier():
        return {"id": request_id_context.get()}

    def invoke(value):
        with TestClient(app) as client:
            response = client.get("/id", headers={"X-Request-ID": value})
            assert response.json()["id"] == value
            assert response.headers["X-Request-ID"] == value

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(invoke, ["first", "second", "third", "fourth"]))


def test_protected_application_requires_verifier():
    with pytest.raises(ValueError):
        create_app(title="Teste", service_name="test", protected_paths=("/private",))


def test_invalid_correlation_is_replaced_and_denials_are_correlated():
    app = create_app(title="Teste", service_name="test", verifier=lambda token: {"id": token},
                     protected_paths=("/private",))

    @app.get("/private")
    def private():
        return {"ok": True}

    response = TestClient(app).get("/private", headers={"X-Request-ID": "a" * 65})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert len(response.headers["X-Request-ID"]) == 32


def test_service_client_propagates_context_and_converts_connection_failure(monkeypatch):
    import httpx
    from microservice_toolkit import ServiceClient

    recorded = []

    class FakeClient:
        def __init__(self, **options):
            assert options == {"timeout": 3, "trust_env": False}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def request(self, method, url, **options):
            recorded.append(options)
            raise httpx.ConnectError("private-host")

    monkeypatch.setattr(httpx, "Client", FakeClient)
    client = ServiceClient({"identity": "http://identity"}, secret_provider=lambda: "synthetic-test-value")
    token = request_id_context.set("trace-test")
    try:
        with pytest.raises(Exception) as failure:
            client.request("identity", "GET", "/me", token="user-token")
    finally:
        request_id_context.reset(token)
    assert failure.value.status_code == 503
    assert "private-host" not in str(failure.value.detail)
    assert recorded[0]["headers"]["X-Request-ID"] == "trace-test"
    assert recorded[0]["headers"]["Authorization"] == "Bearer user-token"


def test_authentication_applies_with_a_gateway_root_path():
    app = create_app(title="Teste", service_name="test", verifier=lambda token: {"id": "verified"},
                     protected_paths=("/private",))

    @app.get("/private")
    def private(request: Request):
        return request.state.user

    client = TestClient(app, root_path="/services/test")
    assert client.get("/services/test/private").status_code == 401
    response = client.get("/services/test/private", headers={"Authorization": "Bearer allowed"})
    assert response.json() == {"id": "verified"}
