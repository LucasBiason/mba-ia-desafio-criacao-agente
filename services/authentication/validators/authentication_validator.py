from fastapi import HTTPException
import jwt
from microservice_toolkit import bearer_token, error, required_secret

from services.authentication.security import (
    AUDIENCE,
    ISSUER,
    dummy_hash,
    verify_password,
)


class AuthenticationValidator:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def validate_attempts(attempts):
        if attempts > 8:
            raise HTTPException(
                429,
                detail={
                    "code": "LOGIN_LIMIT",
                    "message": "Muitas tentativas. Aguarde 15 minutos.",
                },
                headers={"Retry-After": "900"},
            )

    def credentials(self, email, password):
        account = self.repository.account_by_email(email)
        valid = verify_password(
            account.password_hash if account else dummy_hash, password
        )
        if account is None or not valid or not account.active:
            raise error(401, "INVALID_LOGIN", "E-mail ou senha inválidos.")
        original_hash = account.password_hash
        fresh = self.repository.locked_account(account.id)
        if (
            fresh is None
            or not fresh.active
            or fresh.email != email
            or fresh.password_hash != original_hash
        ):
            raise error(401, "INVALID_LOGIN", "E-mail ou senha inválidos.")
        return fresh

    def claims(self, authorization):
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
            raise error(
                401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente."
            ) from None

    def identity(self, authorization):
        claims = self.claims(authorization)
        account = self.repository.identity(claims)
        if account is None:
            raise error(401, "INVALID_SESSION", "Sua sessão expirou. Entre novamente.")
        return account, claims["jti"]
