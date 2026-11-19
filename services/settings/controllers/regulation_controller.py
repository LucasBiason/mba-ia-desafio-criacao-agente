from microservice_toolkit import error
from sqlalchemy.exc import IntegrityError

from services.settings.models.regulation import Regulation
from services.settings.repositories.regulation_repository import RegulationRepository
from services.settings.serializers.regulation_serializer import RegulationSerializer
from services.settings.validators.regulation_validator import RegulationValidator


class RegulationController:
    def current(self, actor, resident_view=False):
        with RegulationRepository() as repository:
            RegulationValidator(repository).validate_read(actor, resident_view)
            return RegulationSerializer.serialize(repository.current())

    def history(self, actor):
        with RegulationRepository() as repository:
            RegulationValidator(repository).validate_read(actor)
            return [RegulationSerializer.serialize(row) for row in repository.list()]

    def publish(self, data, actor):
        try:
            with RegulationRepository() as repository:
                current = RegulationValidator(repository).validate_publish(data, actor)
                record = Regulation(version=current.version + 1, content=data.content,
                                    author_id=actor["id"], author_name=actor["name"])
                return RegulationSerializer.serialize(repository.create(record))
        except IntegrityError:
            raise error(409, "REGULATION_CHANGED", "A versão vigente mudou. Recarregue o regulamento.") from None
