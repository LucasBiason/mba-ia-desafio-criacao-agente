from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ApartmentNumber = Annotated[str, Field(pattern=r"^[0-9]{1,10}[A-Za-z]?$")]
AreaId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
AccountId = Annotated[str, Field(min_length=1, max_length=64)]
AreaName = Annotated[str, Field(min_length=1, max_length=120)]
FeeCents = Annotated[int, Field(strict=True, ge=0, le=100_000_000)]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def reject_null_bytes(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("O campo contém um caractere inválido.")
        return value


class ApartmentInput(Input):
    number: ApartmentNumber
    resident_id: AccountId | None = None

    @field_validator("number")
    @classmethod
    def uppercase_number(cls, value):
        return value.upper()


class ApartmentPatch(ApartmentInput):
    number: ApartmentNumber | None = None

    @field_validator("number")
    @classmethod
    def uppercase_number(cls, value):
        if value is None:
            raise ValueError("Informe o número do apartamento.")
        return value.upper()


class AreaInput(Input):
    id: AreaId
    name: AreaName
    fee_cents: FeeCents


class AreaPatch(Input):
    name: AreaName | None = None
    fee_cents: FeeCents | None = None

    @field_validator("name", "fee_cents")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Informe o valor do campo.")
        return value


class RegulationInput(Input):
    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")
    base_version: int = Field(strict=True, ge=0, le=2_147_483_646)
    content: str = Field(min_length=1, max_length=200_000)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value):
        if not value.strip():
            raise ValueError("Informe o conteúdo do regulamento.")
        return value


class SessionInput(Input):
    apartment: ApartmentNumber

    @field_validator("apartment")
    @classmethod
    def uppercase_apartment(cls, value):
        return value.upper()


class MessageInput(Input):
    message: str = Field(min_length=1, max_length=2000)


Hour = Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]


class ReservationHours(Input):
    start_time: Hour | None
    end_time: Hour | None

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_time is None and self.end_time is None:
            return self
        if self.start_time is None or self.end_time is None or self.start_time >= self.end_time:
            raise ValueError("Informe início e fim em ordem crescente, ou limpe os dois horários.")
        return self


class VisitHours(Input):
    entry_time: Hour | None = None
    exit_time: Hour | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if not self.model_fields_set:
            raise ValueError("Informe os horários da visita ou envie valores nulos para limpá-los.")
        if ("entry_time" in self.model_fields_set and self.exit_time is not None
                and (self.entry_time is None or self.entry_time >= self.exit_time)):
            raise ValueError("A saída deve ser posterior à entrada.")
        return self
