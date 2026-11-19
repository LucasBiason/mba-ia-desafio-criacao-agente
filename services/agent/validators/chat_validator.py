from microservice_toolkit import error

from services.apartments.validators.unit_scope_validator import UnitScopeValidator
from services.permissions import require_resident


class ChatValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_create(self, data, actor):
        UnitScopeValidator(self.repository).validate(data.apartment, actor, lock=True)

    def validate_list(self, actor):
        require_resident(actor)

    def validate_read(self, session_id, actor):
        require_resident(actor)
        record = self.repository.get(session_id, actor["id"])
        if record is None:
            raise error(404, "SESSION_NOT_FOUND", "Sessão não encontrada.")
        return record
