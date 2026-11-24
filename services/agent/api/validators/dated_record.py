from datetime import date
from typing import Annotated

from pydantic import Field, field_validator

from .contract_model import ContractModel

IsoDay = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]


class DatedRecord(ContractModel):
    """Public verification records expose dates as ISO strings, not datetimes."""

    data: IsoDay

    @field_validator("data")
    @classmethod
    def valid_calendar_day(cls, value: str) -> str:
        """Reject impossible calendar dates without altering the wire value."""
        date.fromisoformat(value)
        return value
