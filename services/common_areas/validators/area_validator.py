from microservice_toolkit import error

from services.permissions import require_admin


class AreaValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_read(self, actor, administrative=False):
        if administrative:
            require_admin(actor)

    def validate_create(self, data, actor):
        require_admin(actor)

        if self.repository.get(data.id) is not None or self.repository.named_area(data.name) is not None:
            raise error(409, "AREA_EXISTS", "Já existe uma área com esse identificador ou nome.")

    def validate_update(self, area_id, data, actor):
        area = self.existing(area_id, actor)
        if data.name is not None:
            owner = self.repository.named_area(data.name)
            if owner is not None and owner != area_id:
                raise error(409, "AREA_EXISTS", "Já existe uma área com esse nome.")
        return area

    def existing(self, area_id, actor):
        require_admin(actor)
        area = self.repository.get(area_id, lock=True)
        if area is None:
            raise error(404, "AREA_NOT_FOUND", "Área não encontrada.")
        return area
