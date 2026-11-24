from secrets import token_hex

from microservice_toolkit import error
from sqlalchemy.exc import IntegrityError

from services.authentication.security import hasher
from services.users.models.account import Account
from services.users.repositories.account_repository import AccountRepository
from services.users.serializers.account_serializer import AccountSerializer
from services.users.validators.account_validator import AccountValidator


class AccountController:
    def list(self, actor):
        with AccountRepository() as repository:
            AccountValidator(repository).validate_read(actor)
            return [
                AccountSerializer.serialize(account) for account in repository.list()
            ]

    def get(self, user_id, actor=None):
        with AccountRepository() as repository:
            AccountValidator(repository).validate_read(actor)
            return AccountSerializer.serialize(
                AccountValidator(repository).existing(user_id)
            )

    def create(self, data, actor):
        try:
            with AccountRepository() as repository:
                AccountValidator(repository).validate_create(data, actor)
                account = Account(
                    id=token_hex(16),
                    name=data.name,
                    email=data.email,
                    password_hash=hasher.hash(data.password),
                    role=data.role,
                    active=True,
                )
                return AccountSerializer.serialize(repository.create(account))
        except IntegrityError:
            raise error(
                409, "EMAIL_IN_USE", "Este e-mail já está cadastrado."
            ) from None

    def update(self, user_id, data, actor):
        values = data.model_dump(exclude_unset=True)
        try:
            with AccountRepository() as repository:
                account = AccountValidator(repository).validate_update(
                    actor, user_id, values
                )
                changed_access = (
                    values.get("active", account.active) != account.active
                    or "password" in values
                )
                if "password" in values:
                    values["password_hash"] = hasher.hash(values.pop("password"))
                repository.save(account, values)
                if changed_access:
                    repository.revoke_sessions(user_id)
                return AccountSerializer.serialize(account)
        except IntegrityError:
            raise error(
                409, "EMAIL_IN_USE", "Este e-mail já está cadastrado."
            ) from None
