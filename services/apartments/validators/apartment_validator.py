from microservice_toolkit import error

from services.authentication.client import fetch_user
from services.permissions import require_admin, require_resident


class ApartmentValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_create(self, data, actor):
        require_admin(actor)
        self.responsible(data.resident_id)
        if self.repository.get(data.number) is not None:
            raise error(409, "APARTMENT_EXISTS", "Já existe um apartamento com esse número.")

    def responsible(self, resident_id):
        if resident_id is not None and fetch_user(resident_id)["role"] != "resident":
            raise error(422, "INVALID_RESIDENT", "Selecione uma conta de morador.")

    def existing(self, number, *, lock=False):
        row = self.repository.get(number, lock=lock)
        if row is None:
            raise error(404, "APARTMENT_NOT_FOUND", "Apartamento não encontrado.")
        return row

    def validate_update(self, number, data, actor):
        require_admin(actor)
        if "resident_id" in data.model_fields_set:
            self.responsible(data.resident_id)
        current = self.existing(number, lock=True)
        if data.number is not None and data.number != current[0].number:
            if self.repository.get(data.number) is not None:
                raise error(409, "APARTMENT_EXISTS", "Já existe um apartamento com esse número.")
        return current

    def validate_delete(self, number, actor):
        require_admin(actor)
        return self.existing(number, lock=True)[0]

    def validate_list(self, actor, own):
        require_resident(actor) if own else require_admin(actor)

    def validate_read(self, number, actor):
        require_admin(actor)
        return self.existing(number)
