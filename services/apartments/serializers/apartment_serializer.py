from services.apartments.schemas.apartment_read import ApartmentRead


class ApartmentSerializer:
    @staticmethod
    def serialize(row):
        apartment, resident_id = row
        return ApartmentRead(id=apartment.id, number=apartment.number, resident_id=resident_id)
