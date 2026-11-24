from microservice_toolkit import error

from aurora_toolkit.permissions import require_admin
from services.apartments.validators.unit_scope_validator import UnitScopeValidator
from services.visits.schemas.visit_hours import VisitHours


class VisitValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_list(self, actor, apartment, resident_view):
        if resident_view:
            UnitScopeValidator(self.repository).validate(apartment, actor)
        else:
            require_admin(actor)

    def validate_hours(self, visit_id, data, actor):
        require_admin(actor)
        if not data.model_fields_set:
            raise error(422, "INVALID_VISIT_HOURS", "Informe os horários da visita.")
        record = self.repository.get(visit_id)
        if record is None:
            raise error(404, "VISIT_NOT_FOUND", "Visita não encontrada.")
        values = {
            field: value.strftime("%H:%M") if value else None
            for field, value in (
                ("entry_time", record.entry_time),
                ("exit_time", record.exit_time),
            )
        }
        values.update(data.model_dump(exclude_unset=True))
        hours = VisitHours.model_validate(values)
        if hours.exit_time is not None and (
            hours.entry_time is None or hours.entry_time >= hours.exit_time
        ):
            raise error(
                422, "INVALID_VISIT_HOURS", "A saída deve ser posterior à entrada."
            )
        return record, hours
