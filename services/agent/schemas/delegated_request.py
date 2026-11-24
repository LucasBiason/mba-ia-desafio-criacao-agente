"""Schema explícito de interpretação, sem autoridade ou identidade do modelo."""

from datetime import date as CalendarDate

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    ValidationInfo,
    field_validator,
)

from services.agent.schemas.delegation_operation import DelegationOperation


class DelegatedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: DelegationOperation
    area: StrictStr | None = Field(default=None, max_length=2000)
    date: StrictStr | None = Field(default=None, max_length=2000)
    name: StrictStr | None = Field(default=None, max_length=2000)
    question: StrictStr | None = Field(default=None, max_length=2000)

    @field_validator("area", "date", "name", "question", mode="after")
    @classmethod
    def project_business_field(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        """Valida tipos antes de projetar; chaves desconhecidas continuam proibidas."""
        operation = info.data.get("operation")
        if operation is None:
            return value  # A validação do enum já falhou; não substituir o erro.
        allowed = {
            "read_reservations": (),
            "read_visitors": (),
            "availability": ("area", "date"),
            "reserve": ("area", "date"),
            "cancel": ("area", "date"),
            "propose_visit": ("name", "date"),
            "regulation": ("question",),
            "clarify": ("question",),
        }[operation.value]
        return value if info.field_name in allowed else None

    def missing_fields(self) -> tuple[str, ...]:
        required = {
            "availability": ("area", "date"),
            "reserve": ("area", "date"),
            "cancel": ("area", "date"),
            "propose_visit": ("name", "date"),
            "regulation": ("question",),
            "clarify": ("question",),
        }.get(self.operation.value, ())
        limits = {"area": 100, "date": 10, "name": 160, "question": 500}
        missing = []
        for field in required:
            value = getattr(self, field)
            if (
                value is None
                or not value.strip()
                or not value.isprintable()
                or len(value) > limits[field]
            ):
                missing.append(field)
        if self.date is not None:
            try:
                if CalendarDate.fromisoformat(self.date).isoformat() != self.date:
                    raise ValueError
            except ValueError:
                missing.append("date")
        return tuple(dict.fromkeys(missing))
