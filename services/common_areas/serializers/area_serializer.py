from services.common_areas.schemas.area_read import AreaRead


class AreaSerializer:
    @staticmethod
    def serialize(area):
        return AreaRead.model_validate(area)
