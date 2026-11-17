from sqlalchemy import select

from services.persistence.repository import ApplicationRepository
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident


class UnitScopeRepository(ApplicationRepository):
    def owns_unit(self, number, user_id, *, lock=False):
        query = select(Apartment).join(ApartmentResident, ApartmentResident.apartment_id == Apartment.id).where(
            Apartment.number == number, ApartmentResident.resident_id == user_id,
        )
        if lock:
            query = query.with_for_update(of=Apartment)
        return self.session.scalar(query) is not None
