"""Primeira fatia de F09: identidade do servidor e uma tool somente de leitura.

A composição do runtime cria ReservationReadTool depois de autenticar o morador.
Somente list_my_reservations é exposta ao modelo. Seu contrato não possui
apartamento, residente ou session_id como argumentos controláveis pelo modelo.
Não há chamada ao LLM nem mudança de reservas neste módulo.
"""

from dataclasses import dataclass
from uuid import UUID

from microservice_toolkit import error
from aurora_toolkit.identity import fetch_user
from aurora_toolkit.permissions import require_resident
from services.agent.repositories.reservation_tool_repository import (
    ReservationToolRepository,
)
from services.agent.validators.chat_validator import ChatValidator
from services.agenda.serializers.reservation_serializer import ReservationSerializer


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


class ReservationReadTool:
    def __init__(
        self,
        identity,
        *,
        repository_factory=ReservationToolRepository,
        identity_loader=fetch_user,
    ):
        self.identity = identity
        self.repository_factory = repository_factory
        self.identity_loader = identity_loader

    def _current_actor(self):
        actor = self.identity_loader(self.identity.resident_id)
        if actor["id"] != self.identity.resident_id or actor.get("active") is not True:
            raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
        return actor

    def validate_access(self) -> None:
        """Gate do servidor antes de carregar histórico ou chamar o modelo.

        Não é uma tool exposta ao modelo. A consulta de reservas faz sua própria
        revalidação para não reutilizar uma autorização anterior.
        """
        actor = self._current_actor()
        with self.repository_factory() as repository:
            ChatValidator(repository).validate_read(self.identity.session_id, actor)

    def list_my_reservations(self) -> dict:
        """Lista reservas ativas da unidade fixa desta sessão, sem aceitar outra unidade."""
        actor = self._current_actor()
        with self.repository_factory() as repository:
            # Revalida papel, dono da sessão e vínculo atual da unidade. Uma sessão
            # não continua autorizada se o cadastro de responsáveis tiver mudado.
            ChatValidator(repository).validate_read(self.identity.session_id, actor)
            rows = repository.active_reservations(
                self.identity.session_id,
                self.identity.resident_id,
            )
            return {
                "reservations": [
                    ReservationSerializer.serialize(row).model_dump(mode="json")
                    for row in rows
                ]
            }
