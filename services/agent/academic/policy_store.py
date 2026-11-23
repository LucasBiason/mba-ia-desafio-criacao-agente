"""Explicit, operator-published regulation/policy bundles for the optional lab profile."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json


@dataclass(frozen=True)
class PublishedPolicy:
    version: str
    payload: dict
    regulation: str


class PolicyStore:
    def __init__(self, domain):
        self.domain = domain

    def prepare(self):
        with self.domain.connection(write=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS academic_policy_revisions (
                version TEXT PRIMARY KEY, payload TEXT NOT NULL, regulation TEXT NOT NULL,
                source_sha256 TEXT NOT NULL, published_at TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS academic_policy_head (
                singleton INTEGER PRIMARY KEY CHECK (singleton=1),
                version TEXT REFERENCES academic_policy_revisions(version))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS academic_reservation_policy (
                code TEXT PRIMARY KEY REFERENCES reservations(code),
                version TEXT NOT NULL REFERENCES academic_policy_revisions(version),
                start_time TEXT, end_time TEXT)""")
            conn.execute("""INSERT INTO academic_policy_head(singleton,version) VALUES(1,NULL)
                ON CONFLICT(singleton) DO NOTHING""")

    def publish(self, *, version, payload, regulation, expected_version):
        if (
            not isinstance(version, str)
            or not 1 <= len(version.strip()) <= 80
            or version != version.strip()
        ):
            raise ValueError("Versão de política inválida.")
        if (
            not isinstance(regulation, str)
            or not 1 <= len(regulation.strip()) <= 512_000
        ):
            raise ValueError("Regulamento deve conter texto.")
        if not isinstance(payload, dict) or payload.get("version") != version:
            raise ValueError("O documento e a versão publicada precisam corresponder.")
        from services.agent.academic.policy import policy_from_dict

        policy_from_dict(payload)
        content = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        suffix = " FOR UPDATE" if getattr(self.domain, "is_postgres", False) else ""
        with self.domain.connection(write=True) as conn:
            row = conn.execute(
                "SELECT version FROM academic_policy_head WHERE singleton=1" + suffix
            ).fetchone()
            if row is None or row["version"] != expected_version:
                raise ValueError(
                    "A versão-base da política mudou; revise antes de publicar."
                )
            prior = conn.execute(
                "SELECT version FROM academic_policy_revisions WHERE version=?",
                (version,),
            ).fetchone()
            if prior:
                raise ValueError(
                    "Uma versão publicada é imutável; crie outro identificador."
                )
            conn.execute(
                "INSERT INTO academic_policy_revisions VALUES(?,?,?,?,?)",
                (
                    version,
                    content,
                    regulation,
                    sha256(regulation.encode()).hexdigest(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.execute(
                "UPDATE academic_policy_head SET version=? WHERE singleton=1",
                (version,),
            )

    def active(self, conn, *, for_write=False):
        if for_write and getattr(self.domain, "is_postgres", False):
            # Lock the head first, then read its immutable revision in a fresh
            # READ COMMITTED statement. Avoid a stale join snapshot if a
            # concurrent publisher just changed the pointer while we waited.
            head = conn.execute(
                "SELECT version FROM academic_policy_head WHERE singleton=1 FOR SHARE"
            ).fetchone()
            row = (
                conn.execute(
                    """SELECT version,payload,regulation FROM academic_policy_revisions
                WHERE version=?""",
                    (head["version"],),
                ).fetchone()
                if head and head["version"]
                else None
            )
        else:
            row = conn.execute("""SELECT v.version,v.payload,v.regulation
                FROM academic_policy_head h JOIN academic_policy_revisions v ON v.version=h.version
                WHERE h.singleton=1""").fetchone()
        if row is None:
            raise ValueError(
                "Não existe política publicada neste perfil; nenhuma ação permitida."
            )
        return PublishedPolicy(
            row["version"], json.loads(row["payload"]), row["regulation"]
        )

    def regulation(self):
        with self.domain.connection() as conn:
            return self.active(conn).regulation
