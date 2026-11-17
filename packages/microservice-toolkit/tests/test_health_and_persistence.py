import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, Text, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase

from microservice_toolkit import Database, Repository, create_app, error


def test_health_and_openapi_belong_to_the_factory():
    app = create_app(title="Catálogo", service_name="catalogo", verifier=lambda token: {"id": "user"},
                     protected_paths=("/private",))

    @app.get("/private", tags=["Catálogo"], summary="Consultar catálogo", response_model=dict)
    def private():
        return {"ready": True}

    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ready"}
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/private"]["get"]["security"] == [{"BearerAuth": []}]
    assert schema["paths"]["/health"]["get"]["summary"] == "Verificar prontidão do serviço"


def test_health_uses_readiness_callback():
    def unavailable():
        raise error(503, "DEPENDENCY_UNAVAILABLE", "Dependência indisponível.")

    client = TestClient(create_app(title="Teste", service_name="test", health_check=unavailable))
    assert client.get("/health").status_code == 503


def test_repository_preserves_transaction_after_failed_write():
    class Base(DeclarativeBase):
        pass

    class Item(Base):
        __tablename__ = "items"
        id = Column(Integer, primary_key=True)
        value = Column(Text, unique=True)

    database = Database(lambda: "sqlite://")
    Base.metadata.create_all(database.engine)
    with Repository(database) as repository:
        repository.session.add(Item(id=1, value="original"))
    with pytest.raises(IntegrityError):
        with Repository(database) as repository:
            repository.session.add(Item(id=2, value="original"))
    with Repository(database) as repository:
        assert repository.session.scalars(select(Item.id)).all() == [1]
