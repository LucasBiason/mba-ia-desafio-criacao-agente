from services.visits.schemas.visit_read import VisitRead


class VisitSerializer:
    @staticmethod
    def serialize(record):
        return VisitRead(id=record.id, apartment=record.apartment, name=record.name, date=record.date,
                         entry_time=record.entry_time.strftime("%H:%M") if record.entry_time else None,
                         exit_time=record.exit_time.strftime("%H:%M") if record.exit_time else None)
