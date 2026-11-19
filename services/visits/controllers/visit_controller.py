from datetime import time

from services.visits.repositories.visit_repository import VisitRepository
from services.visits.serializers.visit_serializer import VisitSerializer
from services.visits.validators.visit_validator import VisitValidator


class VisitController:
    def list(self, actor, *, apartment=None, day=None, resident_view=False):
        apartment = apartment.upper() if apartment else None
        with VisitRepository() as repository:
            VisitValidator(repository).validate_list(actor, apartment, resident_view)
            rows = repository.list(apartment=apartment, day=day,
                                   resident_id=actor["id"] if resident_view else None)
            return [VisitSerializer.serialize(row) for row in rows]

    def update_hours(self, visit_id, data, actor):
        with VisitRepository() as repository:
            record, hours = VisitValidator(repository).validate_hours(visit_id, data, actor)
            record = repository.save_hours(record, time.fromisoformat(hours.entry_time) if hours.entry_time else None,
                                           time.fromisoformat(hours.exit_time) if hours.exit_time else None)
            return VisitSerializer.serialize(record)
