from secrets import token_hex

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
dummy_hash = hasher.hash(token_hex(32))
ISSUER = "residencial-aurora"
AUDIENCE = "aurora-product"
SESSION_SECONDS = 3600


def verify_password(stored_hash, password):
    try:
        return hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False
