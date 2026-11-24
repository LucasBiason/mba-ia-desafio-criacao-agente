import re
import unicodedata
from datetime import date


def iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Data deve usar AAAA-MM-DD.")
    return date.fromisoformat(value).isoformat()


def visible_name(value):
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= 160
        or any(not c.isprintable() for c in value)
    ):
        raise ValueError("Nome deve conter de 1 a 160 caracteres visíveis.")
    return " ".join(value.split())


def slug(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        return ""
    plain = unicodedata.normalize("NFKD", value)
    return re.sub(
        r"[^a-z0-9]+", "-", plain.encode("ascii", "ignore").decode().lower()
    ).strip("-")
