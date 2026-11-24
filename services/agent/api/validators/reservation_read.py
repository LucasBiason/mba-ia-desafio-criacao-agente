from .dated_record import DatedRecord


class ReservationRead(DatedRecord):
    """Direct reservation verification, without owner/internal database fields."""

    codigo: str
    area: str
