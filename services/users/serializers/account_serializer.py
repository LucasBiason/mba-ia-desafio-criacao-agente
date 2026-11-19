from services.users.schemas.account_read import AccountRead


class AccountSerializer:
    @staticmethod
    def serialize(account):
        return AccountRead.model_validate(account)
