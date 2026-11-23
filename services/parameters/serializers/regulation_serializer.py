from services.parameters.schemas.regulation_read import RegulationRead


class RegulationSerializer:
    @staticmethod
    def serialize(regulation):
        return RegulationRead.model_validate(regulation)
