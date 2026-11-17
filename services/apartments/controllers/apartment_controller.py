from microservice_toolkit import error
from sqlalchemy.exc import IntegrityError

from services.apartments.models.apartment import Apartment
from services.apartments.repositories.apartment_repository import ApartmentRepository
from services.apartments.serializers.apartment_serializer import ApartmentSerializer
from services.apartments.validators.apartment_validator import ApartmentValidator


class ApartmentController:
    def list(self, actor, own=False):
        with ApartmentRepository() as repository:
            ApartmentValidator(repository).validate_list(actor, own)
            return [ApartmentSerializer.serialize(row) for row in repository.list(actor["id"] if own else None)]

    def get(self, number, actor):
        with ApartmentRepository() as repository:
            return ApartmentSerializer.serialize(ApartmentValidator(repository).validate_read(number, actor))

    def create(self, data, actor):
        try:
            with ApartmentRepository() as repository:
                ApartmentValidator(repository).validate_create(data, actor)
                return ApartmentSerializer.serialize(repository.create(Apartment(number=data.number), data.resident_id))
        except IntegrityError:
            raise error(409, "APARTMENT_EXISTS", "Já existe um apartamento com esse número.") from None

    def update(self, number, data, actor):
        try:
            with ApartmentRepository() as repository:
                apartment, _ = ApartmentValidator(repository).validate_update(number, data, actor)
                if data.number is not None:
                    apartment.number = data.number
                if "resident_id" in data.model_fields_set:
                    repository.assign(apartment.id, data.resident_id)
                return ApartmentSerializer.serialize(repository.save(apartment))
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise error(409, "APARTMENT_IN_USE", "O número é preservado porque o apartamento tem histórico.") from None
            raise error(409, "APARTMENT_EXISTS", "Já existe um apartamento com esse número.") from None

    def delete(self, number, actor):
        try:
            with ApartmentRepository() as repository:
                repository.delete(ApartmentValidator(repository).validate_delete(number, actor))
        except IntegrityError:
            raise error(409, "APARTMENT_IN_USE", "O apartamento tem histórico e não pode ser excluído.") from None
