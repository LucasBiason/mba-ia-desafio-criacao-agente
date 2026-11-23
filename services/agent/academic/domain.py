"""Domínio SQLite do avaliador, separado de bancos e identidade do produto."""

from contextlib import closing, contextmanager
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from uuid import uuid4


_SCHEMA = (
    "CREATE TABLE academic_seed (version INTEGER PRIMARY KEY CHECK (version=1))",
    "CREATE TABLE apartments (number TEXT PRIMARY KEY)",
    "CREATE TABLE areas (id TEXT PRIMARY KEY, name TEXT NOT NULL, fee_cents INTEGER NOT NULL CHECK (fee_cents>=0))",
    """CREATE TABLE reservations (
        code TEXT PRIMARY KEY, apartment TEXT NOT NULL REFERENCES apartments(number),
        area TEXT NOT NULL REFERENCES areas(id), day TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
    )""",
    "CREATE UNIQUE INDEX one_active_reservation ON reservations(area,day) WHERE active=1",
    """CREATE TABLE visitors (
        id INTEGER PRIMARY KEY, apartment TEXT NOT NULL REFERENCES apartments(number),
        name TEXT NOT NULL, day TEXT NOT NULL
    )""",
    """CREATE TABLE receipts (
        operation_id TEXT PRIMARY KEY, apartment TEXT NOT NULL REFERENCES apartments(number),
        action TEXT NOT NULL, payload TEXT NOT NULL, result TEXT NOT NULL
    )""",
)


