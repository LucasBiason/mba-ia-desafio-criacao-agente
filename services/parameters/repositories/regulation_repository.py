from sqlalchemy import func, select

from microservice_toolkit import Repository
from services.parameters.models.regulation import Regulation


class RegulationRepository(Repository):
    def current(self, *, lock=False):
        if lock:
            self.session.execute(select(func.pg_advisory_xact_lock(640202)))
        return self.session.scalar(
            select(Regulation).order_by(Regulation.version.desc()).limit(1)
        )

    def list(self):
        return self.session.scalars(
            select(Regulation).order_by(Regulation.version.desc())
        ).all()

    def create(self, regulation):
        self.session.add(regulation)
        self.session.flush()
        return regulation
