from sqlalchemy import select

from microservice_toolkit import Repository
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident


class UnitScopeRepository(Repository):
    def owns_unit(self, number, user_id, *, lock=False):
        query = (
            select(Apartment)
            .join(ApartmentResident, ApartmentResident.apartment_id == Apartment.id)
            .where(
                Apartment.number == number,
                ApartmentResident.resident_id == user_id,
            )
        )
        if lock:
            query = query.with_for_update(of=Apartment)
        return self.session.scalar(query) is not None
