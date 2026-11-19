from pydantic import ConfigDict, Field
from microservice_toolkit.schemas import RequestSchema


class RegulationInput(RequestSchema):
    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")
    base_version: int = Field(strict=True, ge=0, le=2_147_483_646)
    content: str = Field(min_length=1, max_length=200_000)
