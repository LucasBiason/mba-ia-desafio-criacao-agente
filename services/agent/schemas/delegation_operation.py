"""Operações do protocolo privado; nenhuma operação representa aprovação."""

from enum import Enum


class DelegationOperation(str, Enum):
    READ_RESERVATIONS = "read_reservations"
    AVAILABILITY = "availability"
    RESERVE = "reserve"
    CANCEL = "cancel"
    READ_VISITORS = "read_visitors"
    PROPOSE_VISIT = "propose_visit"
    REGULATION = "regulation"
    CLARIFY = "clarify"
