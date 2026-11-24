"""Preflight de privacidade e política; operações usam a delegação tipada."""

import re
import unicodedata

REFUSAL = (
    "Por privacidade, não posso consultar reservas ou visitantes, nem fazer alterações "
    "em nome de outro apartamento. Só posso atender pedidos da sua unidade."
)
_UNITS = r"apartamentos?|aptos?|apts?|aps?|unidades?"
_ID = r"[0-9]{1,10}[a-z]?"
_UNIT_IDS = re.compile(
    rf"\b(?:{_UNITS})\.?\s*(?:(?:n(?:o|umero)?\.?\s*|[º°#-])\s*)?({_ID})\b"
)
_IMPLICIT_IDS = re.compile(
    rf"\b(?:d[oae]|n[oae]|pelo|pela|para o|para a|em nome d[oae])\s+#?({_ID})\b(?![\w/:-])"
)
_OTHER_UNIT = re.compile(
    rf"\b(?:(?:outr[oa]s?|qualquer|todas? as|todos? os)\s+(?:{_UNITS})|outro morador|meu vizinho|minha vizinha|dos vizinhos)\b"
)
_PRIVATE = re.compile(
    r"\b(?:reserv\w*|cancel\w*|visit\w*|autoriza\w*|morador(?:es)?)\b"
)


def normalize(value):
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", str(value).casefold())
        if not unicodedata.combining(c)
    )


def _unit(value):
    return normalize(value).lstrip("0")


def foreign_unit_request(message, apartment):
    query = normalize(message)
    # Unqualified numbers count only in domain requests and after a scope
    # preposition. Years by themselves are not apartment identifiers.
    if not _PRIVATE.search(query):
        return False
    if _OTHER_UNIT.search(query):
        return True
    identifiers = set(_UNIT_IDS.findall(query))
    identifiers.update(
        value
        for value in _IMPLICIT_IDS.findall(query)
        if not re.fullmatch(r"(?:19|20|21)\d{2}", value)
    )
    return any(_unit(value) != _unit(apartment) for value in identifiers)


def portal_reply(message, apartment, actions):
    if scope_change_request(message) or foreign_unit_request(message, apartment):
        return {"message": REFUSAL, "confirmacoes_pendentes": actions.pending()}
    query = normalize(message)
    if re.search(
        r"\b(?:limites? (?:de |para (?:as )?)reservas?|quantas reservas|numero maximo de reservas)\b",
        query,
    ):
        return {
            "message": actions.reservation_limit(),
            "confirmacoes_pendentes": actions.pending(),
        }
    return None


def scope_change_request(message):
    """Reconhece troca do escopo da conversa, inclusive entre unidades próprias."""
    query = normalize(message)
    return bool(
        re.search(
            r"\b(?:mude|mudar|troque|trocar|altere|alterar|substitua|substituir|passar|passe)\b",
            query,
        )
        and re.search(
            r"\b(?:apartamento|apto|apt|unidade|identidade|permissoes?|sessao|conversa)\b",
            query,
        )
    )
