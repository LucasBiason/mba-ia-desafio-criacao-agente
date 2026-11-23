from typing import Annotated, Literal
from pydantic import Field, StringConstraints

ApartmentNumber = Annotated[str, Field(pattern=r"^[0-9]{1,10}[A-Za-z]?$")]
AreaId = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
]
AccountId = Annotated[str, Field(min_length=1, max_length=64)]
AreaName = Annotated[str, Field(min_length=1, max_length=120)]
FeeCents = Annotated[int, Field(strict=True, ge=0, le=100_000_000)]
Hour = Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]


Role = Literal["admin", "resident"]
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=254,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    ),
]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
Password = Annotated[str, StringConstraints(min_length=12, max_length=256)]
LoginPassword = Annotated[str, StringConstraints(min_length=1, max_length=256)]
