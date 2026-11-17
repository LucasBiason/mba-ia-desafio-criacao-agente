from sqlalchemy import func, select

from services.persistence.repository import ApplicationRepository
from services.common_areas.models.area import Area


class AreaRepository(ApplicationRepository):
    def list(self):
        return self.session.scalars(select(Area).order_by(Area.name, Area.id)).all()

    def get(self, area_id, *, lock=False):
        return self.session.get(Area, area_id, with_for_update=lock)

    def named_area(self, name):
        return self.session.scalar(select(Area.id).where(func.lower(Area.name) == name.lower()))

    def create(self, area):
        self.session.add(area)
        self.session.flush()
        return area

    def save(self, area, values):
        for field, value in values.items():
            setattr(area, field, value)
        self.session.flush()
        return area

    def delete(self, area):
        self.session.delete(area)
        self.session.flush()
