from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from services.agenda.models.agenda_seed import AgendaSeed
from services.agenda.models.reservation import Reservation
from services.apartments.models.apartment import Apartment
from services.apartments.models.apartment_resident import ApartmentResident
from services.common_areas.models.area import Area
from microservice_toolkit import Repository


class AgendaSeedRepository(Repository):
    def add(self, generator):
        self.session.execute(select(func.pg_advisory_xact_lock(640203)))
        AgendaSeed.__table__.create(self.session.connection(), checkfirst=True)
        source = Path(os.environ.get("AURORA_DATA_DIR", "/app/dados")) / "areas.json"
        ids = [row["id"] for row in json.loads(source.read_text())]
        areas = (
            self.session.execute(
                select(Area.id, Area.fee_cents)
                .where(Area.id.in_(ids))
                .order_by(Area.id)
            )
            .mappings()
            .all()
        )
        residents = (
            self.session.execute(
                select(Apartment.number, ApartmentResident.resident_id)
                .join(
                    ApartmentResident,
                    ApartmentResident.apartment_id == Apartment.id,
                )
                .order_by(Apartment.number)
            )
            .mappings()
            .all()
        )
        if not areas or not residents:
            return "Nenhuma reserva criada. Cadastre áreas e responsáveis primeiro."
        inserted = skipped = 0
        anchor = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        for code, apartment, resident_id, area_id, day, fee, start, end in generator(
            anchor, areas, residents
        ):
            try:
                with self.session.begin_nested():
                    self.session.add(
                        Reservation(
                            code=code,
                            apartment=apartment,
                            resident_id=resident_id,
                            area_id=area_id,
                            date=day,
                            fee_cents=fee,
                            start_time=start,
                            end_time=end,
                            status="active",
                        )
                    )
                    self.session.flush()
                    self.session.add(AgendaSeed(reservation_code=code))
                inserted += 1
            except IntegrityError:
                skipped += 1
        return f"{inserted} reservas de demonstração criadas. {skipped} combinações existentes preservadas."

    def remove(self):
        self.session.execute(select(func.pg_advisory_xact_lock(640203)))
        if not inspect(self.session.connection()).has_table("aurora_agenda_seed"):
            return "Nenhuma reserva de demonstração registrada."
        records = self.session.scalars(
            select(Reservation).join(
                AgendaSeed, AgendaSeed.reservation_code == Reservation.code
            )
        ).all()
        for record in records:
            self.session.delete(record)
        self.session.flush()
        return f"{len(records)} reservas de demonstração removidas."
