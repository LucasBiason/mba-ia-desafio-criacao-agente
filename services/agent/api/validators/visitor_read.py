from .dated_record import DatedRecord


class VisitorRead(DatedRecord):
    """Direct visitor verification, without owner/internal database fields."""

    nome: str
