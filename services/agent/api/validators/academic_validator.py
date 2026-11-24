import json

from fastapi import HTTPException


def validate_message(value):
    if not value.strip():
        raise HTTPException(422, "Mensagem vazia.")


def decode_evidence(value):
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        raise HTTPException(
            409, "Evidência inválida; reconciliação bloqueada."
        ) from None
    if not isinstance(parsed, dict):
        raise HTTPException(409, "Evidência inválida; reconciliação bloqueada.")
    return parsed
