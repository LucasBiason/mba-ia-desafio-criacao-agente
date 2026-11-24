from dataclasses import dataclass
from uuid import UUID
from microservice_toolkit import error
from aurora_toolkit.permissions import require_resident


@dataclass(frozen=True)
class SessionIdentity:
    """Identificadores do servidor; o apartamento é recuperado do banco a cada uso."""

    session_id: UUID
    resident_id: str

    @classmethod
    def from_authenticated_actor(cls, session_id, actor):
        require_resident(actor)
        if actor.get("active") is not True:
            raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
        return cls(UUID(str(session_id)), actor["id"])
