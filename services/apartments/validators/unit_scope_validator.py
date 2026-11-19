from microservice_toolkit import error

from services.permissions import require_resident


class UnitScopeValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate(self, number, actor, *, lock=False):
        require_resident(actor)
        if not self.repository.owns_unit(number, actor["id"], lock=lock):
            raise error(403, "APARTMENT_FORBIDDEN", "O apartamento não está vinculado à sua conta.")
