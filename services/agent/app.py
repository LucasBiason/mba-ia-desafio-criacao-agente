"""Transport boundary for the guided agent implementation."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, StringConstraints

from services.common import error, required_secret, verify_internal


@asynccontextmanager
async def lifespan(_app: FastAPI):
    required_secret("AURORA_INTERNAL_TOKEN")
    yield


app = FastAPI(title="Aurora · Serviço de agentes", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    session_id: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    apartment: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    user_id: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


@app.get("/health")
def health():
    return {"status": "ready", "agent_configured": False, "mode": "learning"}


@app.post("/internal/chat/messages", dependencies=[Depends(verify_internal)])
def message(_request: Message):
    raise error(503, "AGENT_NOT_CONFIGURED", "O serviço está pronto para a etapa guiada de agentes.")
