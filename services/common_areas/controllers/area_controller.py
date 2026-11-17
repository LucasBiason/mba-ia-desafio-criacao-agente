from microservice_toolkit import error
from sqlalchemy.exc import IntegrityError

from services.common_areas.models.area import Area
from services.common_areas.repositories.area_repository import AreaRepository
from services.common_areas.serializers.area_serializer import AreaSerializer
from services.common_areas.validators.area_validator import AreaValidator


class AreaController:
    def list(self, actor, administrative=False):
        with AreaRepository() as repository:
            AreaValidator(repository).validate_read(actor, administrative)
            return [AreaSerializer.serialize(area) for area in repository.list()]

    def get(self, area_id, actor):
        with AreaRepository() as repository:
            return AreaSerializer.serialize(AreaValidator(repository).existing(area_id, actor))

    def create(self, data, actor):
        try:
            with AreaRepository() as repository:
                AreaValidator(repository).validate_create(data, actor)
                return AreaSerializer.serialize(repository.create(Area(**data.model_dump())))
        except IntegrityError:
            raise error(409, "AREA_EXISTS", "Já existe uma área com esse identificador ou nome.") from None

    def update(self, area_id, data, actor):
        try:
            with AreaRepository() as repository:
                area = AreaValidator(repository).validate_update(area_id, data, actor)
                return AreaSerializer.serialize(repository.save(area, data.model_dump(exclude_unset=True)))
        except IntegrityError:
            raise error(409, "AREA_EXISTS", "Já existe uma área com esse nome.") from None

    def delete(self, area_id, actor):
        try:
            with AreaRepository() as repository:
                repository.delete(AreaValidator(repository).existing(area_id, actor))
        except IntegrityError:
            raise error(409, "AREA_IN_USE", "A área tem reservas no histórico e não pode ser excluída.") from None
