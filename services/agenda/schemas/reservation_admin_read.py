from .reservation_read import ReservationRead


class ReservationAdminRead(ReservationRead):
    resident_id: str | None
