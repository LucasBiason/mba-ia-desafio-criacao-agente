"""Account lifecycle, password authentication and revocable JWT sessions."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
from secrets import token_hex
from typing import Annotated, Literal

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import jwt
import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, StringConstraints

from services.common import authenticated_user, bearer_token, error, required_secret, verify_internal
from services.resident_seed import read_seed_apartments, seed_resident_id


Role = Literal["admin", "resident"]
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254,
                                          pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=256)]
LoginPassword = Annotated[str, StringConstraints(min_length=1, max_length=256)]

ISSUER = "residencial-aurora"
AUDIENCE = "aurora-product"
SESSION_SECONDS = 3600
HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
SCHEMA = Path(__file__).with_name("schema.sql")
RESIDENT_MIGRATION = SCHEMA.parent / "migrations" / "002_account_roles.sql"
ACCOUNT_WRITE_LOCK = 74109143
USER_FIELDS = "id, name, email, role, active"
INITIAL_ADMINS = (
    ("demo-super", "Administração auxiliar", "super@aurora.test", "DEMO_SUPER_PASSWORD"),
    ("demo-admin", "Administração", "admin@aurora.test", "DEMO_ADMIN_PASSWORD"),
)
INITIAL_RESIDENT_ID = "demo-resident"


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: Email
    password: LoginPassword


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: Name
    email: Email
    password: Password
    role: Role = "resident"


class AccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: Name | None = None
    email: Email | None = None
    password: Password | None = None
    role: Role | None = None
    active: bool | None = None


def db():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=3)


def insert_initial_account(conn, user_id: str, name: str, email: str, role: Role, variable: str) -> None:
    password = os.environ.get(variable, "")
    if not 12 <= len(password) <= 256:
        raise RuntimeError(f"Credencial local obrigatória ausente ou inválida: {variable}.")
    conn.execute(
        "INSERT INTO accounts (id, name, email, password_hash, role) VALUES (%s,%s,%s,%s,%s)",
        (user_id, name, email, HASHER.hash(password), role),
    )


def import_resident_accounts(conn, apartments: list[dict]) -> None:
    for apartment in apartments:
        number = apartment["numero"]
        name = apartment["morador"]
        user_id = seed_resident_id(number)
        if user_id == INITIAL_RESIDENT_ID:
            conn.execute(
                """UPDATE accounts SET name = %s
                   WHERE id = %s AND role = 'resident' AND name = 'Morador de demonstração'""",
                (name, user_id),
            )
            continue
        if conn.execute("SELECT 1 FROM accounts WHERE id = %s", (user_id,)).fetchone():
            continue
        local_part = f"morador-{number.lower()}"
        email = f"{local_part}@aurora.test"
        available_suffix = 2
        while conn.execute("SELECT 1 FROM accounts WHERE email = %s", (email,)).fetchone():
            email = f"{local_part}+{available_suffix}@aurora.test"
            available_suffix += 1
        conn.execute(
            """INSERT INTO accounts (id, name, email, password_hash, role, active)
               VALUES (%s,%s,%s,%s,'resident',false)""",
            (user_id, name, email, HASHER.hash(token_hex(32))),
        )


def seed_identity() -> None:
    with db() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(74109142)")
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        if conn.execute("SELECT 1 FROM identity_migrations WHERE version = 2").fetchone():
            return
        apartments = read_seed_apartments()
        if not conn.execute("SELECT 1 FROM identity_seed").fetchone():
            for user_id, name, email, variable in INITIAL_ADMINS:
                insert_initial_account(conn, user_id, name, email, "admin", variable)
            initial_resident = next(
                (row for row in apartments if seed_resident_id(row["numero"]) == INITIAL_RESIDENT_ID), None,
            )
            if initial_resident is not None:
                insert_initial_account(
                    conn, INITIAL_RESIDENT_ID, initial_resident["morador"],
                    "morador@aurora.test", "resident", "DEMO_RESIDENT_PASSWORD",
                )
            conn.execute("INSERT INTO identity_seed DEFAULT VALUES")
        conn.execute(RESIDENT_MIGRATION.read_text(encoding="utf-8"))
        import_resident_accounts(conn, apartments)
        conn.execute("INSERT INTO identity_migrations (version) VALUES (2)")


@asynccontextmanager
async def auth_lifespan(app: FastAPI):
    required_secret("AURORA_INTERNAL_TOKEN")
    required_secret("AURORA_JWT_KEY")
    seed_identity()
    app.state.dummy_hash = HASHER.hash(token_hex(32))
    yield


@asynccontextmanager
async def users_lifespan(_app: FastAPI):
    required_secret("AURORA_INTERNAL_TOKEN")
    with db() as conn:
        conn.execute("SELECT 1 FROM accounts LIMIT 1")
    yield


auth_app = FastAPI(title="Aurora · Autenticação", lifespan=auth_lifespan, docs_url=None, redoc_url=None, openapi_url=None)
users_app = FastAPI(title="Aurora · Usuários", lifespan=users_lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@auth_app.exception_handler(RequestValidationError)
@users_app.exception_handler(RequestValidationError)
def safe_validation(_request: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(map(str, item["loc"])), "code": item["type"]}
              for item in exc.errors()]
    return JSONResponse(status_code=422, content={
        "detail": {"code": "INVALID_INPUT", "message": "Revise os campos do formulário.", "fields": fields},
    })


@auth_app.exception_handler(psycopg.OperationalError)
@users_app.exception_handler(psycopg.OperationalError)
def identity_database_unavailable(_request: Request, _exc: psycopg.OperationalError):
    return JSONResponse(status_code=503, content={
        "detail": {"code": "DATABASE_UNAVAILABLE", "message": "Banco de identidade indisponível."},
    })


@auth_app.get("/health")
@users_app.get("/health")
def health():
    try:
        with db() as conn:
            conn.execute("SELECT 1 FROM identity_seed")
    except psycopg.Error:
        raise error(503, "DATABASE_UNAVAILABLE", "Banco de identidade indisponível.") from None
    return {"status": "ready"}


def public_account(row: dict) -> dict:
    return {key: row[key] for key in ("id", "name", "email", "role", "active")}


def check_password(stored_hash: str, password: str) -> bool:
    try:
        return HASHER.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def session_claims(authorization: str | None) -> dict:
    token = bearer_token(authorization)
    try:
        claims = jwt.decode(
            token,
            required_secret("AURORA_JWT_KEY"),
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud"]},
        )
        if not isinstance(claims["jti"], str) or len(claims["jti"]) != 32:
            raise jwt.InvalidTokenError()
        return claims
    except jwt.InvalidTokenError:
        raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.") from None


def current_identity(authorization: str | None) -> tuple[dict, str]:
    claims = session_claims(authorization)
    with db() as conn:
        row = conn.execute(
            """SELECT a.id, a.name, a.email, a.role, a.active
               FROM sessions s JOIN accounts a ON a.id = s.account_id
               WHERE s.id = %s AND s.account_id = %s AND s.revoked_at IS NULL
               AND s.expires_at > now() AND a.active""",
            (claims["jti"], claims["sub"]),
        ).fetchone()
    if row is None:
        raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
    return row, claims["jti"]


@auth_app.post("/api/auth/login")
def login(data: Login, response: Response):
    bucket = sha256(data.email.encode()).hexdigest()
    with db() as conn:
        conn.execute("DELETE FROM login_limits WHERE window_start < now() - interval '1 day'")
        limit = conn.execute(
            """INSERT INTO login_limits (key, window_start, attempts) VALUES (%s, now(), 1)
               ON CONFLICT (key) DO UPDATE
               SET attempts = CASE WHEN login_limits.window_start < now() - interval '15 minutes'
                                   THEN 1 ELSE login_limits.attempts + 1 END,
                   window_start = CASE WHEN login_limits.window_start < now() - interval '15 minutes'
                                       THEN now() ELSE login_limits.window_start END
               RETURNING attempts""",
            (bucket,),
        ).fetchone()
    if limit["attempts"] > 8:
        raise HTTPException(429, detail={"code": "LOGIN_LIMIT", "message": "Muitas tentativas. Aguarde 15 minutos."},
                            headers={"Retry-After": "900"})
    with db() as conn:
        account = conn.execute("SELECT * FROM accounts WHERE email = %s", (data.email,)).fetchone()
        valid = check_password(account["password_hash"] if account else auth_app.state.dummy_hash, data.password)
        if account is None or not valid or not account["active"]:
            raise error(401, "INVALID_LOGIN", "E-mail ou senha inválidos.")
        # Confirm current credentials again under a row lock to avoid creating a session
        # after another request revoked the old password or permissions.
        fresh = conn.execute("SELECT * FROM accounts WHERE id=%s FOR UPDATE", (account["id"],)).fetchone()
        if (not fresh or not fresh["active"] or fresh["password_hash"] != account["password_hash"]
                or fresh["email"] != data.email):
            raise error(401, "INVALID_LOGIN", "E-mail ou senha inválidos.")
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=SESSION_SECONDS)
        session_id = token_hex(16)
        conn.execute("DELETE FROM sessions WHERE expires_at < now()")
        conn.execute("INSERT INTO sessions (id, account_id, expires_at) VALUES (%s,%s,%s)",
                     (session_id, fresh["id"], expires_at))
        conn.execute("DELETE FROM login_limits WHERE key = %s", (bucket,))
        key = required_secret("AURORA_JWT_KEY")
        access_token = jwt.encode(
            {"sub": fresh["id"], "jti": session_id, "iat": now, "exp": expires_at, "iss": ISSUER, "aud": AUDIENCE},
            key, algorithm="HS256",
        )
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": access_token, "token_type": "bearer", "expires_in": SESSION_SECONDS,
            "user": public_account(fresh)}


@auth_app.get("/api/auth/me")
def me(authorization: Annotated[str | None, Header()] = None):
    return current_identity(authorization)[0]


@auth_app.get("/internal/identity", dependencies=[Depends(verify_internal)])
def introspect(authorization: Annotated[str | None, Header()] = None):
    return current_identity(authorization)[0]


@auth_app.post("/api/auth/logout", status_code=204)
def logout(authorization: Annotated[str | None, Header()] = None):
    _, session_id = current_identity(authorization)
    with db() as conn:
        conn.execute("UPDATE sessions SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL", (session_id,))
    return Response(status_code=204)


def admin_user(user: Annotated[dict, Depends(authenticated_user)]):
    if user["role"] != "admin":
        raise error(403, "ADMIN_REQUIRED", "Operação reservada à administração.")
    return user


def lock_account_write(conn, actor_id: str) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_WRITE_LOCK,))
    if not conn.execute(
        "SELECT 1 FROM accounts WHERE id = %s AND role = 'admin' AND active",
        (actor_id,),
    ).fetchone():
        raise error(403, "ADMIN_REQUIRED", "Operação reservada à administração.")


@users_app.get("/internal/users/{user_id}", dependencies=[Depends(verify_internal)])
def internal_user(user_id: str):
    with db() as conn:
        row = conn.execute(f"SELECT {USER_FIELDS} FROM accounts WHERE id = %s", (user_id,)).fetchone()
    if row is None:
        raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
    return row


@users_app.get("/api/admin/users", dependencies=[Depends(admin_user)])
def list_users():
    with db() as conn:
        return conn.execute(f"SELECT {USER_FIELDS} FROM accounts ORDER BY name, id").fetchall()


@users_app.get("/api/admin/users/{user_id}", dependencies=[Depends(admin_user)])
def get_user(user_id: str):
    return internal_user(user_id)


@users_app.post("/api/admin/users", status_code=201)
def create_user(data: AccountCreate, actor: Annotated[dict, Depends(admin_user)]):
    password_hash = HASHER.hash(data.password)
    try:
        with db() as conn:
            lock_account_write(conn, actor["id"])
            return conn.execute(
                f"""INSERT INTO accounts (id, name, email, password_hash, role)
                     VALUES (%s,%s,%s,%s,%s) RETURNING {USER_FIELDS}""",
                (token_hex(16), data.name, data.email, password_hash, data.role),
            ).fetchone()
    except UniqueViolation:
        raise error(409, "EMAIL_IN_USE", "Este e-mail já está cadastrado.") from None


@users_app.patch("/api/admin/users/{user_id}")
def update_user(user_id: str, data: AccountPatch, actor: Annotated[dict, Depends(admin_user)]):
    values = data.model_dump(exclude_unset=True)
    if not values or any(value is None for value in values.values()):
        raise error(422, "INVALID_UPDATE", "Informe um ou mais campos válidos.")
    try:
        with db() as conn:
            lock_account_write(conn, actor["id"])
            row = conn.execute("SELECT * FROM accounts WHERE id = %s FOR UPDATE", (user_id,)).fetchone()
            if row is None:
                raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
            if values.get("role", row["role"]) != row["role"]:
                raise error(409, "ROLE_IMMUTABLE", "O perfil da conta é definido no cadastro.")
            active = values.get("active", row["active"])
            if row["role"] == "admin" and row["active"] and not active:
                if not conn.execute(
                    "SELECT 1 FROM accounts WHERE role = 'admin' AND active AND id <> %s LIMIT 1",
                    (user_id,),
                ).fetchone():
                    raise error(409, "LAST_ADMIN", "Mantenha pelo menos um administrador ativo.")
            password_hash = HASHER.hash(values["password"]) if "password" in values else row["password_hash"]
            saved = conn.execute(
                f"""UPDATE accounts SET name=%s, email=%s, active=%s, password_hash=%s
                     WHERE id=%s RETURNING {USER_FIELDS}""",
                (values.get("name", row["name"]), values.get("email", row["email"]), active,
                 password_hash, user_id),
            ).fetchone()
            if active != row["active"] or "password" in values:
                conn.execute("UPDATE sessions SET revoked_at = now() WHERE account_id=%s AND revoked_at IS NULL",
                             (user_id,))
            return saved
    except UniqueViolation:
        raise error(409, "EMAIL_IN_USE", "Este e-mail já está cadastrado.") from None
