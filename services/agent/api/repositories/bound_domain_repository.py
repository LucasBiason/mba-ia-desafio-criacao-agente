from ..validators.domain_values import iso_day as _iso
from ..validators.domain_values import visible_name as _name


class BoundDomain:
    """Capacidades fixadas pelo servidor no apartamento da sessão."""

    def __init__(self, domain, apartment: str):
        self._domain, self._apartment = domain, apartment

    def listar_reservas(self):
        return {"reservas": self._domain.reservations(self._apartment)}

    def listar_visitantes(self):
        return {"visitantes": self._domain.visitors(self._apartment)}

    def consultar_disponibilidade(self, area: str, data: str):
        with self._domain.connection() as conn:
            row = self._domain._area(conn, area)
            if row is None:
                return {"status": "unknown_area"}
            try:
                day = _iso(data)
            except ValueError:
                return {"status": "invalid_date"}
            available = self._domain._available(conn, row["id"], day)
            return {"status": "available" if available else "occupied"}

    def reservar_area(
        self, area: str, data: str, *, operation_id: str, start=None, end=None
    ):
        with self._domain.connection(write=True) as conn:
            row = self._domain._area(conn, area)
            if row is None:
                return {"status": "unknown_area"}
            try:
                day = _iso(data)
            except ValueError:
                return {"status": "invalid_date"}
            key = row["id"]
            if start is not None or end is not None:
                return {"status": "time_not_supported"}
            fee = row["fee_cents"]
            details = {"area": key, "data": day}
            if fee > 0:
                if not self._domain._available(conn, key, day):
                    return {"status": "occupied"}
                return {
                    "status": "confirmation_required",
                    "acao": "reservar_area",
                    "detalhes": dict(details, taxa=fee / 100),
                }
            return self._domain._once(
                conn,
                self._apartment,
                "free_reservation",
                details,
                operation_id,
                lambda: self._domain._insert_reservation(
                    conn, self._apartment, key, day
                ),
            )

    def cancelar_reserva(self, area: str, data: str, *, operation_id: str):
        with self._domain.connection(write=True) as conn:
            row = self._domain._area(conn, area)
            if row is None:
                return {"status": "unknown_area"}
            try:
                day = _iso(data)
            except ValueError:
                return {"status": "invalid_date"}

            def cancel():
                return self._domain.cancel_reservation(
                    conn, self._apartment, row["id"], day
                )

            return self._domain._once(
                conn,
                self._apartment,
                "cancel_reservation",
                {"area": row["id"], "data": day},
                operation_id,
                cancel,
            )

    def preparar_visita(self, nome: str, data: str):
        try:
            name, day = _name(nome), _iso(data)
        except ValueError:
            return {"status": "invalid_details"}
        return {
            "status": "confirmation_required",
            "acao": "autorizar_visitante",
            "detalhes": {"nome": name, "data": day},
        }
