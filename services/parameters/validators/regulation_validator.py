from microservice_toolkit import error

from aurora_toolkit.permissions import require_admin, require_resident


class RegulationValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_read(self, actor, resident_view=False):
        require_resident(actor) if resident_view else require_admin(actor)

    def validate_publish(self, data, actor):
        require_admin(actor)
        if not data.content.strip():
            raise error(422, "INVALID_REGULATION", "Informe o conteúdo do regulamento.")
        current = self.repository.current(lock=True)
        if current.version != data.base_version:
            raise error(
                409,
                "REGULATION_CHANGED",
                "A versão vigente mudou. Recarregue o regulamento.",
            )
        if current.content == data.content:
            raise error(
                422,
                "REGULATION_UNCHANGED",
                "Altere o conteúdo antes de publicar uma versão.",
            )
        return current
