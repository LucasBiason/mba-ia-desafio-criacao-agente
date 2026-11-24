"""Vínculo imutável gerado pelo servidor para uma única invocação ADK."""

from dataclasses import dataclass

from services.agent.schemas.delegated_request import DelegatedRequest


@dataclass(frozen=True)
class DelegationEnvelope:
    turn_id: str
    invocation_id: str
    session_id: str
    resident_id: str
    specialist: str
    request: DelegatedRequest
