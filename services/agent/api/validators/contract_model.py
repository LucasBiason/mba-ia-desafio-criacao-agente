from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Fixed contract fields, without implicit coercion or unknown keys."""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
