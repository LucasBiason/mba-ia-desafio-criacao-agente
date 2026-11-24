from sqlalchemy import select

from services.apartments.repositories.unit_scope_repository import UnitScopeRepository
from services.agenda.models.reservation import Reservation
from services.common_areas.models.area import Area


class ReservationRepository(UnitScopeRepository):
    def list(
        self, *, area_id=None, day=None, status=None, apartment=None, resident_id=None
    ):
        query = select(Reservation, Area.name).join(
            Area, Area.id == Reservation.area_id
        )
        for column, value in [
            (Reservation.area_id, area_id),
            (Reservation.date, day),
            (Reservation.status, status),
            (Reservation.apartment, apartment),
            (Reservation.resident_id, resident_id),
        ]:
            if value is not None:
                query = query.where(column == value)
        return self.session.execute(
            query.order_by(Reservation.date, Reservation.code)
        ).all()

    def get(self, code):
        return self.session.get(Reservation, code, with_for_update=True)

    def save_hours(self, reservation, start, end):
        reservation.start_time = start
        reservation.end_time = end
        self.session.flush()
        return reservation, self.session.get(Area, reservation.area_id).name
