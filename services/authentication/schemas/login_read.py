from pydantic import BaseModel

from services.users.schemas.account_read import AccountRead


class LoginRead(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: AccountRead
