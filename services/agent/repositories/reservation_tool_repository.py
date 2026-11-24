"""Consulta de reservas vinculada à sessão, sem identidade escolhida pelo modelo."""

from sqlalchemy import select

from services.agent.models.chat_session import ChatSession
from services.agent.repositories.chat_repository import ChatRepository
from services.agenda.models.reservation import Reservation
from services.common_areas.models.area import Area


class ReservationToolRepository(ChatRepository):
    def active_reservations(self, session_id, resident_id):
        # A subconsulta repete o vínculo vigente no instante da leitura. Não usar
        # apartamento guardado no prompt nem uma lista geral filtrada em Python.
        scope = (
            self.authorized_query(resident_id)
            .where(
                ChatSession.id == session_id,
            )
            .subquery()
        )
        query = (
            select(Reservation, Area.name)
            .join(
                Area,
                Area.id == Reservation.area_id,
            )
            .join(scope, scope.c.apartment == Reservation.apartment)
            .where(
                Reservation.status == "active",
                Reservation.resident_id == resident_id,
            )
            .order_by(Reservation.date, Reservation.code)
        )
        return self.session.execute(query).all()
