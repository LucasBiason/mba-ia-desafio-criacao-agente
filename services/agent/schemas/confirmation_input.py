from uuid import UUID
from pydantic import Field, StrictBool
from microservice_toolkit.schemas import RequestSchema


class ConfirmationInput(RequestSchema):
    id: UUID = Field(
        description="Identificador da proposta persistida na sessão de origem."
    )
    confirmado: StrictBool = Field(
        description="Aprovar (true) ou negar (false); texto no chat não autoriza."
    )
