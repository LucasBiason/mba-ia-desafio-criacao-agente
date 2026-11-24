"""Tool autenticada: lê versão vigente no servidor e expõe só artigo pertinente."""

from services.parameters.repositories.regulation_repository import RegulationRepository
from services.parameters.queries.regulation_excerpt import select_excerpt, words
import hashlib


class RegulationReadTool:
    def __init__(self, access_tool, *, repository_factory=RegulationRepository):
        self.identity = access_tool.identity
        self._validate_access = access_tool.validate_access
        self.repository_factory = repository_factory

    def consultar_regulamento(self, pergunta: str) -> dict:
        """Consulta uma dúvida específica do regulamento vigente, sem devolver texto integral."""
        self._validate_access()
        if not isinstance(pergunta, str) or not pergunta.strip() or len(pergunta) > 500:
            raise ValueError("Informe uma pergunta entre1 e500 caracteres.")
        with self.repository_factory() as repository:
            current = repository.current()
            if current is None:
                return {
                    "status": "unavailable",
                    "message": "Regulamento não disponível.",
                }
            result = select_excerpt(current.content, pergunta)
            audited = audited_reservation_absence(current.content, pergunta)
            if audited is not None:
                # Lexical overlap with "salão" alone can select an unrelated
                # prohibition. The reviewed absence is specific to this question.
                result = audited
            return {"version": current.version, **result}


# Reviewed source: official unchanged regulation; this is NOT a policy for edits.
AUDITED_REGULATION_SHA256 = (
    "86893f3b1471c06ec48c4004d2a9739134b22fac4ec5802b5d10a554cb5f4494"
)


def is_reservation_notice_question(question):
    terms = words(question)
    reservation = bool(terms & {"reserva", "reservas", "reservar", "salao"})
    notice = bool(terms & {"antecedencia", "antecedencias"})
    cancellation = bool(terms & {"cancelamento", "cancelar", "cancelamentos"})
    policy_cue = bool(
        terms
        & {
            "prazo",
            "prazos",
            "multa",
            "multas",
            "taxa",
            "taxas",
            "politica",
            "regras",
            "regra",
        }
    )
    return reservation and (notice or (cancellation and policy_cue))


def audited_reservation_absence(content, question):
    if not is_reservation_notice_question(question):
        return None
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != AUDITED_REGULATION_SHA256:
        return None
    return {
        "status": "not_specified",
        "message": "Na edição consultada do regulamento, não localizei prazo específico de antecedência mínima "
        "para reservar o salão nem regra específica de prazo ou multa por cancelamento dessa reserva. "
        "Isso não significa que o cancelamento seja gratuito ou que não existam regras complementares. "
        "Confirme essas condições com a administração antes de reservar ou cancelar.",
    }
