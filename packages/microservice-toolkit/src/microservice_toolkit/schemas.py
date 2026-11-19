from pydantic import BaseModel, ConfigDict, field_validator


class RequestSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def reject_null_bytes(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("O campo contém um caractere inválido.")
        return value
