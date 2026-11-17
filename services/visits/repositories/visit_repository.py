from sqlalchemy import select

from services.apartments.repositories.unit_scope_repository import UnitScopeRepository
from services.visits.models.visit import Visit


class VisitRepository(UnitScopeRepository):
    def list(self, *, apartment=None, day=None, resident_id=None):
        query = select(Visit)
        for column, value in [(Visit.apartment, apartment), (Visit.date, day), (Visit.resident_id, resident_id)]:
            if value is not None:
                query = query.where(column == value)
        return self.session.scalars(query.order_by(Visit.date, Visit.id)).all()

    def get(self, visit_id):
        return self.session.get(Visit, visit_id, with_for_update=True)

    def save_hours(self, record, entry_time, exit_time):
        record.entry_time = entry_time
        record.exit_time = exit_time
        self.session.flush()
        return record
