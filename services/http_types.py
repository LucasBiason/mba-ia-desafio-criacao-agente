from typing import Annotated
from pydantic import Field

ApartmentNumber = Annotated[str, Field(pattern=r"^[0-9]{1,10}[A-Za-z]?$")]
AreaId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
AccountId = Annotated[str, Field(min_length=1, max_length=64)]
AreaName = Annotated[str, Field(min_length=1, max_length=120)]
FeeCents = Annotated[int, Field(strict=True, ge=0, le=100_000_000)]
Hour = Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]
