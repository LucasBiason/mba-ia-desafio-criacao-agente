from services.agenda.schemas.reservation_read import ReservationRead
from services.agenda.schemas.reservation_admin_read import ReservationAdminRead


class ReservationSerializer:
    @staticmethod
    def serialize(row, administrative=False):
        record, area_name = row
        values = {
            key: getattr(record, key)
            for key in ("code", "apartment", "area_id", "date", "fee_cents", "status")
        }
        values.update(
            area_name=area_name,
            start_time=record.start_time.strftime("%H:%M")
            if record.start_time
            else None,
            end_time=record.end_time.strftime("%H:%M") if record.end_time else None,
        )
        if administrative:
            return ReservationAdminRead(**values, resident_id=record.resident_id)
        return ReservationRead(**values)
