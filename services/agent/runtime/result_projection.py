"""Texto público derivado somente de resultados autorizados de consulta."""

import json


def project_reads(read_results):
    grounded = []
    regulation_results = [
        result for kind, result in read_results if kind == "regulation"
    ]
    has_cited = any(result.get("status") == "found" for result in regulation_results)
    audited_misses = [
        result
        for result in regulation_results
        if result.get("status") == "not_specified"
    ]
    miss_emitted = False
    for kind, result in read_results:
        if kind == "regulation":
            if result.get("status") == "found":
                grounded.append(
                    f"Regulamento versão {result['version']}:\n{result['excerpt']}"
                )
            elif not miss_emitted and (not has_cited or audited_misses):
                selected = audited_misses[-1] if audited_misses else result
                grounded.append(
                    selected.get("message")
                    or "Não foi possível selecionar um trecho. Especifique a dúvida."
                )
                miss_emitted = True
        elif kind == "availability":
            grounded.append(
                {
                    "occupied": "A área está ocupada na data consultada.",
                    "available": "A área está disponível na data consultada.",
                    "unknown_area": "Área não cadastrada.",
                    "invalid_details": "Informe área e data válidas.",
                }.get(
                    result.get("status"),
                    "Não foi possível confirmar disponibilidade.",
                )
            )
        elif kind == "visitors":
            rows = result.get("visitors", [])
            grounded.append(
                "Visitas da sua unidade:\n"
                + json.dumps(rows, ensure_ascii=False, indent=2)
                if rows
                else "Não há visitas registradas para este morador."
            )
        elif kind == "reservations":
            rows = result.get("reservations", [])
            grounded.append(
                "Reservas ativas da sua unidade:\n"
                + json.dumps(rows, ensure_ascii=False, indent=2)
                if rows
                else "Não há reservas ativas da sua unidade para este morador."
            )
    return "\n\n".join(dict.fromkeys(grounded))
