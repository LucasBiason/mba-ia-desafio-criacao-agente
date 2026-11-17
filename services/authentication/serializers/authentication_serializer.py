from services.authentication.schemas.login_read import LoginRead
from services.authentication.security import SESSION_SECONDS
from services.users.serializers.account_serializer import AccountSerializer


class AuthenticationSerializer:
    @staticmethod
    def token(account, access_token):
        return LoginRead(access_token=access_token, token_type="bearer", expires_in=SESSION_SECONDS,
                         user=AccountSerializer.serialize(account))
