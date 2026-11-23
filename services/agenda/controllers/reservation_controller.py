from datetime import time

from services.agenda.repositories.reservation_repository import ReservationRepository
from services.agenda.serializers.reservation_serializer import ReservationSerializer
from services.agenda.validators.reservation_validator import ReservationValidator


class ReservationController:
    def list(self, actor, *, area_id=None, day=None, status=None, apartment=None):
        with ReservationRepository() as repository:
            ReservationValidator(repository).validate_list(actor, apartment)
            rows = repository.list(
                area_id=area_id,
                day=day,
                status=status,
                apartment=apartment,
                resident_id=actor["id"] if apartment is not None else None,
            )
            return [
                ReservationSerializer.serialize(row, administrative=apartment is None)
                for row in rows
            ]

    def update_hours(self, code, data, actor):
        with ReservationRepository() as repository:
            record = ReservationValidator(repository).validate_hours(code, data, actor)
            row = repository.save_hours(
                record,
                time.fromisoformat(data.start_time) if data.start_time else None,
                time.fromisoformat(data.end_time) if data.end_time else None,
            )
            return ReservationSerializer.serialize(row, administrative=True)
