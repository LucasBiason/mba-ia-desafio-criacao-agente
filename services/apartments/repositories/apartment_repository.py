from sqlalchemy import select

from services.persistence.repository import ApplicationRepository
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident


class ApartmentRepository(ApplicationRepository):
    def list(self, resident_id=None):
        query = select(Apartment, ApartmentResident.resident_id).outerjoin(
            ApartmentResident, ApartmentResident.apartment_id == Apartment.id,
        )
        if resident_id is not None:
            query = query.where(ApartmentResident.resident_id == resident_id)
        return self.session.execute(query.order_by(Apartment.number)).all()

    def get(self, number, *, lock=False):
        query = select(Apartment).where(Apartment.number == number.upper())
        if lock:
            query = query.with_for_update()
        apartment = self.session.scalar(query)
        if apartment is None:
            return None
        relation = self.session.get(ApartmentResident, apartment.id)
        return apartment, relation.resident_id if relation else None

    def create(self, apartment, resident_id):
        self.session.add(apartment)
        self.session.flush()
        self.assign(apartment.id, resident_id)
        return apartment, resident_id

    def assign(self, apartment_id, resident_id):
        relation = self.session.get(ApartmentResident, apartment_id)
        if resident_id is None:
            if relation is not None:
                self.session.delete(relation)
        elif relation is None:
            self.session.add(ApartmentResident(apartment_id=apartment_id, resident_id=resident_id))
        else:
            relation.resident_id = resident_id
        self.session.flush()

    def save(self, apartment):
        self.session.flush()
        relation = self.session.get(ApartmentResident, apartment.id)
        return apartment, relation.resident_id if relation else None

    def delete(self, apartment):
        self.session.delete(apartment)
        self.session.flush()
