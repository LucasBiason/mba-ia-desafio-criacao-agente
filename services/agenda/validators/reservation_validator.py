from microservice_toolkit import error

from aurora_toolkit.permissions import require_admin
from services.apartments.validators.unit_scope_validator import UnitScopeValidator


class ReservationValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_list(self, actor, apartment=None):
        if apartment is None:
            require_admin(actor)
        else:
            UnitScopeValidator(self.repository).validate(apartment, actor)

    def validate_hours(self, code, data, actor):
        require_admin(actor)
        if not (data.start_time is None and data.end_time is None):
            if (
                data.start_time is None
                or data.end_time is None
                or data.start_time >= data.end_time
            ):
                raise error(
                    422,
                    "INVALID_RESERVATION_HOURS",
                    "Informe início e fim em ordem crescente.",
                )
        record = self.repository.get(code)
        if record is None:
            raise error(404, "RESERVATION_NOT_FOUND", "Reserva não encontrada.")
        return record
