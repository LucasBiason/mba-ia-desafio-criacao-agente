"""Seleção determinística conservadora: um capítulo, um artigo, nunca o inteiro."""

import re
import unicodedata


def words(text):
    normalized = unicodedata.normalize("NFKD", text.lower())
    return set(
        re.findall(
            r"[a-z0-9]+", "".join(c for c in normalized if not unicodedata.combining(c))
        )
    )


ALIASES = {
    "barulho": "silencio",
    "silencioso": "silencio",
    "pet": "animais",
    "cachorro": "animais",
    "gato": "animais",
    "lixo": "lixo",
    "obra": "obras",
    "reforma": "reformas",
    "visitante": "portaria",
    "visitantes": "portaria",
    "carro": "garagem",
    "domingo": "domingos",
}
STOP = {
    "a",
    "o",
    "as",
    "os",
    "de",
    "do",
    "da",
    "dos",
    "das",
    "e",
    "em",
    "na",
    "no",
    "para",
    "por",
    "qual",
    "quais",
    "que",
    "como",
    "posso",
    "pode",
    "me",
    "um",
    "uma",
    "ao",
    "aos",
    "se",
    "com",
    "regra",
    "regras",
    "regulamento",
    "capitulo",
}


def select_excerpt(content: str, question: str) -> dict[str, str]:
    """Return one related article, or an explicit match status without the source text."""
    terms = words(question) - STOP
    terms |= {ALIASES[w] for w in terms if w in ALIASES}
    chapters = []
    matches = list(re.finditer(r"^##\s+(.+)$", content, re.MULTILINE))
    for index, match in enumerate(matches):
        title = match.group(1)
        title_terms = words(title) - STOP
        score = len(terms & title_terms)
        if score:
            end = (
                matches[index + 1].start() if index + 1 < len(matches) else len(content)
            )
            chapters.append((score, title, content[match.end() : end]))
    if not chapters:
        return {
            "status": "not_found",
            "message": "Informe um assunto específico do regulamento.",
        }
    highest = max(c[0] for c in chapters)
    candidates = [c for c in chapters if c[0] == highest]
    if len(candidates) != 1:
        return {"status": "ambiguous", "message": "Consulte um assunto de cada vez."}
    _, title, body = candidates[0]
    title_terms = words(title) - STOP
    subjects = terms & title_terms
    query_terms = terms - title_terms
    asks_time = bool(
        terms
        & {
            "horario",
            "horarios",
            "hora",
            "horas",
            "periodo",
            "periodos",
            "abre",
            "aberta",
            "aberto",
            "abertura",
            "fecha",
            "fechar",
            "fechamento",
            "encerra",
            "encerramento",
            "funcionamento",
        }
    )
    if asks_time:
        query_terms |= {"funciona", "periodos", "horas", "horario", "disponivel"}
    if terms & {"idade", "idades", "crianca", "criancas", "etaria"}:
        query_terms |= {"anos", "etaria"}
    articles = re.split(r"(?=^\*\*Art\.)", body, flags=re.MULTILINE)
    scored = []
    active_subjects = set()
    for article in articles:
        article = article.strip()
        if not article.startswith("**Art."):
            continue
        # Capítulos mistos não tornam seus assuntos intercambiáveis. O começo
        # do artigo define o assunto; artigo seguinte sem nome explícito herda
        # esse contexto (ex.: personal trainer continua a seção da academia).
        opening = article.split("\n\n", 1)[0]
        explicit_subjects = words(opening) & title_terms
        if explicit_subjects:
            active_subjects = explicit_subjects
        if not subjects & active_subjects:
            continue
        score = len(words(article) & query_terms)
        if asks_time and re.search(r"\b\d{1,2}h(?:\d{2})?\b", article):
            score += 2
        scored.append((score, article))
    if not scored or max(score for score, _ in scored) == 0:
        return {
            "status": "not_found",
            "message": "Especifique a dúvida, por exemplo horário ou convidados.",
        }
    best = max(score for score, _ in scored)
    selected = [text for score, text in scored if score == best]
    if len(selected) != 1 or len(selected[0]) > 4000:
        return {
            "status": "ambiguous",
            "message": "Refine a dúvida para selecionar um único artigo.",
        }
    return {"status": "found", "chapter": title, "excerpt": selected[0]}
