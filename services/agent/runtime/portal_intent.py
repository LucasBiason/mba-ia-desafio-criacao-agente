"""Routing for explicit resident scope and agenda lookups, before the model."""

from datetime import date
import re
import unicodedata

REFUSAL = (
    "Por privacidade, não posso consultar reservas ou visitantes, nem fazer alterações "
    "em nome de outro apartamento. Só posso atender pedidos da sua unidade."
)
_UNITS = r"apartamentos?|aptos?|apts?|aps?|unidades?"
_ID = r"0*[0-9]{2,5}[a-z]?"
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
_AVAILABILITY = re.compile(
    r"\b(?:livres?|vag[oa]s?|disponive(?:l|is)|disponibilidade|ocupad[oa]s?|tem (?:uma )?vaga)\b"
)
_RULE = re.compile(r"\b(?:regulamento|artigo|regras?|politica)\b")
_AREAS = {
    "Salão de festas": r"\bsalao(?: de festas)?\b",
    "Churrasqueira": r"\bchurrasqueiras?\b",
    "Quadra": r"\bquadra(?: poliesportiva)?\b",
}
_DATES = re.compile(r"(?<![\w/])(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})(?![\w/])")
_TIME = re.compile(r"\b(?:\d{1,2}\s*(?:h(?:\d{2})?|:\d{2})|horarios?)\b")


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


def availability_reply(message, lookup):
    query = normalize(message)
    if not _AVAILABILITY.search(query) or _RULE.search(query):
        return None
    areas = [name for name, pattern in _AREAS.items() if re.search(pattern, query)]
    if len(areas) != 1:
        return (
            "Qual área você quer consultar: Salão de festas, Churrasqueira ou Quadra?"
        )
    area = areas[0]
    dates = list(dict.fromkeys(_DATES.findall(query)))
    if len(dates) != 1:
        return f"Para qual data você quer consultar {area}? Envie a área e a data, por exemplo: «{area} está livre em 25/11/2026?»."
    try:
        if "/" in dates[0]:
            day, month, year = map(int, dates[0].split("/"))
            target = date(year, month, day)
        else:
            target = date.fromisoformat(dates[0])
    except ValueError:
        return "A data informada não é válida. Use DD/MM/AAAA."
    status = lookup(area, target.isoformat()).get("status")
    label = target.strftime("%d/%m/%Y")
    if status not in ("available", "occupied"):
        return f"Não consegui confirmar a disponibilidade de {area} em {label}."
    state = "livre" if status == "available" else "com uma reserva ativa"
    detail = (
        " A agenda deste portal é por dia, não por horário."
        if _TIME.search(query)
        else ""
    )
    return f"Em {label}, a agenda mostra {area} {state}.{detail} Nenhuma reserva foi criada."


def portal_reply(message, apartment, actions):
    if foreign_unit_request(message, apartment):
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
    reply = availability_reply(message, actions.availability)
    if reply is not None:
        return {"message": reply, "confirmacoes_pendentes": actions.pending()}
    return None
