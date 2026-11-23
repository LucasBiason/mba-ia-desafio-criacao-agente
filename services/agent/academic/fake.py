"""Deterministic model for isolated Compose acceptance; never used implicitly."""

import json

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class AcademicFakeModel(BaseLlm):
    model: str = "aurora-compose-fake"
    role: str

    async def generate_content_async(self, request, stream=False):
        texts = [
            part.text
            for content in request.contents
            if content.role == "user"
            for part in content.parts or []
            if part.text and "<<<BEGIN_QUOTED_AGENT_CONTENT>>>" not in part.text
        ]
        try:
            command = json.loads(texts[-1])
            if not isinstance(command, dict):
                command = {}
        except (IndexError, ValueError):
            command = {}
        responses = [
            part.function_response
            for part in request.contents[-1].parts or []
            if part.function_response
        ]
        operation = command.get("tool", "reservar_area")
        target = "convivencia" if operation == "consultar_regulamento" else "reservas"
        if self.role == "principal":
            part = types.Part(
                function_call=types.FunctionCall(
                    name="transfer_to_agent", args={"agent_name": target}
                )
            )
        elif self.role != target and not responses:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="transfer_to_agent", args={"agent_name": "principal"}
                )
            )
        elif responses:
            result = responses[-1].response
            if command.get("fail_after_commit") and result.get("status") == "reserved":
                raise RuntimeError("Controlled provider failure after commit.")
            part = types.Part(text=json.dumps(result, ensure_ascii=False))
        elif (
            operation in ("reservar_area", "cancelar_reserva")
            and isinstance(command.get("area"), str)
            and isinstance(command.get("data"), str)
        ):
            fields = (
                ("area", "data", "hora_inicio", "hora_fim")
                if operation == "reservar_area"
                else ("area", "data")
            )
            part = types.Part(
                function_call=types.FunctionCall(
                    name=operation, args={k: command[k] for k in fields if k in command}
                )
            )
        elif operation == "consultar_regulamento" and isinstance(
            command.get("pergunta"), str
        ):
            part = types.Part(
                function_call=types.FunctionCall(
                    name=operation, args={"pergunta": command["pergunta"]}
                )
            )
        else:
            part = types.Part(
                text="Modelo de teste: envie um JSON com área e data; não é Gemini."
            )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))
