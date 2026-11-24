"""Coordenação das ações do morador com a fronteira ORM e recibos duráveis."""

from aurora_toolkit.identity import fetch_user
from aurora_toolkit.permissions import require_resident
from microservice_toolkit import error

from services.agent.repositories.product_action_repository import (
    ProductActionRepository,
)


def prepare_product_actions():
    """Compatibilidade com bootstrap explícito, fora do servidor HTTP."""
    from services.agent.bootstrap import initialize

    return initialize()


def _friendly(result):
    messages = {
        "reserved": "Reserva gravada. Código: {code}.",
        "occupied": "A área já está ocupada nessa data. Nenhuma reserva foi criada.",
        "cancelled": "Sua reserva foi cancelada.",
        "authorized": "A autorização do visitante foi gravada.",
        "not_found": "Nenhuma reserva ativa da sua unidade corresponde ao pedido.",
        "unknown_area": "Área não cadastrada.",
        "fee_changed": "A taxa mudou. Faça uma nova proposta antes de confirmar.",
        "policy_review_required": "Não foi possível consultar uma edição válida do regulamento vigente. Nenhuma alteração foi feita.",
        "policy_changed": "O regulamento mudou desde a proposta. Nenhuma alteração foi feita.",
        "invalid_details": "Informe uma área ou um visitante válido e uma data válida.",
        "pending": "O pedido está pendente. Use Aprovar ou Negar no cartão; um “sim” no chat não autoriza.",
        "rejected": "Pedido negado. Nenhuma alteração foi feita.",
    }
    value = result.get("status")
    return messages.get(
        value, "Não há confirmação de que a operação foi executada."
    ).format(code=result.get("code", ""))


class ProductActions:
    def __init__(self, identity, *, repository_factory=ProductActionRepository):
        self.identity = identity
        self.repository = repository_factory(identity)
        self.results = []

    def _actor(self):
        actor = fetch_user(self.identity.resident_id)
        require_resident(actor)
        if (
            actor.get("id") != self.identity.resident_id
            or actor.get("active") is not True
        ):
            raise error(401, "INVALID_SESSION", "Identidade inválida.")
        return actor

    def _store(self, value):
        self.results.append(value)
        return value

    def _ledger(self):
        return self.repository._ledger()

    def reservation_limit(self):
        self._actor()
        return self.repository.reservation_limit()

    def availability(self, area, data):
        self._actor()
        return self.repository.availability(area, data)

    def reserve(self, area, data, *, proposal_id=None):
        self._actor()
        return self._store(self.repository.reserve(area, data, proposal_id=proposal_id))

    def cancel(self, area, data):
        self._actor()
        return self._store(self.repository.cancel(area, data))

    def authorize_visit(self, nome, data, *, proposal_id=None):
        self._actor()
        return self._store(
            self.repository.authorize_visit(nome, data, proposal_id=proposal_id)
        )

    def list_my_visits(self):
        self._actor()
        return self.repository.list_my_visits()

    def pending(self):
        self._actor()
        return self.repository.pending()

    def _pending_projection(self, *, preserve_receipt):
        try:
            return {"confirmacoes_pendentes": self.pending()}
        except Exception as exc:
            # Never disclose a cached receipt after an explicit ownership or
            # identity revocation. Transient refresh errors must not erase commit.
            from fastapi import HTTPException

            if isinstance(exc, HTTPException) and exc.status_code in (401, 403, 404):
                raise
            if not preserve_receipt:
                raise
            return {"confirmacoes_pendentes": [], "pending_refresh_failed": True}

    def message_projection(self, text):
        if self.results:
            text = "\n".join(_friendly(item) for item in self.results)
        else:
            text = "Nenhuma alteração foi registrada neste turno.\n" + (text or "")
        return {
            "message": text,
            **self._pending_projection(preserve_receipt=bool(self.results)),
        }

    def decide(self, confirmation_id, confirmed):
        self._actor()
        outcome = self._ledger().decide(self.identity, str(confirmation_id), confirmed)
        result = outcome["result"] or {"status": "rejected"}
        # Ledger yields only after successful commit; never ask Gemini for the verdict.
        return {
            "message": _friendly(result),
            "resultado": result,
            **self._pending_projection(preserve_receipt=True),
        }
