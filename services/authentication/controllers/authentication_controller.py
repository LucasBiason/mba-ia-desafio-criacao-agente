from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_hex

import jwt
from microservice_toolkit import required_secret

from services.authentication.models.login_session import LoginSession
from services.authentication.repositories.session_repository import SessionRepository
from services.authentication.security import AUDIENCE, ISSUER, SESSION_SECONDS
from services.authentication.serializers.authentication_serializer import (
    AuthenticationSerializer,
)
from services.authentication.validators.authentication_validator import (
    AuthenticationValidator,
)
from services.users.serializers.account_serializer import AccountSerializer


class AuthenticationController:
    def verify_identity(self, token):
        """Resolve o bearer para o middleware do próprio serviço de identidade."""
        return self.me("Bearer " + token).model_dump()

    def login(self, data):
        bucket = sha256(data.email.encode()).hexdigest()
        with SessionRepository() as repository:
            attempts = repository.register_attempt(bucket)
        AuthenticationValidator.validate_attempts(attempts)
        with SessionRepository() as repository:
            account = AuthenticationValidator(repository).credentials(
                data.email, data.password
            )
            now = datetime.now(UTC)
            session_id = token_hex(16)
            record = LoginSession(
                id=session_id,
                account_id=account.id,
                expires_at=now + timedelta(seconds=SESSION_SECONDS),
            )
            repository.create(record, bucket)
            token = jwt.encode(
                {
                    "sub": account.id,
                    "jti": session_id,
                    "iat": now,
                    "exp": record.expires_at,
                    "iss": ISSUER,
                    "aud": AUDIENCE,
                },
                required_secret("AURORA_JWT_KEY"),
                algorithm="HS256",
            )
            return AuthenticationSerializer.token(account, token)

    def me(self, authorization):
        with SessionRepository() as repository:
            account, _ = AuthenticationValidator(repository).identity(authorization)
            return AccountSerializer.serialize(account)

    def logout(self, authorization):
        with SessionRepository() as repository:
            _, session_id = AuthenticationValidator(repository).identity(authorization)
            repository.revoke(session_id)
