from typing import Annotated, Literal
from pydantic import StringConstraints

Role = Literal["admin", "resident"]
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254,
                                          pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=256)]
LoginPassword = Annotated[str, StringConstraints(min_length=1, max_length=256)]
