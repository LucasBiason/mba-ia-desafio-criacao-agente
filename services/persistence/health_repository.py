from sqlalchemy import select

from services.persistence.repository import ApplicationRepository


class HealthRepository(ApplicationRepository):
    @classmethod
    def check(cls):
        with cls() as repository:
            repository.session.execute(select(1))