def _iso(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Data deve usar AAAA-MM-DD.")
    return date.fromisoformat(value).isoformat()


def _name(value):
    if (
        not isinstance(value, str)
        or not 1 <= len(value.strip()) <= 160
        or any(not c.isprintable() for c in value)
    ):
        raise ValueError("Nome deve conter de 1 a 160 caracteres visíveis.")
    return " ".join(value.split())


def _slug(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        return ""
    plain = unicodedata.normalize("NFKD", value)
    return re.sub(
        r"[^a-z0-9]+", "-", plain.encode("ascii", "ignore").decode().lower()
    ).strip("-")


class AcademicDomain:
    policy_store = None
    policy_now = staticmethod(lambda: datetime.now(timezone.utc))

    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()

    def _open(self, *, create=False):
        conn = sqlite3.connect(
            self.path.as_uri() + ("?mode=rwc" if create else "?mode=rw"),
            uri=True,
            timeout=10,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def connection(self, *, write=False):
        """Conexão por operação. Para escrita, reserva o lock antes de qualquer leitura."""
        with closing(self._open()) as conn, conn:
            if not conn.execute(
                "SELECT version FROM academic_seed WHERE version=1"
            ).fetchone():
                raise RuntimeError("Banco acadêmico não inicializado.")
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn

    def initialize(self, fixtures: Path | str) -> bool:
        """Carrega fixtures somente em banco vazio; nunca altera fonte, nem restaura implicitamente."""
        fixtures = Path(fixtures)

        def rows(name):
            return json.loads((fixtures / (name + ".json")).read_text(encoding="utf-8"))

        with closing(self._open(create=True)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if (
                "academic_seed" in tables
                and conn.execute(
                    "SELECT version FROM academic_seed WHERE version=1"
                ).fetchone()
            ):
                return False
            if tables:
                raise ValueError("Não inicializar sobre banco existente não acadêmico.")
            for statement in _SCHEMA:
                conn.execute(statement)
            conn.executemany(
                "INSERT INTO apartments VALUES (?)",
                [(r["numero"],) for r in rows("apartamentos")],
            )
            conn.executemany(
                "INSERT INTO areas VALUES (?,?,?)",
                [
                    (r["id"], r["nome"], int(Decimal(str(r["taxa"])) * 100))
                    for r in rows("areas")
                ],
            )
            conn.executemany(
                "INSERT INTO reservations(code,apartment,area,day) VALUES (?,?,?,?)",
                [
                    (r["codigo"], r["apartamento"], r["area"], _iso(r["data"]))
                    for r in rows("reservas")
                ],
            )
            conn.executemany(
                "INSERT INTO visitors(apartment,name,day) VALUES (?,?,?)",
                [
                    (r["apartamento"], _name(r["nome"]), _iso(r["data"]))
                    for r in rows("visitantes")
                ],
            )
            conn.execute("INSERT INTO academic_seed VALUES (1)")
            return True

    def has_apartment(self, apartment: str) -> bool:
        with self.connection() as conn:
            return (
                conn.execute(
                    "SELECT 1 FROM apartments WHERE number=?", (apartment,)
                ).fetchone()
                is not None
            )

    def reservations(self, apartment: str) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT code AS codigo,area,day AS data FROM reservations
                WHERE apartment=? AND active=1 ORDER BY day,area,code""",
                (apartment,),
            )
            return [dict(row) for row in rows]

    def visitors(self, apartment: str) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT name AS nome,day AS data FROM visitors
                WHERE apartment=? ORDER BY day,name,id""",
                (apartment,),
            )
            return [dict(row) for row in rows]

    def tools(self, apartment: str):
        if not self.has_apartment(apartment):
            raise ValueError("Apartamento não cadastrado.")
        return BoundDomain(self, apartment)

    @staticmethod
    def _area(conn, value):
        target = _slug(value)
        if not target:
            return None
        for row in conn.execute("SELECT id,name,fee_cents FROM areas"):
            if target in (row["id"], _slug(row["name"])):
                return row
        return None

    @staticmethod
    def _available(conn, area, day):
        return not conn.execute(
            "SELECT 1 FROM reservations WHERE area=? AND day=? AND active=1",
            (area, day),
        ).fetchone()

    @staticmethod
    def _once(conn, apartment, action, details, operation_id, effect):
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 256:
            raise ValueError("Identificador confiável da operação é obrigatório.")
        if not conn.in_transaction:
            raise RuntimeError("A operação exige uma transação de escrita.")
        payload = json.dumps(
            details, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        prior = conn.execute(
            "SELECT * FROM receipts WHERE operation_id=?", (operation_id,)
        ).fetchone()
        if prior:
            if (prior["apartment"], prior["action"], prior["payload"]) != (
                apartment,
                action,
                payload,
            ):
                return {"status": "operation_conflict"}
            return json.loads(prior["result"])
        result = effect()
        conn.execute(
            "INSERT INTO receipts VALUES (?,?,?,?,?)",
            (
                operation_id,
                apartment,
                action,
                payload,
                json.dumps(result, ensure_ascii=False),
            ),
        )
        return result

    @staticmethod
    def _insert_reservation(conn, apartment, area, day):
        # O índice parcial arbitra concorrência no INSERT, não uma checagem prévia.
        for _ in range(3):
            code = "RSV-" + uuid4().hex.upper()
            cursor = conn.execute(
                """INSERT INTO reservations(code,apartment,area,day)
                VALUES (?,?,?,?)
                ON CONFLICT(area,day) WHERE active=1 DO NOTHING
                ON CONFLICT(code) DO NOTHING""",
                (code, apartment, area, day),
            )
            if cursor.rowcount:
                return {"status": "reserved", "codigo": code, "area": area, "data": day}
            if not AcademicDomain._available(conn, area, day):
                return {"status": "occupied"}
        raise RuntimeError("Não foi possível gerar um código único de reserva.")

    def policy_decision(
        self, conn, action, area, day, *, start=None, end=None, quote_version=None
    ):
        if self.policy_store is None:
            return None
        from services.agent.academic.policy import evaluate, policy_from_dict

        def hhmm(value):
            if value is None:
                return None
            if not isinstance(value, str) or not re.fullmatch(
                r"[0-9]{2}:[0-9]{2}", value
            ):
                raise ValueError("Horário deve usar HH:MM.")
            return time.fromisoformat(value)

        active = self.policy_store.active(conn, for_write=True)
        return evaluate(
            policy_from_dict(active.payload),
            action,
            area,
            date.fromisoformat(day),
            now=self.policy_now(),
            start=hhmm(start),
            end=hhmm(end),
            quote_version=quote_version,
        )

    @staticmethod
    def policy_result(ruling):
        return {
            "status": "policy_changed"
            if ruling.code == "stale_quote"
            else "policy_denied",
            "reason": ruling.code,
            "policy_version": ruling.policy_version,
            "source_articles": list(ruling.source_articles),
        }

    def insert_with_policy(self, conn, apartment, area, day, details):
        result = self._insert_reservation(conn, apartment, area, day)
        if result["status"] == "reserved" and self.policy_store is not None:
            conn.execute(
                "INSERT INTO academic_reservation_policy VALUES(?,?,?,?)",
                (
                    result["codigo"],
                    details["policy_version"],
                    details.get("hora_inicio"),
                    details.get("hora_fim"),
                ),
            )
        return result

    def apply_confirmed(self, apartment, action, details, *, operation_id):
        """Somente para o adaptador confiável que validou a confirmação externa."""
        with self.connection(write=True) as conn:
            return self.execute_confirmed(
                conn, apartment, action, details, operation_id=operation_id
            )

    def execute_confirmed(self, conn, apartment, action, details, *, operation_id):
        """Executa a ação aprovada na transação do chamador; nunca registrar como tool."""
        if not conn.execute(
            "SELECT 1 FROM apartments WHERE number=?", (apartment,)
        ).fetchone():
            return {"status": "unknown_apartment"}
        if action == "reservar_area":
            area = self._area(conn, details.get("area"))
            if area is None or (self.policy_store is None and area["fee_cents"] <= 0):
                return {"status": "invalid_action"}
            day = _iso(details.get("data"))
            if self.policy_store is not None:
                payload = {
                    k: details[k]
                    for k in (
                        "area",
                        "data",
                        "taxa",
                        "policy_version",
                        "hora_inicio",
                        "hora_fim",
                    )
                    if k in details
                }

                def revalidate():
                    ruling = self.policy_decision(
                        conn,
                        "reserve",
                        area["id"],
                        day,
                        start=payload.get("hora_inicio"),
                        end=payload.get("hora_fim"),
                        quote_version=payload.get("policy_version"),
                    )
                    if not ruling.allowed:
                        return self.policy_result(ruling)
                    if payload.get("taxa") != ruling.fee_cents / 100:
                        return {
                            "status": "policy_changed",
                            "policy_version": ruling.policy_version,
                        }
                    return self.insert_with_policy(
                        conn, apartment, area["id"], day, payload
                    )

                return self._once(
                    conn,
                    apartment,
                    "paid_reservation",
                    payload,
                    operation_id,
                    revalidate,
                )
            if details.get("taxa") != area["fee_cents"] / 100:
                return {"status": "invalid_action"}
            payload = {"area": area["id"], "data": day, "taxa": area["fee_cents"] / 100}
            return self._once(
                conn,
                apartment,
                "paid_reservation",
                payload,
                operation_id,
                lambda: self._insert_reservation(conn, apartment, area["id"], day),
            )
        if action == "autorizar_visitante":
            name, day = _name(details.get("nome")), _iso(details.get("data"))
            payload = {"nome": name, "data": day}

            def insert():
                conn.execute(
                    "INSERT INTO visitors(apartment,name,day) VALUES (?,?,?)",
                    (apartment, name, day),
                )
                return {"status": "authorized", **payload}

            return self._once(conn, apartment, action, payload, operation_id, insert)
        return {"status": "invalid_action"}


class BoundDomain:
    """Capacidades fixadas pelo servidor no apartamento da sessão."""

    def __init__(self, domain: AcademicDomain, apartment: str):
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
            if self._domain.policy_store is None and (
                start is not None or end is not None
            ):
                return {"status": "time_not_supported"}
            try:
                ruling = self._domain.policy_decision(
                    conn, "reserve", key, day, start=start, end=end
                )
            except ValueError:
                return {"status": "invalid_policy_input"}
            if ruling is not None and not ruling.allowed:
                return self._domain.policy_result(ruling)
            fee = row["fee_cents"] if ruling is None else ruling.fee_cents
            details = {"area": key, "data": day}
            if ruling is not None:
                details["policy_version"] = ruling.policy_version
                if start is not None:
                    details["hora_inicio"] = start
                if end is not None:
                    details["hora_fim"] = end
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
                lambda: self._domain.insert_with_policy(
                    conn, self._apartment, key, day, details
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
                anchor = None
                if self._domain.policy_store is not None:
                    booking = conn.execute(
                        """SELECT p.start_time FROM reservations r
                        LEFT JOIN academic_reservation_policy p ON p.code=r.code
                        WHERE r.apartment=? AND r.area=? AND r.day=? AND r.active=1""",
                        (self._apartment, row["id"], day),
                    ).fetchone()
                    if booking is None:
                        return {"status": "not_found"}
                    anchor = booking["start_time"]
                ruling = self._domain.policy_decision(
                    conn, "cancel", row["id"], day, start=anchor
                )
                if ruling is not None:
                    if not ruling.allowed:
                        return self._domain.policy_result(ruling)
                    if ruling.fee_cents:
                        return {
                            "status": "attendance_required",
                            "fee_cents": ruling.fee_cents,
                            "policy_version": ruling.policy_version,
                        }
                cursor = conn.execute(
                    """UPDATE reservations SET active=0
                    WHERE apartment=? AND area=? AND day=? AND active=1""",
                    (self._apartment, row["id"], day),
                )
                return {"status": "cancelled" if cursor.rowcount else "not_found"}

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
