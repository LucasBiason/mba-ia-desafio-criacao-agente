from sqlalchemy import select

from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident
from services.apartments.repositories.unit_scope_repository import UnitScopeRepository
from services.agent.models.chat_session import ChatSession


class ChatRepository(UnitScopeRepository):
    def authorized_query(self, resident_id):
        return select(ChatSession).join(Apartment, Apartment.number == ChatSession.apartment).join(
            ApartmentResident, ApartmentResident.apartment_id == Apartment.id,
        ).where(ChatSession.resident_id == resident_id, ApartmentResident.resident_id == resident_id)

    def list(self, resident_id):
        return self.session.scalars(self.authorized_query(resident_id).order_by(
            ChatSession.created_at.desc(), ChatSession.id,
        )).all()

    def get(self, session_id, resident_id):
        return self.session.scalar(self.authorized_query(resident_id).where(ChatSession.id == session_id))

    def create(self, record):
        self.session.add(record)
        self.session.flush()
        return record
